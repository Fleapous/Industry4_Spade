from spade.agent import Agent
from spade.behaviour import PeriodicBehaviour


class ProductionAgent(Agent):
    def __init__(self, jid: str, password: str, *args, **kwargs):
        super().__init__(jid, password, *args, **kwargs)

    async def setup(self) -> None:
        behaviour = ProductionOrderBehaviour()
        self.add_behaviour(behaviour)


class ProductionOrderBehaviour(PeriodicBehaviour):
    async def run(self) -> None:
        pass
