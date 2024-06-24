import asyncio
import random
from typing import Optional

from spade.agent import Agent
from spade.behaviour import FSMBehaviour, State
from spade.message import Message

from Classes.Util import log, get_order_info, get_next_item_index, mark_done
from DF.DF import df, AgentDescription, ServiceDescription, Property


class MachineAgent(Agent):
    def __init__(self, jid: str, password: str, type: str, group: str, *args, **kwargs):
        super().__init__(jid, password, *args, **kwargs)
        self.type = type
        self.group = group
        self.current_order: Optional[str] = None
        self.previous_orders: dict[str, str] = {}
        self.previous_agent: str = ""
        self.manager: str = ""
        self.description: AgentDescription = AgentDescription()

    async def setup(self) -> None:
        self.presence.approve_all = True
        behaviour = MachineBehaviour()
        self.add_behaviour(behaviour)

    def set_busy(self, busy: bool) -> None:
        log(self, f"Setting busy to {busy}. Services: {self.description.services}")
        self.description.services['machine'].properties['busy'].value = busy
        df.update(self.description)

class MachineBehaviour(FSMBehaviour):
    def __init__(self):
        super().__init__()

        self.add_state("Init", self.InitState(), True)
        self.add_state("Idle", self.IdleState())
        self.add_state("Working", self.WorkingState())
        self.add_state("Maintenance", self.MaintenanceState())

        self.add_transition("Init", "Idle")
        self.add_transition("Idle", "Working")
        self.add_transition("Working", "Idle")
        self.add_transition("Idle", "Maintenance")
        self.add_transition("Working", "Maintenance")

    async def on_start(self) -> None:
        log(self.agent, "Machine starting.")
        self.presence.on_unavailable = self.on_unavailable

    async def on_end(self) -> None:
        log(self.agent, "Machine stopping.")
        await self.agent.stop()

    def on_unavailable(self, jid, stanza) -> None:
        order = self.agent.previous_orders.get(jid)
        if order is not None:
            self.agent.handle_order(order)

    async def handle_order(self, order: str) -> None:
        machine = self.get_next_machine()
        if machine:
            self.agent.previous_orders[order] = machine.name
            self.agent.cancel_order = None
            await self.send_order(machine.name, order)
        else:
            self.agent.previous_orders[order] = self.agent.manager
            self.agent.cancel_order = None
            await self.handle_order_machine_missing(order)

    def get_next_machine(self) -> Optional[AgentDescription]:
        machines = self.get_machines()
        if machines:
            return machines[0]
        return None

    async def handle_order_machine_missing(self, order: str) -> None:
        await self.send_order(self.agent.manager, order)

    async def send_order(self, jid: str, order: str, ontology: str = "order_request") -> None:
        msg = Message(to=jid)
        msg.set_metadata("ontology", ontology)
        msg.body = order
        await self.send(msg)

    class InitState(State):
        async def run(self) -> None:
            await asyncio.sleep(1)
            machine_service: ServiceDescription = ServiceDescription(type="machine")
            type_property: Property = Property("type", self.agent.type)
            machine_service.add_property(type_property)
            group_property: Property = Property("group", self.agent.group)
            machine_service.add_property(group_property)
            busy_property: Property = Property("busy", False)
            machine_service.add_property(busy_property)
            agent_description: AgentDescription = AgentDescription(self.agent.jid)
            agent_description.add_service(machine_service)
            self.agent.description = agent_description
            df.register(agent_description)
            log(self.agent, "Machine registered with the DF.")
            log(self.agent, "Awaiting message from Manager.")
            while True:
                msg = await self.receive(10)
                if msg:
                    self.agent.manager = msg.sender
                    log(self.agent, f"Subscribing to other Machines in Group {self.agent.group}.")
                    machines = self.get_machines()
                    log(self.agent, f"Machines found: {len(machines)}.")
                    machine: AgentDescription
                    for machine in machines:
                        #print(f'Subscribe to {machine.name}.')
                        self.presence.subscribe(str(machine.name))
                        await asyncio.sleep(0.2)
                    break
                await asyncio.sleep(1)
            log(self.agent, "Transition to Idle state.")
            self.set_next_state("Idle")

        def get_machines(self) -> list[AgentDescription]:
            machine_service: ServiceDescription = ServiceDescription(type="machine")

            group = self.agent.group
            group_property: Property = Property("group", group)
            machine_service.add_property(group_property)

            query: AgentDescription = AgentDescription()
            query.add_service(machine_service)
            machines = df.search(query)
            return [machine for machine in machines if machine.name != self.agent.jid]

    class IdleState(State):
        async def run(self):
            log(self.agent, "Starting Idle state.")
            self.agent.set_busy(False)
            while True:
                msg = await self.receive(10)
                if msg:
                    log(self.agent, f"Received message {msg}")
                    if msg.metadata["ontology"] == "order_request":
                        order = get_order_info(msg.body)
                        log(self.agent, f"Order received: {order}.")
                        self.agent.current_order = order
                        chance = random.random()
                        if chance < self.agent.maintenance_probability:
                            log(self.agent, "Transition to Maintenance state.")
                            self.set_next_state("Maintenance")
                        else:
                            self.agent.previous_agent = msg.sender
                            log(self.agent, "Transition to Working state.")
                            self.set_next_state("Working")
                        break
                    elif msg.metadata["ontology"] == "order_part_completed":
                        order = get_order_info(msg.body)
                        self.agent.previous_orders.pop(order, None)
                        log(self.agent, f"Order progress confirmation received: {order}.")
                        continue
                await asyncio.sleep(1)

    class WorkingState(State):
        async def run(self):
            self.agent.set_busy(True)
            order = self.agent.current_order
            order = await self.do_work(order)
            await self.handle_order(order)
            log(self.agent, "Transition to Idle state.")
            self.set_next_state("Idle")

        async def do_work(self, order) -> str:
            next_index = get_next_item_index(order)
            order = mark_done(next_index, order)
            await self.send_order(self.agent.previous_order, order, "order-part-completed")
            self.agent.previous_agent = ""
            return order

        async def handle_order(self, order: str) -> None:
            machine = self.get_next_machine()
            if machine:
                self.agent.previous_orders[order] = machine.name
                self.agent.cancel_order = None
                await self.send_order(machine.name, order)
            else:
                self.agent.previous_orders[order] = self.agent.manager
                self.agent.cancel_order = None
                await self.handle_order_machine_missing(order)

        def get_next_machine(self) -> Optional[AgentDescription]:
            machines = self.get_machines()
            if machines:
                return machines[0]
            return None

        async def handle_order_machine_missing(self, order: str) -> None:
            await self.send_order(self.agent.manager, order)

        async def send_order(self, jid: str, order: str, ontology: str = "order_request") -> None:
            msg = Message(to=jid)
            msg.set_metadata("ontology", ontology)
            msg.body = order
            await self.send(msg)

        def get_machines(self) -> list[AgentDescription]:
            machine_service: ServiceDescription = ServiceDescription(type="machine")

            next_item_index = get_next_item_index(self.agent.current_order)
            type = self.agent.current_order[next_item_index]
            type_property: Property = Property("type", type)
            machine_service.add_property(type_property)

            group = self.agent.group
            group_property: Property = Property("group", group)
            machine_service.add_property(group_property)

            busy_property: Property = Property("busy", False)
            machine_service.add_property(busy_property)

            query: AgentDescription = AgentDescription()
            query.add_service(machine_service)
            return df.search(query)

    class MaintenanceState(State):
        async def run(self):
            self.agent.set_busy(True)
            time = random.randint(15, 60)
            log(self.agent, f"Maintenance. The machine will be offline for {time}s")
            self.presence.set_unavailable()
            await asyncio.sleep(time)
            log(self.agent, f"Maintenance over.")
            self.presence.set_available()
            log(self.agent, "Transition to Idle state.")
            self.set_next_state("Idle")