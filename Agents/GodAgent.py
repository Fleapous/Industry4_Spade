from spade.agent import Agent
from spade.behaviour import PeriodicBehaviour
from spade.message import Message

from datetime import datetime, timedelta

from Classes.ProductionOrder import ProductionOrder

from Classes.Util import log


class GodAgent(Agent):
    def __init__(self, jid: str, password: str, factory_manager_jid: str, period: int, *args, **kwargs):
        super().__init__(jid, password, *args, **kwargs)
        self.factory_manager_jid = factory_manager_jid
        self.period = period

    def setup(self) -> None:
        start_at = datetime.now() + timedelta(seconds=5)
        behaviour = GodAgentBehaviour(self, period=self.period, start_at=start_at)
        self.add_behaviour(behaviour)


class GodAgentBehaviour(PeriodicBehaviour):
    def __init__(self, agent: GodAgent, period: float, start_at: datetime = None):
        super().__init__(period=period, start_at=start_at)
        self.agent = agent

    async def run(self) -> None:
        log(self.agent, "Behaviour starting")

        order = ProductionOrder()
        order.generate_items()
        order.agent_jid = str(self.agent.jid)
        order_items = order.print_items()

        log(self.agent, f"New Order: {order_items}")

        log(self.agent, f"Sending Order to Factory Manager: {self.agent.factory_manager_jid}")
        msg = Message(to=str(self.agent.factory_manager_jid))
        msg.set_metadata("ontology", "order_request")
        msg.body = order.print_as_msg_body()
        await self.send(msg)