import asyncio
from typing import List

import spade.agent
from datetime import datetime, timedelta
from spade.behaviour import PeriodicBehaviour, FSMBehaviour, State, OneShotBehaviour
from spade.message import Message

from Classes.ProductionOrder import ProductionOrder
from Classes.Util import get_managers, log, get_order_info, get_item_list_parts, get_item_list_counts
from DF.DF import ServiceDescription, Property, AgentDescription, df


INIT = "INIT"
WORKING = "WORKING"


class FactoryManagerAgent(spade.agent.Agent):
    def __init__(self, jid: str, password: str, period: int = 2, *args, **kwargs):
        super().__init__(jid, password, *args, **kwargs)
        self.period = period

    async def setup(self) -> None:
        await asyncio.sleep(5)
        behaviour = ProductionOrderBehaviour(self)
        self.add_behaviour(behaviour)


def pick_manager(order: str, managers: list[AgentDescription]):
    items_found = 0
    order_item_counts = get_item_list_counts(order)
    order_items = get_item_list_parts(order)
    best_manager = AgentDescription()
    best_score = -1000
    manager: AgentDescription
    for manager in managers:
        manager_score = 0
        service: ServiceDescription = manager.services["Manager"]
        if service:
            property: Property
            for property in service.properties:
                order_item: str
                for order_item in order_items:
                    if order_item == property.name:
                        manager_score += property.value * order_item_counts[order_item]
                        items_found += 1
        if items_found == order_items.count and manager_score > best_score:
            best_manager = manager
            best_score = manager_score
    return best_manager


class ProductionOrderBehaviour(OneShotBehaviour):
    def __init__(self, agent: FactoryManagerAgent):
        super().__init__()
        self.agent = agent

    async def on_start(self):
        log(self.agent, "Factory manager starting.")

    async def on_end(self):
        log(self.agent, "Factory manager finished.")
        await self.agent.stop()

    async def run(self):
        while True:
            msg = await self.receive(10)
            if msg is None:
                continue
            order = msg.body
            order_items = get_order_info(order)
            log(self.agent, f"Received Order: {order_items}. Looking for GOM Managers.")
            managers = get_managers(order_items)
            if managers:
                log(self.agent, f"Found {managers.count} GOM Managers. Choosing optimal candidate.")
                picked_manager = pick_manager(managers)
                log(self.agent, f"GOM Manager chosen: {picked_manager.name}. Sending Order: {order_items}.")
                msg = Message(to=str(picked_manager.name))
                msg.set_metadata("ontology", "order_request")
                msg.body = order_items
                await self.send(msg)
            await asyncio.sleep(1)
