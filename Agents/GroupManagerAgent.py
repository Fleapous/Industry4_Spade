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
from typing import List, Optional

from spade.agent import Agent
import spade.behaviour
import spade.template

from Classes.Util import get_order_info, get_sender_info, is_done, get_next_item_index, get_item_list_parts, \
    get_managers, log, get_type
from DF.DF import ServiceDescription, Property, AgentDescription, df
from Classes.ProductionOrder import ProductionOrder
from Enums.MachineType import MachineType


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
        self.machines: dict[str, {bool, AgentDescription}] = {}
        self.description: AgentDescription = AgentDescription()

    async def on_start(self) -> None:
        log(self.agent, "GoM Manager Bahaviour starting")
        log(self.agent, "Looking for Machines in Group")
        self.machines = await self.get_machines()
        await self.setup_presence()
        log(self.agent, f"Machines found: {self.machines}")
        self.description = await self.register()
        log(self.agent, f"Registering Manager Service with the DF: {self.description}")
        log(self.agent, "GoM Manager Bahaviour startup finished")

    async def setup_presence(self) -> None:
        self.presence.on_available = self.on_available
        self.presence.on_unavailable = self.on_unavailable
        self.presence.set_available()
        machine_jid: str
        for machine_jid in self.machines.keys():
            self.presence.subscribe(machine_jid)

    def on_available(self, jid) -> None:
        machine = self.machines[jid]
        if machine["available"]:
            return

        type = get_type(machine["machine"])
        self.description.services["Manager"].properties[type] += 1
        df.update(self.description)
        log(self.agent, f"Machine {jid} of type {type} is available.")
        self.machines[jid]["available"] = True

    def on_unavailable(self, jid) -> None:
        machine = self.machines[jid]
        if not machine["available"]:
            return

        type = get_type(machine["machine"])
        self.description.services["Manager"].properties[type] -= 1
        df.update(self.description)
        log(self.agent, f"Machine {jid} of type {type} is unavailable.")
        self.machines[jid]["available"] = False

    async def get_machines(self) -> dict[str, {bool, AgentDescription}]:
        machine_service: ServiceDescription = ServiceDescription(type="machine")
        group_property: Property = Property("group", self.agent.group)
        machine_service.add_property(group_property)
        query: AgentDescription = AgentDescription()
        query.add_service(machine_service)
        machines = df.search(query)
        return {machine.name: {"available": True, "description": machine} for machine in machines}

    async def register(self) -> AgentDescription:

        types = set(list(MachineType))
        machine_type_counts = {type: 0 for type in types}

        machine: AgentDescription
        for machine in self.machines:
            service: ServiceDescription = machine.services["machine"]
            property: Property
            properties = service.properties.values()
            for property in properties:
                machine_type_counts[property.name] += 1

        manager_service: ServiceDescription = ServiceDescription(type="manager")
        for machine_type, count in machine_type_counts.items():
            type_property: Property = Property(machine_type, count)
            manager_service.add_property(type_property)

        agent_description: AgentDescription = AgentDescription(self.agent.jid)
        agent_description.add_service(manager_service)
        df.register(agent_description)
        return agent_description

    async def run(self) -> None:
        msg = await self.receive()
        log(self.agent, f"Received message")

        if msg.get_metadata("ontology") == "order_request":
            self.order_received(msg.body)
        elif msg.get_metadata("ontology") == "order_machine_missing":
            self.order_missing_machine_received(msg.body)
        else:
            log(self.agent, f"Unknown ontology: {msg.get_metadata('ontology')}")

    def order_received(self, order: str) -> None:
        order = get_order_info(order)
        log(self.agent, f"Received Order: {order}.")
        if is_done(order):
            return

        machine = self.find_machine(order)
        if machine:
            self.send_order(order, machine)
        else:
            self.order_missing_machine_received(order)


    def order_missing_machine_received(self, order: str) -> None:
        order = get_order_info(order)

    def find_machine(self, order: str) -> str:
        order_items = get_order_info(order)
        item_index = get_next_item_index(order_items)
        item = order_items[item_index]

        machine_service: ServiceDescription = ServiceDescription(type="Machine")
        type_property: Property = Property(item, None)
        machine_service.add_property(type_property)

        query: AgentDescription = AgentDescription()
        query.add_service(machine_service)

        machines = df.search(query)

        if machines:
            # TODO add sm logic here for picking the good one
            return machines[0].name
        return ""

    def send_order(self, order: str, agent_jid: str) -> bool:
        pass

    def get_available_manager(self, order: str) -> Optional[str]:
        order_items = get_order_info(order)
        managers = get_managers(order_items)
        if managers:
            # TODO add sm logic to it and dont pick the same agent
            return managers[0].name
        return None
