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

from DF.DF import ServiceDescription, Property, AgentDescription, df
from Classes.ProductionOrder import ProductionOrder


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

    def get_item_list(self) -> str:
        # TODO get the items from
        return "ABC"

    async def on_start(self) -> None:
        print("started to look for orders")
        items = self.get_item_list()  # TODO change this with items
        manager_service: ServiceDescription = ServiceDescription(type="manager")
        for item in items:
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
            self.edit_item_service()

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
        print(f"order received!! order: {msg.body}")

    def finished_order_received(self):
        pass

    def edit_item_service(self):
        pass
