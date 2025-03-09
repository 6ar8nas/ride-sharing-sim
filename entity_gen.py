import random
import threading
import time

from entity import Driver, Rider
from state import SimulationState


class EntityGenerator:
    rider_frequency = (1, 2)
    driver_frequency = (1, 2)

    def __init__(self, state: SimulationState):
        self.state = state
        self.node_ids = list(state.graph.node_indices())
        self.generate_events = False

    def start(self):
        if self.generate_events:
            return

        self.generate_events = True

        def generate_driver():
            while self.generate_events:
                time.sleep(random.uniform(*EntityGenerator.driver_frequency))
                self.__new_driver()

        def generate_rider():
            while self.generate_events:
                time.sleep(random.uniform(*EntityGenerator.rider_frequency))
                self.__new_rider()

        self.thread_driver = threading.Thread(target=generate_driver, daemon=True)
        self.thread_driver.start()
        self.thread_rider = threading.Thread(target=generate_rider, daemon=True)
        self.thread_rider.start()

    def stop(self):
        if not self.generate_events:
            return

        self.generate_events = False
        self.thread_rider.join()
        self.thread_driver.join()

    def __new_driver(self) -> Driver:
        start_node, end_node = 0, 0
        while start_node == end_node:
            start_node, end_node = random.choices(self.node_ids, k=2)
        [passenger_count] = random.choices([1, 2, 3, 4], [0.15, 0.2, 0.05, 0.6])
        return Driver(start_node, end_node, self.state, passenger_count)

    def __new_rider(self) -> Rider:
        start_node, end_node = 0, 0
        while start_node == end_node:
            start_node, end_node = random.choices(self.node_ids, k=2)
        [riders_count] = random.choices([1, 2, 3], [0.8, 0.15, 0.05])
        return Rider(start_node, end_node, self.state, riders_count)
