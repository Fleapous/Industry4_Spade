from spade.agent import Agent
from spade.behaviour import OneShotBehaviour
from DF.DF import df, AgentDescription, ServiceDescription, Property


class MachineAgent(Agent):
    def __init__(self, jid: str, password: str, type: str, *args, **kwargs):
        super().__init__(jid, password, *args, **kwargs)
        self.type = type

    async def setup(self) -> None:
        behaviour = TestBehaviour()
        self.add_behaviour(behaviour)


class TestBehaviour(OneShotBehaviour):

    async def run(self) -> None:
        print(self.agent.jid, ": machine setup, type ", self.agent.type)
        machine_service: ServiceDescription = ServiceDescription(
            name="machine_service",
            type="machine"
        )
        type_property: Property = Property("machine_type", self.agent.type)
        machine_service.add_property(type_property)

        agent_description: AgentDescription = AgentDescription(self.agent.jid)
        agent_description.add_service(machine_service)
        print(self.agent.jid, ": machine registers")
        df.register(agent_description)

    def __init__(self):
        super().__init__()
