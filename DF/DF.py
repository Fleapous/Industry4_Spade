from typing import List


class Property:
    def __init__(self, name: str, value):
        self.name = name
        self.value = value

    def __eq__(self, other):
        if not isinstance(other, Property):
            return False
        #print(f"selfs name: {self.name}, others name: {other.name}")
        #print(f"selfs value {self.value}, others value {other.value}")
        value_ = self.name == other.name and (other.value is None or self.value == other.value)
        #print(value_)
        return value_

    def __repr__(self):
        return f'{self.name}: {self.value}'


class ServiceDescription:
    def __init__(self, name: str = None, type: str = None):
        self.name: str = name
        self.type: str = type
        self.properties: dict[str, Property] = {}

    def __repr__(self):
        string = f'{self.name}: {self.type} ['
        for property in self.properties.values():
            string += f' {property} '
        return string + ']'

    def add_property(self, property: Property):
        self.properties[property.name] = property

    def update_property(self, property: Property) -> None:
        self.properties[property.name] = property

    def remove_property(self, property: Property):
        self.properties.pop(property.name, "not found")


class AgentDescription:
    def __init__(self, name: str = None):
        self.name: str = name
        self.services: dict[str, ServiceDescription] = {}

    def __repr__(self):
        string = f'{self.name}: ['
        for service in self.services.values():
            string += f'{service}'
        return string + ']'

    def add_service(self, service: ServiceDescription):
        self.services[service.type] = service

    def remove_service(self, service: ServiceDescription):
        self.services.pop(service.type, "not found")


class DF:
    def __init__(self):
        self.agents: dict[str, AgentDescription] = {}

    def search(self, query: AgentDescription) -> list[AgentDescription]:
        # print(f"query: {query.services}")
        matching_agents = []
        agent: AgentDescription
        service: ServiceDescription
        query_service: ServiceDescription
        property: Property
        for agent in self.agents.values():
            if all(
                    any(
                        service.type == query_service.type and all(
                            any(
                                query_property.name == property.name and
                                (query_property.value is None or
                                 query_property.value == property.value)
                                for property in service.properties.values()
                            ) for query_property in query_service.properties.values()
                        )
                        for service in agent.services.values()
                    )
                    for query_service in query.services.values()
            ):
                matching_agents.append(agent)
        return matching_agents

    def register(self, agent_description: AgentDescription) -> None:
        self.agents[agent_description.name] = agent_description
        print(f"[DF] Agent registered: {agent_description}")
        return

    def update(self, agent_description: AgentDescription) -> None:
        self.agents[agent_description.name] = agent_description

    def remove(self, agent_description: AgentDescription) -> None:
        self.agents.pop(agent_description.name, "not found")


df: DF = DF()
