import datetime
from typing import List

from spade.agent import Agent
from spade.behaviour import PeriodicBehaviour

from Classes.ProductionOrder import ProductionOrder
from DF.DF import ServiceDescription, Property, AgentDescription, df


class ProductionAgent(Agent):
    def __init__(self, jid: str, password: str, order_count: int = 5, *args, **kwargs):
        super().__init__(jid, password, *args, **kwargs)
        self.order_count = order_count
        self.current_order = 0
        self.orders: List[ProductionOrder] = []

    async def setup(self) -> None:
        # Generate the specified number of orders
        for _ in range(self.order_count):
            order = ProductionOrder()
            order.generate_items()
            self.orders.append(order)

        # Start the behaviour
        start_at = datetime.datetime.now() + datetime.timedelta(seconds=5)
        behaviour = ProductionOrderBehaviour(self, period=2, start_at=start_at)
        self.add_behaviour(behaviour)


class ProductionOrderBehaviour(PeriodicBehaviour):
    def __init__(self, agent: ProductionAgent, period: float, start_at: datetime = None):
        super().__init__(period=period, start_at=start_at)
        self.agent = agent

    async def run(self) -> None:
        print(f"Running behaviour for agent: {self.agent.jid}")

        order = self.agent.orders[self.agent.current_order].print_items()
        types = set(order)
        print(f"order: {order}")
        manager_service: ServiceDescription = ServiceDescription(type="manager")
        for type in types:
            # print(f"the type: {type}")
            type_property: Property = Property(type, None)
            manager_service.add_property(type_property)
        query: AgentDescription = AgentDescription()
        query.add_service(manager_service)

        managers = df.search(query)
        self.pick_manager(managers)

        if self.agent.current_order == self.agent.order_count - 1:
            self.kill()
        self.agent.current_order += 1

    def pick_manager(self, managers: list[AgentDescription]):
        print(f"manager found {managers}")

    async def on_end(self):
        await self.agent.stop()
