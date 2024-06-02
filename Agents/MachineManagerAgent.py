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
from typing import List

from spade.agent import Agent
from spade.behaviour import CyclicBehaviour, OneShotBehaviour
from spade.template import Template

from Classes.Util import get_order_info, get_sender_info, is_done, get_next_item_index, get_item_list_parts
from DF.DF import ServiceDescription, Property, AgentDescription, df
from Classes.ProductionOrder import ProductionOrder
from Enums.MachineType import MachineType


class MachineManagerAgent(Agent):
    def __init__(self, jid: str, password: str, *args, **kwargs):
        super().__init__(jid, password, *args, **kwargs)

    async def setup(self) -> None:
        # TODO no idea why we need this
        # order_receive = Template()
        # order_receive.metadata = {"ontology": "receiveOrder"}
        #
        # completed_order_receive = Template()
        # completed_order_receive.metadata = {"ontology": "completeOrder"}
        #
        # maintenance = Template()
        # maintenance.metadata = {"ontology": "maintenance"}

        main = MainBehaviour(self)
        self.add_behaviour(main)


class MainBehaviour(CyclicBehaviour):
    def __init__(self, agent: MachineManagerAgent):
        super().__init__()
        self.agent = agent
        self.orders: List[ProductionOrder] = []
        self.items: List[str] = []

    async def on_start(self) -> None:
        print("started to look for orders")
        self.get_item_list()
        manager_service: ServiceDescription = ServiceDescription(type="manager")
        for item in self.items:
            type_property: Property = Property(item, 10)
            manager_service.add_property(type_property)
        agent_description: AgentDescription = AgentDescription(self.agent.jid)
        agent_description.add_service(manager_service)
        df.register(agent_description)

    async def run(self) -> None:
        msg = await self.receive(timeout=120)
        if msg:
            print(f"agent: {self.agent.jid}, received msg")
        else:
            print(f"agent: {self.agent.jid}, did not receive a msg for 2 minutes.")
            self.kill()

        if msg.get_metadata("ontology") == "order_request":
            self.order_received(msg)
        elif msg.get_metadata("ontology") == "order_finished":
            self.finished_order_received()
        elif msg.get_metadata("ontology") == "scheduled_maintenance":
            self.get_item_list()

        """
            wait for messages
            possible messages:
                order from factory manager
                order from machine manager
                order return from machine
                machine scheduled maintenance
                
            order from factory manager and order from machine manager:
                get order try to assign onto machine if not look for another manager that has it
            
            order return from machine: 
                if order done send it to factory manager if not look for a new manager
                
            machine scheduled maintenance:
                adit the service accordingly 
                
        """

    def order_received(self, msg):
        order = msg.body
        print(f"order received!! order: {get_order_info(order)}. order sender: {get_sender_info(order)}")
        if not is_done(get_order_info(order)):
            machine = self.find_machine(order)
            if machine != "":
                self.send_order(order, machine)
            else:
                manager = self.get_available_manager(order)
                if manager != "":
                    self.send_order(order, manager)
        else:
            self.finished_order_received()

    def finished_order_received(self):
        pass

    def get_item_list(self):
        all_machine_types = list(MachineType)
        self.items = all_machine_types

    def find_machine(self, order: str) -> str:
        order_items = get_order_info(order)
        item_index = get_next_item_index(order_items)
        item = order_items[item_index]

        machine_service: ServiceDescription = ServiceDescription(type=f"machine${str(self.agent.jid)}")
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

    def get_available_manager(self, order: str) -> str:
        order_items = get_order_info(order)
        items = get_item_list_parts(order_items)

        manager_service: ServiceDescription = ServiceDescription(type="manager")
        for item in items:
            type_property: Property = Property(item, None)
            manager_service.add_property(type_property)
        query: AgentDescription = AgentDescription()
        query.add_service(manager_service)
        managers = df.search(query)
        if managers:
            # TODO add sm logic to it and dont pick the same agent
            return managers[0].name
        return ""
