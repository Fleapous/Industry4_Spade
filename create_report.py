import re
from datetime import datetime
import matplotlib.pyplot as plt

from Classes.Util import LogMessage, Log, Orders


def extract_and_calculate_state_durations():
    machine_agents = {}
    state_transition_pattern = r"Transition to (.+) state\."

    for jid, log_messages in Log.items():

        # Check if agent JID has a second digit after /
        if re.match(r".+/[0-9]{2}$", str(jid)):
            current_state = None
            current_state_start_time = None
            for log_message in log_messages:
                match = re.search(state_transition_pattern, log_message.message)
                if match:
                    state = match.group(1)
                    time = log_message.time
                    if state != current_state:
                        if current_state:
                            # Calculate duration for previous state
                            duration = (time - current_state_start_time).total_seconds()
                            machine_agents.setdefault(current_state, []).append(duration)
                        # Update current state
                        current_state = state
                        current_state_start_time = time

            # Calculate duration for last state transition in the loop
            if current_state and current_state_start_time:
                duration = (log_messages[-1].time - current_state_start_time).total_seconds()
                machine_agents.setdefault(current_state, []).append(duration)

    return machine_agents


def plot_average_state_durations():
    state_durations = extract_and_calculate_state_durations()
    average_durations = {state: sum(durations) / len(durations) for state, durations in state_durations.items()}

    labels = list(average_durations.keys())
    durations = list(average_durations.values())

    # Define colors for the pie chart slices
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22',
              '#17becf']

    # Plotting the pie chart with custom colors
    plt.figure(figsize=(8, 8))
    plt.pie(durations, labels=labels, autopct='%1.1f%%', startangle=140, colors=colors)
    plt.title('Average Time Spent in Each State')
    plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    plt.show()


def extract_and_calculate_state_durations_for_agent(target_jid: str):
    state_durations = {}
    state_transition_pattern = r"Transition to (.+) state\."

    if target_jid not in Log:
        print(f"No logs found for {target_jid}")
        return state_durations

    log_messages = Log[target_jid]
    current_state = None
    current_state_start_time = None
    for log_message in log_messages:
        match = re.search(state_transition_pattern, log_message.message)
        if match:
            state = match.group(1)
            # Correct the datetime format string to include microseconds
            time = datetime.strptime(str(log_message.time), '%Y-%m-%d %H:%M:%S.%f')
            if state != current_state:
                if current_state:
                    # Calculate duration for previous state
                    duration = (time - current_state_start_time).total_seconds()
                    state_durations.setdefault(current_state, []).append(duration)
                # Update current state
                current_state = state
                current_state_start_time = time

    # Calculate duration for the last state transition in the loop
    if current_state and current_state_start_time:
        duration = (datetime.strptime(str(log_messages[-1].time),
                                      '%Y-%m-%d %H:%M:%S.%f') - current_state_start_time).total_seconds()
        state_durations.setdefault(current_state, []).append(duration)

    return state_durations


def calculate_state_percentages_for_agent(target_jid: str):
    print(target_jid)
    state_durations = extract_and_calculate_state_durations_for_agent(target_jid)
    if not state_durations:
        print(f"No state durations to calculate for {target_jid}")
        return []

    total_duration = sum(sum(durations) for durations in state_durations.values())
    state_percentages = {state: (sum(durations) / total_duration) * 100 for state, durations in state_durations.items()}

    state_percentage_strings = [f"{state}: {percentage:.2f}%" for state, percentage in state_percentages.items()]
    return state_percentage_strings


# def main():
#     plot_order_times()


if __name__ == "__main__":
    plot_average_state_durations()
    # main()


def extract_order_times():
    order_times = []
    # print(Orders)
    for order in Orders:
        print(f"{order.start} _ {order.end} _ {order.id}")
        if order.end:
            start_time = order.start
            end_time = order.end
            order_times.append((start_time, end_time))
    return order_times


# Function to plot order times
def plot_order_times():
    order_times = extract_order_times()

    # Convert datetime objects and calculate durations
    start_times = [start for start, end in order_times]
    durations = [(end - start).total_seconds() for start, end in order_times if
                 end]  # Calculate only if end time is defined

    if not durations:
        print("No valid orders found to plot.")
        return

    # Plotting the order durations as a bar plot
    plt.figure(figsize=(10, 5))
    plt.bar(start_times, durations, width=0.0003, align='center')
    plt.xlabel('Order Start Time')
    plt.ylabel('Order Duration (seconds)')
    plt.title('Order Durations Over Time')
    plt.grid(True)
    plt.show()
