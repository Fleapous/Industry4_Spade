import asyncio
import random
import re
from datetime import datetime
from typing import Optional

from spade.agent import Agent
from spade.behaviour import FSMBehaviour, State
from spade.message import Message

from Classes.Util import log, get_order_info, get_next_item_index, mark_done, is_done, Orders
from Classes.Util import log, get_order_info, get_next_item_index, mark_done, Log
from DF.DF import df, AgentDescription, ServiceDescription, Property
from create_report import calculate_state_percentages_for_agent


class MachineAgent(Agent):
    def __init__(self, jid: str, password: str, type: str, group: str, *args, **kwargs):
        super().__init__(jid, password, *args, **kwargs)
        self.type = type
        self.group = group
        self.current_order: Optional[str] = None
        self.current_order_id: Optional[str] = None
        self.previous_orders: dict[str, str] = {}
        self.previous_agent: str = ""
        self.manager: str = ""
        self.description: AgentDescription = AgentDescription()
        self.maintenance_probability = 0.1

    async def get_machine_info(self, request):
        previous_orders_list = [f"{key}: {value}" for key, value in self.previous_orders.items()]

        # Search for messages related to maintenance
        maintenance_messages = []
        maintenance_pattern = r"Maintenance\. The machine will be offline for (\d+)s"
        maintenance_over_pattern = r"Maintenance over\."

        if self.jid in Log:
            for log_message in Log[self.jid]:
                match_maintenance = re.search(maintenance_pattern, log_message.message)
                match_maintenance_over = re.search(maintenance_over_pattern, log_message.message)
                if match_maintenance:
                    offline_time = int(match_maintenance.group(1))
                    maintenance_messages.append((log_message.time, f"Maintenance: Machine offline for {offline_time}s"))
                elif match_maintenance_over:
                    maintenance_messages.append((log_message.time, "Maintenance over."))

        # Sort maintenance messages by timestamp
        maintenance_messages.sort(key=lambda x: x[0])

        return {
            "jid": self.jid,
            "type": self.type,
            "group": self.group,
            "current_order": self.current_order,
            "previous_orders": previous_orders_list,
            "previous_agent": self.previous_agent,
            "manager": self.manager,
            "working_times": calculate_state_percentages_for_agent(self.jid),
            "maintenance_messages": [f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}" for time, message in maintenance_messages]
        }

    async def setup(self) -> None:
        self.presence.approve_all = True
        behaviour = MachineBehaviour()
        self.add_behaviour(behaviour)

    def set_busy(self, busy: bool) -> None:
        log(self, f"Setting busy to {busy}.")
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
        self.add_transition("Maintenance", "Idle")

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
            self.agent.current_order = None
            await self.send_order(machine.name, order)
        else:
            self.agent.previous_orders[order] = self.agent.manager
            self.agent.current_order = None
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
                    if msg.metadata["ontology"] == "order_request":
                        order = get_order_info(msg.body)
                        order_id = msg.get_metadata("order_id")
                        log(self.agent, f"Order received: {order}, order_id: {order_id}")
                        self.agent.current_order = order
                        self.agent.current_order_id = order_id
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
            order_id = self.agent.current_order_id
            order = await self.do_work(order, order_id)
            if not is_done(order):
                await self.handle_order(order)
            log(self.agent, "Transition to Idle state.")
            self.set_next_state("Idle")

        async def do_work(self, order, order_id) -> str:
            next_index = get_next_item_index(order)
            log(self.agent, f"Starting work on order {order}, order_id {order_id}.")
            new_order = mark_done(next_index, order)
            await asyncio.sleep(1)
            log(self.agent, f"Work done on order {new_order}, order_id {order_id}.")
            if is_done(order):
                log(self.agent, f"Order completed: {order}, order_id: {order_id}")
                Orders[int(order_id)].end = datetime.now()
            await self.send_order(self.agent.previous_agent, order, "order_part_completed")
            self.agent.previous_agent = ""
            return new_order

        async def handle_order(self, order: str) -> None:
            machine = self.get_next_machine()
            if machine:
                self.agent.previous_orders[order] = machine.name
                self.agent.current_order = None
                await self.send_order(machine.name, order)
            else:
                self.agent.previous_orders[order] = self.agent.manager
                self.agent.current_order = None
                await self.handle_order_machine_missing(order)

        def get_next_machine(self) -> Optional[AgentDescription]:
            machines = self.get_machines()
            if machines:
                return machines[0]
            return None

        async def handle_order_machine_missing(self, order: str) -> None:
            await self.send_order(self.agent.manager, order)

        async def send_order(self, jid: str, order: str, ontology: str = "order_request") -> None:
            msg = Message(to=str(jid))
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