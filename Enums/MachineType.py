from enum import Enum


class MachineType(Enum):
    A = 1
    B = 2
    C = 3


MachineType = Enum('MachineType', ('A', 'B', 'C'))
