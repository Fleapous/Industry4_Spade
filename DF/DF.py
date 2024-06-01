from typing import List


class Property:
    def __init__(self, name: str, value):
        self.name = name
        self.value = value

    def __eq__(self, other):
        if not isinstance(other, Property):
            return False
        # print(f"selfs name: {self.name}, others name: {other.name}")
        # print(f"selfs value {self.value}, others value {other.value}")
        value_ = self.name == other.name and (other.value is None or self.value == other.value)
        # print(value_)
        return value_

    def __repr__(self):
        return f'{self.name}: {self.value}'


class ServiceDescription:
    def __init__(self, name: str = None, type: str = None):
        self.name: str = name
        self.type: str = type
        self.properties = []

    def __repr__(self):
        return f'{self.name}: {self.type}, {self.properties}'

    def add_property(self, property: Property):
        self.properties.append(property)

    def remove_property(self, property: Property):
        self.properties.remove(property)


class AgentDescription:
    def __init__(self, name: str = None):
        self.name: str = name
        self.services = []

    def __repr__(self):
        return f'{self.name}: {self.services}'

    def add_service(self, service: ServiceDescription):
        self.services.append(service)

    def remove_service(self, service: ServiceDescription):
        self.services.remove(service)


class DF:
    def __init__(self):
        self.agents = []

    def search(self, query: AgentDescription) -> List[AgentDescription]:
        # print(f"query: {query.services}")
        matching_agents = []
        for agent in self.agents:
            if all(
                    any(
                        service.type == query_service.type and all(
                            any(
                                property == query_property for query_property in query_service.properties
                            ) for property in service.properties
                        )
                        for service in agent.services
                    )
                    for query_service in query.services
            ):
                matching_agents.append(agent)

        return matching_agents

    def register(self, agent_description: AgentDescription) -> None:
        self.agents.append(agent_description)
        print(f"agent got registered! {agent_description.name}. the services: {agent_description.services}")
        return


df: DF = DF()
