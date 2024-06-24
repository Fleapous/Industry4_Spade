import asyncio

from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message


from Classes.ProductionOrder import ProductionOrder

from Classes.Util import log


class GodAgent(Agent):
    def __init__(self, jid: str, password: str, factory_manager_jid: str, period: int, *args, **kwargs):
        super().__init__(jid, password, *args, **kwargs)

        self.factory_manager_jid = factory_manager_jid
        self.period = period

    def setup(self) -> None:
        behaviour = self.GodAgentBehaviour()
        self.add_behaviour(behaviour)


    class GodAgentBehaviour(CyclicBehaviour):
        def __init__(self):
            super().__init__()

        async def on_start(self):
            log(self.agent, "God agent starting.")

        async def on_end(self):
            log(self.agent, "God agent stopping.")
            await self.agent.stop()

        async def run(self) -> None:
            while True:
                log(self.agent, "God agent running")

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
                await asyncio.sleep(self.agent.period)
