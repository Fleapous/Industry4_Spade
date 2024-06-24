import asyncio
from asyncio import Future
from typing import List, Union, Coroutine

import spade.agent
from datetime import datetime, timedelta
from spade.behaviour import PeriodicBehaviour, FSMBehaviour, State, OneShotBehaviour
from spade.message import Message

from Classes.ProductionOrder import ProductionOrder
from Classes.Util import get_managers, log, get_order_info, get_item_list_parts, get_item_list_counts, Orders, \
    OrderRecord
from DF.DF import ServiceDescription, Property, AgentDescription, df
from create_report import plot_average_state_durations, plot_order_times

INIT = "INIT"
WORKING = "WORKING"


class FactoryManagerAgent(spade.agent.Agent):
    def __init__(self, jid: str, password: str, *args, **kwargs):
        super().__init__(jid, password, *args, **kwargs)
        self.order_id = 0

    async def setup(self) -> None:
        behaviour = ProductionOrderBehaviour(self)
        self.add_behaviour(behaviour)

    async def stop(self) -> Union[Coroutine, Future]:
        pass
    async def get_orders_from_factory_manager(self, request):
        production_orders = []

        for b in self.orders:
            prodOrder = {
                "order": str(b.print_items()),
                "orderSentDate": str(b.timeSent)
            }
            production_orders.append(prodOrder)

        return {
            "productionOrders": production_orders
        }


def pick_manager(order: str, managers: list[AgentDescription]):
    items_found = 0
    order_item_counts = get_item_list_counts(order)
    order_items = get_item_list_parts(order)
    best_manager = AgentDescription()
    best_score = -1000
    manager: AgentDescription
    for manager in managers:

        manager_score = 0
        service: ServiceDescription = manager.services["manager"]
        if service:
            property: Property
            for property in service.properties.values():
                order_item: str
                for order_item in order_items:
                    if order_item == property.name:
                        manager_score += property.value * order_item_counts[order_item]
                        items_found += 1
        print(f"manager: {manager}, score: {manager_score}, items: {items_found}, items_count: {len(order_items)}")
        if items_found == len(order_items) and manager_score > best_score:
            best_manager = manager
            best_score = manager_score
    print(f"best manager: {best_manager}, best_score: {best_score}")
    return best_manager


class ProductionOrderBehaviour(OneShotBehaviour):
    def __init__(self, agent: FactoryManagerAgent):
        super().__init__()
        self.agent = agent

    async def on_start(self):
        log(self.agent, "Factory manager starting.")

    async def on_end(self):
        log(self.agent, "Factory manager stopping.")
        await self.agent.stop()

    async def run(self):
        log(self.agent, "Factory manager waiting for orders.")
        while True:
            msg = await self.receive(10)
            if msg is None:
                production_order = ProductionOrder()
                production_order.generate_items()
                order = production_order.print_items()
            else:
                order = get_order_info(msg.body)
            log(self.agent, f"Received Order: {order}, order_id: {self.agent.order_id}. Looking for GOM Managers.")
            Orders.append(OrderRecord(self.agent.order_id))
            self.agent.order_id += 1
            managers = get_managers(order)
            if managers:
                log(self.agent, f"Found {len(managers)} GOM Managers. Choosing optimal candidate.")
                picked_manager = pick_manager(order, managers)
                log(self.agent, f"GOM Manager chosen: {picked_manager.name}. Sending Order: {order}.")
                msg = Message(to=str(picked_manager.name))
                msg.set_metadata("ontology", "order_request")
                msg.set_metadata("order_id", str(self.agent.order_id))
                msg.body = order
                await self.send(msg)
            await asyncio.sleep(1)
