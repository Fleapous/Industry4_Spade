from datetime import datetime


class Item:
    def __init__(self, item_type: str):
        self.itemType = item_type
        self.isDone = False
        self.completedDate = None

    def mark_done(self):
        self.isDone = True
        self.completedDate = datetime.now()

