import random
from datetime import datetime
from typing import List

from Classes.Item import Item
from Enums.MachineType import MachineType


class ProductionOrder:
    def __init__(self):
        self.agent_jid: str = ""
        self.items: List[Item] = []
        self.index = 0
        self.timeSent = None
        self.timeReceived = None

    def __repr__(self):
        return f'ProductionOrder(agent_jid={self.agent_jid}, index={self.index}, timeSent={self.timeSent}, timeReceived={self.timeReceived})'

    def generate_items(self, min_items=1, max_items=10):
        num_items = random.randint(min_items, max_items)
        for _ in range(num_items):
            item_type = random.choice(list(MachineType))
            item = Item(item_type)
            self.items.append(item)

    def get_current_item(self):
        if self.index < len(self.items):
            return self.items[self.index]
        else:
            return None

    def print_items(self):
        item_types = [item.itemType.name for item in self.items]
        return "".join(item_types)

    def print_as_msg_body(self):
        item_types = [item.itemType.name for item in self.items]
        return "".join(item_types) + "$" + self.agent_jid

    def mark_item_done(self):
        if self.index < len(self.items):
            current_item = self.items[self.index]
            current_item.mark_done()
            self.index += 1
