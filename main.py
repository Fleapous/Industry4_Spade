import asyncio

from Agents.MachineAgent import MachineAgent
from Agents.ManagerAgent import ManagerAgent

if __name__ == '__main__':
    machines = \
        [
            MachineAgent("test_agent@jabbim.pl/0", "123", "A"),
            MachineAgent("test_agent@jabbim.pl/1", "123", "A"),
            MachineAgent("test_agent@jabbim.pl/2", "123", "B"),
            MachineAgent("test_agent@jabbim.pl/3", "123", "C")
        ]
    manager = ManagerAgent("test_agent@jabbim.pl/4", "123")

    for machine in machines:
        machine.start()
    manager.start()

    try:
        asyncio.get_event_loop().run_forever()
    except KeyboardInterrupt:
        for machine in machines:
            machine.stop()
        manager.stop()
