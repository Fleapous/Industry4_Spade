import asyncio
import random


from Agents.GodAgent import GodAgent
from Agents.FactoryManagerAgent import FactoryManagerAgent
from Agents.GroupManagerAgent import GroupManagerAgent
from Agents.MachineAgent import MachineAgent

from Classes.Util import get_types, Log



async def main():
    factory_manager = FactoryManagerAgent("industry41@pimux.de/2", "123123")
    god_agent = GodAgent(f"industry41@pimux.de/1", "123123", factory_manager.jid, 2)
    machines = []
    machine_group_managers = []
    types = get_types()
    for group in range(3, 5):
        manager = GroupManagerAgent(f"industry41@pimux.de/{group}", "123123", str(group))
        machine_group_managers.append(manager)
        for machine in range(10):
            type = random.choice(types)
            machine_agent = MachineAgent(f"industry41@pimux.de/{group}{machine}", "123123", str(type), str(group))
            machines.append(machine_agent)

    for machine in machines:
        machine.start()
        await asyncio.sleep(0.2)
    for manager in machine_group_managers:
        manager.start()
        await asyncio.sleep(0.2)
    await asyncio.sleep(0.5)
    factory_manager.start()
    # await asyncio.sleep(0.2)
    # await god_agent.start()


    while True:
        try:
            await asyncio.sleep(1)
        except KeyboardInterrupt:
            break

    for machine in machines:
        await machine.stop()
    for manager in machine_group_managers:
        await manager.stop()
    await factory_manager.stop()
    await god_agent.stop()
    for entry in Log:
        print(f"{entry}\n")

if __name__ == '__main__':
    asyncio.run(main())

