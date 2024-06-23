from DF.DF import ServiceDescription, Property, AgentDescription, df
from spade.agent import Agent
from datetime import datetime


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


def mark_done(item_index: int, order_list: str) -> str:
    if 0 <= item_index < len(order_list):
        order_list = list(order_list)
        order_list[item_index] = '*'
        return ''.join(order_list)
    else:
        return order_list


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
    return list(desc.services["Machine"].properties)[0]

def log(agent: Agent, message: str):
    print(f"[{datetime.time}] {agent.jid}: {message}")