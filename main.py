import asyncio
import random


from Agents.GodAgent import GodAgent
from Agents.FactoryManagerAgent import FactoryManagerAgent
from Agents.GroupManagerAgent import GroupManagerAgent
from Agents.MachineAgent import MachineAgent

from Classes.Util import get_types, Log
from create_report import plot_average_state_durations


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

    machine_ports = 0
    for machine in machines:
        machine.start(auto_register=True)

        machine.web.add_get("/machineInfo", machine.get_machine_info, "./machineInfo.html")
        machine.web.start(port=10010 + machine_ports)
        await asyncio.sleep(0.2)
        machine_ports += 1
    machine_ports = 0
    for manager in machine_group_managers:
        manager.start(auto_register=True)

        manager.web.add_get("/managerInfo", manager.get_machines, "./group_manager.html")
        manager.web.start(port=10020 + machine_ports)
        await asyncio.sleep(0.2)
        machine_ports += 1
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


    # prodAgent.web.add_get("/hello", prodAgent.get_orders_from_factory_manager, "./hello.html")
    # prodAgent.start(auto_register=True)
    # port = 10000
    # prodAgent.web.start(port=port)
    #
    # prodAgent1.web.add_get("/hello", prodAgent1.get_orders_from_factory_manager, "./hello.html")
    # prodAgent1.start(auto_register=True)
    # port = 10001
    # prodAgent1.web.start(port=port)