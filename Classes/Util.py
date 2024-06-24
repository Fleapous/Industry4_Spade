from typing import Optional

from DF.DF import ServiceDescription, Property, AgentDescription, df
from spade.agent import Agent
from datetime import datetime

from Enums.MachineType import MachineType


def get_sender_info(order: str) -> str:
    dollar_index = order.find('$')

    if dollar_index != -1:
        return order[dollar_index + 1:]
    else:
        return ""


def get_order_info(order: str) -> str:
    dollar_index = order.find('$')
    if dollar_index != -1:
        return order[:dollar_index]
    else:
        return ""


def is_done(order_list: str) -> bool:
    return all(char == '*' for char in order_list)


def get_next_item_index(order_list: str) -> int:
    for index, char in enumerate(order_list):
        if char != '*':
            return index
    return -1


def mark_done(item_index: int, order: str) -> str:
    if 0 <= item_index < len(order):
        order_list = list(order)
        order_list[item_index] = '*'
        return ''.join(order_list)
    else:
        return order


def get_item_list_parts(item_list: str) -> list:
    item_set = set(item_list)
    item_set.discard('*')
    return list(item_set)


def get_item_list_counts(item_list: str) -> dict:
    count_dict: dict[str, int] = {}
    for item in item_list:
        if item in count_dict:
            count_dict[item] += 1
        else:
            count_dict[item] = 1

    return count_dict

def get_managers(order_items: str) -> list[AgentDescription]:
    types = get_item_list_parts(order_items)
    manager_service: ServiceDescription = ServiceDescription(type="manager")
    for type in types:
        type_property: Property = Property(type, None)
        manager_service.add_property(type_property)
    query: AgentDescription = AgentDescription()
    query.add_service(manager_service)
    managers = df.search(query)
    return managers


def get_type(desc: AgentDescription) -> str:
    return desc.services["machine"].properties["type"].value


class LogMessage:
    def __init__(self, time: datetime, message: str):
        self.time = time
        self.message = message


Log: dict[str, LogMessage] = {}


def log(agent: Agent, message: str):
    Log[agent.jid] = LogMessage(datetime.now(), message)
    print(f"[{datetime.now().__str__()}] {agent.jid}: {message}")


def get_types() -> list[str]:
    return [str(s)[-1] for s in set(MachineType)]
