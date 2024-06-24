"""
get types needed
check order service for the types
get orders for matching types until storage is full
assign orders to production lines
get finished or incomplete orders from production line
senf finished orders to order agent
put incomplete orders to order service
repeat
"""
import asyncio
import datetime
import re
from typing import List, Optional, TypedDict

from spade.agent import Agent
import spade.behaviour
import spade.template
from spade.message import Message

from Classes.Util import get_order_info, get_sender_info, is_done, get_next_item_index, get_item_list_parts, \
    get_managers, log, get_type, get_types, Log
from DF.DF import ServiceDescription, Property, AgentDescription, df
from Classes.ProductionOrder import ProductionOrder
from Enums.MachineType import MachineType


# from create_report import agent_messages


class MachineInfo(TypedDict):
    available: bool
    description: AgentDescription


class GroupManagerAgent(Agent):
    def __init__(self, jid: str, password: str, group: str, *args, **kwargs):
        super().__init__(jid, password, *args, **kwargs)
        self.group = group

    async def setup(self) -> None:
        main = MainBehaviour(self)
        self.add_behaviour(main)

    async def get_machines(self, request):
        unavailable_machines = []
        managed_machines = []

        # Extract group number from self.jid
        if '/' in str(self.jid):
            base_jid, resource = str(self.jid).rsplit('/', 1)
            if resource.isdigit() and len(resource) == 1:
                group_number = resource
            else:
                raise ValueError("Invalid group number in self.jid")
        else:
            raise ValueError("Invalid format for self.jid")

        # Search for messages indicating machine unavailability
        unavailable_pattern = r"Machine ([0-9]+) of type [0-9] is unavailable."

        if self.jid in Log:
            messages = Log[self.jid]

            # List to store the most recent 5 unavailable machine messages
            recent_unavailable = []

            for log_message in reversed(messages):
                if len(recent_unavailable) >= 5:
                    break

                if "Machine" in log_message.message and "is unavailable." in log_message.message:
                    match = re.search(unavailable_pattern, log_message.message)
                    if match:
                        machine_number = match.group(1)
                        recent_unavailable.append(f"{log_message.time}: Machine {machine_number}")

            # Reverse the list to maintain chronological order
            recent_unavailable.reverse()
            unavailable_machines = recent_unavailable

        # Get machines controlled by the manager
        for agent_jid, messages in Log.items():
            if agent_jid.startswith(base_jid) and '/' in agent_jid:
                _, resource = agent_jid.rsplit('/', 1)
                if resource.isdigit() and len(resource) == 2 and resource[0] == group_number:
                    managed_machines.append(agent_jid)

        return {
            "unavailable_machines": unavailable_machines,
            "managed_machines": managed_machines
        }


class MainBehaviour(spade.behaviour.CyclicBehaviour):
    def __init__(self, agent: GroupManagerAgent):
        super().__init__()
        self.agent = agent
        self.orders: List[ProductionOrder] = []
        self.machines: dict[str, MachineInfo] = {}
        self.description: AgentDescription = AgentDescription()

    async def on_start(self) -> None:
        log(self.agent, "GoM Manager Bahaviour starting. Waiting 3s for machines")
        await asyncio.sleep(3)
        log(self.agent, f"Looking for Machines in Group {self.agent.group}")
        self.machines = await self.get_machines()
        log(self.agent, f"Machines found: {len(self.machines)}")
        await self.setup_presence()
        machine: str
        for machine in self.machines.keys():
            msg: Message = Message(to=str(machine), body="Machines initialized")
            await self.send(msg)
        self.description = await self.register()
        log(self.agent, f"Registering Manager Service with the DF: {self.description}")
        log(self.agent, "GoM Manager Bahaviour startup finished")

    async def on_stop(self) -> None:
        log(self.agent, "GoM Manager stopping")
        await self.agent.stop()

    async def setup_presence(self) -> None:
        self.presence.on_available = self.on_available
        self.presence.on_unavailable = self.on_unavailable
        self.presence.set_available()
        machine_jid: str
        for machine_jid in self.machines.keys():
            self.presence.subscribe(str(machine_jid))

    def on_available(self, jid, stanza) -> None:
        machine = self.machines.get(jid)
        if not machine or machine["available"]:
            return

        type = get_type(machine["description"])
        if self.description.services["manager"].properties[type].value is int:
            self.description.services["manager"].properties[type].value += 1
        df.update(self.description)
        log(self.agent, f"Machine {jid} of type {type} is available.")
        self.machines[jid]["available"] = True

    def on_unavailable(self, jid, stanza) -> None:
        machine = self.machines.get(jid)
        if not machine or not machine["available"]:
            return

        type = get_type(machine["description"])
        if self.description.services["manager"].properties[type].value is int:
            self.description.services["Manager"].properties[type].value -= 1
        df.update(self.description)
        log(self.agent, f"Machine {jid} of type {type} is unavailable.")
        self.machines[jid]["available"] = False

    async def get_machines(self) -> dict[str, MachineInfo]:
        machine_service: ServiceDescription = ServiceDescription(type="machine")
        group_property: Property = Property("group", self.agent.group)
        machine_service.add_property(group_property)
        query: AgentDescription = AgentDescription()
        query.add_service(machine_service)
        machines = df.search(query)
        result: dict[str, MachineInfo] = {}
        machine: AgentDescription
        for machine in machines:
            if result.get(machine.name) is None:
                result[machine.name] = {"available": True, "description": machine}
        return result

    async def register(self) -> AgentDescription:
        types = get_types()
        machine_type_counts = {type: 0 for type in types}

        try:
            for machine in [info["description"] for info in self.machines.values()]:
                property: Property = machine.services["machine"].properties["type"]
                machine_type_counts[property.value] += 1

            manager_service = ServiceDescription(type="manager")
            for machine_type, count in machine_type_counts.items():
                type_property = Property(machine_type, count)
                manager_service.add_property(type_property)

            agent_description = AgentDescription(self.agent.jid)
            agent_description.add_service(manager_service)
            df.register(agent_description)
            return agent_description

        except KeyError as e:
            print(machine_type_counts)
            print(f"KeyError: {e}")
            raise
        except AttributeError as e:
            print(f"AttributeError: {e}")
            raise

    async def run(self) -> None:
        while True:
            msg = await self.receive()
            if msg:
                if msg.get_metadata("ontology") == "order_request":
                    await self.order_received(msg.body, msg.get_metadata("order_id"))
                elif msg.get_metadata("ontology") == "order_machine_missing":
                    await self.order_missing_machine_received(msg.body, msg.get_metadata("order_id"))
                elif msg.metadata["ontology"] == "order_part_completed":
                    order = get_order_info(msg.body)
                    log(self.agent, f"Order progress confirmation received: {order}.")
                    continue
                else:
                    log(self.agent, f"Unknown ontology: {msg.get_metadata('ontology')}")
            else:
                await asyncio.sleep(1)

    async def order_received(self, order: str, order_id: str) -> None:
        order = get_order_info(order)
        log(self.agent, f"Received Order: {order}, order_id: {order_id}.")
        if is_done(order):
            return

        log(self.agent, f"Searching for machine.")
        machine = self.find_machine(order)
        if machine:
            log(self.agent, f"Machine found: {machine}.")
            await self.send_order(order, order_id, machine)
        else:
            log(self.agent, f"Machine not found.")
            await self.order_missing_machine_received(order, order_id)

    async def order_missing_machine_received(self, order: str, order_id: str) -> None:
        order = get_order_info(order)
        manager = self.get_available_manager(order)
        await self.send_order(order, order_id, manager)

    def find_machine(self, order: str) -> str:

        machine_service: ServiceDescription = ServiceDescription(type="machine")

        next_item_index = get_next_item_index(order)
        type = order[next_item_index]
        type_property: Property = Property("type", type)
        machine_service.add_property(type_property)

        group = self.agent.group
        group_property: Property = Property("group", group)
        machine_service.add_property(group_property)

        busy_property: Property = Property("busy", False)
        machine_service.add_property(busy_property)

        query: AgentDescription = AgentDescription()
        query.add_service(machine_service)
        print(f"query: {query}")
        machines = df.search(query)

        if machines:
            return machines[0].name
        return ""

    async def send_order(self, order: str, order_id: str, agent_jid: str) -> None:
        msg = Message(to=str(agent_jid))
        msg.set_metadata("ontology", "order_request")
        msg.set_metadata("order_id", order_id)
        msg.body = order
        await self.send(msg)

    def get_available_manager(self, order: str) -> Optional[str]:
        order_items = get_order_info(order)
        managers = get_managers(order_items)
        managers = [manager for manager in managers if manager is not self.description]
        if managers:
            return managers[0].name
        return None
