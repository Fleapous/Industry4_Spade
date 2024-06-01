import asyncio

from Agents.MachineAgent import MachineAgent
from Agents.ManagerAgent import ManagerAgent
from Agents.ProductionAgent import ProductionAgent
from Agents.FactoryManagerAgent import FactoryManagerAgent

if __name__ == '__main__':
    # machines = \
    #     [
    #         MachineAgent("test_agent@jabbim.pl/0", "123", "A"),
    #         MachineAgent("test_agent@jabbim.pl/1", "123", "A"),
    #         MachineAgent("test_agent@jabbim.pl/2", "123", "B"),
    #         MachineAgent("test_agent@jabbim.pl/3", "123", "C")
    #     ]
    # manager = ManagerAgent("test_agent@jabbim.pl/4", "123")
    #
    # for machine in machines:
    #     machine.start()
    # manager.start()

    prodAgents = \
        [
            ProductionAgent("test_agent@jabbim.pl/0", "123", 30),
            # ProductionAgent("test_agent@jabbim.pl/1", "123", 6)
        ]

    factoryAgent = FactoryManagerAgent("test_agent@jabbim.pl/1", "123")

    for prodAgent in prodAgents:
        prodAgent.start()
    factoryAgent.start()

    try:
        asyncio.get_event_loop().run_forever()
    except KeyboardInterrupt:
        for prodAgent in prodAgents:
            prodAgent.stop()
        factoryAgent.stop()
