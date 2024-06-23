import asyncio
import random

from Agents.GodAgent import GodAgent
from Agents.FactoryManagerAgent import FactoryManagerAgent
from Agents.GroupManagerAgent import GroupManagerAgent
from Agents.MachineAgent import MachineAgent
from Classes.Util import get_types

from Enums.MachineType import MachineType

if __name__ == '__main__':
    factory_manager = FactoryManagerAgent("test_agent@jabbim.cz/1", "123", 30)
    god_agent = GodAgent(f"test_agent@jabbim.cz/0", "123", factory_manager.jid, 10)
    machines = []
    machine_group_managers = []
    types = get_types()
    for group in range(2, 4):
        manager = GroupManagerAgent(f"test_agent@jabbim.cz/{group}", "123", str(group))
        machine_group_managers.append(manager)
        for machine in range(9):
            type = random.choice(types)
            machine_agent = MachineAgent(f"test_agent@jabbim.cz/{group}{machine}", "123", str(type), str(group))
            machines.append(machine_agent)

    for machine in machines:
        machine.start()
    for manager in machine_group_managers:
        manager.start()
    factory_manager.start()
    god_agent.start()

    try:
        asyncio.get_event_loop().run_forever()
    except KeyboardInterrupt:
        for machine in machines:
            machine.stop()
        for manager in machine_group_managers:
            manager.stop()
        factory_manager.stop()
        god_agent.stop()
