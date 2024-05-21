from datetime import datetime


class Item:
    def __init__(self, itemType):
        self.itemType = itemType
        self.isDone = False
        self.completedDate = None

    def mark_done(self):
        self.isDone = True
        self.completedDate = datetime.now()

