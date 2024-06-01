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

from DF.DF import ServiceDescription, Property, AgentDescription, df


class FactoryManagerAgent(Agent):
    def __init__(self, jid: str, password: str, *args, **kwargs):
        super().__init__(jid, password, *args, **kwargs)

    async def setup(self) -> None:
        behav = GetOrderBehaviour(self)
        self.add_behaviour(behav)


class GetOrderBehaviour(OneShotBehaviour):
    def __init__(self, agent: FactoryManagerAgent):
        super().__init__()
        self.agent = agent

    async def run(self) -> None:

        print("started to look for orders")
        items = self.get_item_list()
        manager_service: ServiceDescription = ServiceDescription(type="manager")
        for item in items:
            type_property: Property = Property(item, 10)
            manager_service.add_property(type_property)
        agent_description: AgentDescription = AgentDescription(f"factory_agent number {self.agent.jid}")
        agent_description.add_service(manager_service)
        df.register(agent_description)

    def get_item_list(self) -> str:
        return "ABC"
