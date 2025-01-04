import random
import threading
import time

import pygame

from entity import Driver, Rider
from state import SimulationState

class EntityGenerator:
    rider_frequency = 2
    driver_frequency = 4

    def __init__(self, state: SimulationState):
        self.state = state
        self.node_ids = list(state.nodes.keys())
        self.generate_events = False

    def start(self):
        if self.generate_events:
            return

        self.generate_events = True
        def generate_driver():
            while self.generate_events:
                time.sleep(EntityGenerator.driver_frequency)
                self.__new_driver()

        def generate_rider():
            while self.generate_events:
                time.sleep(EntityGenerator.rider_frequency)
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
        return Driver(start_node, end_node, pygame.time.get_ticks(), self.state)

    def __new_rider(self) -> Rider:
        start_node, end_node = 0, 0
        while start_node == end_node:
            start_node, end_node = random.choices(self.node_ids, k=2)
        return Rider(start_node, end_node, pygame.time.get_ticks(), self.state)