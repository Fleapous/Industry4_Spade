import asyncio
import random
import time

from Agents.GodAgent import GodAgent
from Agents.FactoryManagerAgent import FactoryManagerAgent
from Agents.GroupManagerAgent import GroupManagerAgent
from Agents.MachineAgent import MachineAgent
from Classes import Util
from Classes.Util import get_types, Log

from Enums.MachineType import MachineType

if __name__ == '__main__':
    factory_manager = FactoryManagerAgent("industry40@pimux.de/1", "123123", 30)
    god_agent = GodAgent(f"industry40@pimux.de/0", "123123", factory_manager.jid, 10)
    machines = []
    machine_group_managers = []
    types = get_types()
    for group in range(2, 4):
        manager = GroupManagerAgent(f"industry40@pimux.de/{group}", "123123", str(group))
        machine_group_managers.append(manager)
        for machine in range(4):
            type = random.choice(types)
            machine_agent = MachineAgent(f"industry40@pimux.de/{group}{machine}", "123123", str(type), str(group))
            machines.append(machine_agent)

    for machine in machines:
        machine.start()
        time.sleep(0.2)
    for manager in machine_group_managers:
        manager.start()
        time.sleep(0.2)
    factory_manager.start()
    time.sleep(0.2)
    god_agent.start()
    time.sleep(0.2)

    try:
        asyncio.get_event_loop().run_forever()
    except KeyboardInterrupt:
        for machine in machines:
            machine.stop()
        for manager in machine_group_managers:
            manager.stop()
        factory_manager.stop()
        god_agent.stop()
        for entry in Log:
            print(f"{entry}\n")
