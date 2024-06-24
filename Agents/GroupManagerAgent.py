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
from typing import List, Optional, TypedDict

from spade.agent import Agent
import spade.behaviour
import spade.template
from spade.message import Message

from Classes.Util import get_order_info, get_sender_info, is_done, get_next_item_index, get_item_list_parts, \
    get_managers, log, get_type, get_types
from DF.DF import ServiceDescription, Property, AgentDescription, df
from Classes.ProductionOrder import ProductionOrder
from Enums.MachineType import MachineType


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
        machine = self.machines[jid]
        if machine["available"]:
            return

        type = get_type(machine["description"])
        if self.description.services["manager"].properties[type].value is int:
            self.description.services["manager"].properties[type].value += 1
        df.update(self.description)
        log(self.agent, f"Machine {jid} of type {type} is available.")
        self.machines[jid]["available"] = True

    def on_unavailable(self, jid, stanza) -> None:
        machine = self.machines[jid]
        if not machine["available"]:
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
                log(self.agent, f"Received message")

                if msg.get_metadata("ontology") == "order_request":
                    await self.order_received(msg.body)
                elif msg.get_metadata("ontology") == "order_machine_missing":
                    await self.order_missing_machine_received(msg.body)
                else:
                    log(self.agent, f"Unknown ontology: {msg.get_metadata('ontology')}")
            else:
                await asyncio.sleep(1)

    async def order_received(self, order: str) -> None:
        order = get_order_info(order)
        log(self.agent, f"Received Order: {order}.")
        if is_done(order):
            return

        machine = self.find_machine(order)
        if machine:
            await self.send_order(order, machine)
        else:
            await self.order_missing_machine_received(order)

    async def order_missing_machine_received(self, order: str) -> None:
        order = get_order_info(order)
        manager = self.get_available_manager(order)
        await self.send_order(order, manager)

    def find_machine(self, order: str) -> str:
        order_items = get_order_info(order)
        item_index = get_next_item_index(order_items)
        item = order_items[item_index]

        machine_service: ServiceDescription = ServiceDescription(type="machine")
        type_property: Property = Property(item, None)
        machine_service.add_property(type_property)

        query: AgentDescription = AgentDescription()
        query.add_service(machine_service)

        machines = df.search(query)

        if machines:
            # TODO add sm logic here for picking the good one
            return machines[0].name
        return ""

    async def send_order(self, order: str, agent_jid: str) -> None:
        msg = Message(to=agent_jid)
        msg.set_metadata("ontology", "order_request")
        msg.body = order
        await self.send(msg)

    def get_available_manager(self, order: str) -> Optional[str]:
        order_items = get_order_info(order)
        managers = get_managers(order_items)
        managers = [manager for manager in managers if manager is not self.description]
        if managers:
            # TODO add sm logic to it and dont pick the same agent
            return managers[0].name
        return None
