import datetime
from typing import List

from spade.agent import Agent
from spade.behaviour import PeriodicBehaviour
from spade.message import Message

from Classes.ProductionOrder import ProductionOrder
from Classes.Util import get_item_list_parts
from DF.DF import ServiceDescription, Property, AgentDescription, df


class FactoryManagerAgent(Agent):
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
    def __init__(self, agent: FactoryManagerAgent, period: float, start_at: datetime = None):
        super().__init__(period=period, start_at=start_at)
        self.agent = agent

    async def run(self) -> None:
        print(f"Running behaviour for agent: {self.agent.jid}")

        production_order = self.agent.orders[self.agent.current_order]
        production_order.agent_jid = str(self.agent.jid)
        order = production_order.print_items()
        types = get_item_list_parts(order)
        print(f"order: {order}")

        manager_service: ServiceDescription = ServiceDescription(type="manager")
        for type in types:
            # print(f"the type: {type}")
            type_property: Property = Property(type, None)
            manager_service.add_property(type_property)
        query: AgentDescription = AgentDescription()
        query.add_service(manager_service)
        managers = df.search(query)

        if managers:
            picked_manager = self.pick_manager(managers)
            print(f"manager found {picked_manager.name}")
            msg = Message(to=str(picked_manager.name))
            msg.set_metadata("ontology", "order_request")
            msg.body = production_order.print_as_msg_body()
            await self.send(msg)

        if self.agent.current_order == self.agent.order_count - 1:
            self.kill()
        self.agent.current_order += 1

    def pick_manager(self, managers: list[AgentDescription]):
        return managers[0]

    async def on_end(self):
        await self.agent.stop()
