import asyncio

from spade.agent import Agent
from spade.behaviour import OneShotBehaviour

from DF.DF import df, AgentDescription, ServiceDescription, Property


class ManagerAgent(Agent):
    def __init__(self, jid: str, password: str, *args, **kwargs):
        super().__init__(jid, password, *args, **kwargs)

    async def setup(self) -> None:
        behaviour = TestBehaviour()
        self.add_behaviour(behaviour)


class TestBehaviour(OneShotBehaviour):

    async def run(self) -> None:
        await asyncio.sleep(3)
        print(self.agent.jid, ": manager setup")

        descriptions = self.get_machines("A")
        self.print_response(descriptions)
        descriptions = self.get_machines("B")
        self.print_response(descriptions)
        descriptions = self.get_machines("C")
        self.print_response(descriptions)

    def print_response(self, descriptions: []) -> None:
        print(self.agent.jid, ": received responses (", len(descriptions), "):")
        for agent_description in descriptions:
            print(agent_description)

    def get_machines(self, type: str) -> []:
        print(self.agent.jid, f": manager requests type {type}")
        machine_service: ServiceDescription = ServiceDescription(type="machine")
        type_property: Property = Property("machine_type", type)
        machine_service.add_property(type_property)

        query: AgentDescription = AgentDescription()
        query.add_service(machine_service)

        print(self.agent.jid, ": query sent")
        return df.search(query)

    def __init__(self):
        super().__init__()
