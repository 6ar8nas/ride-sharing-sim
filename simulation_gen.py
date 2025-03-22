import random
import threading
import time

from constants import Events
from entity import Driver, Rider
from utils import DateTime
from state import SimulationState


class SimulationGenerator:
    rider_frequency = (2, 4)
    driver_frequency = (2, 4)
    rush_hour_frequency_rate = 2
    night_frequency_rate = 0.3
    rush_hour_commute_bias = 0.7
    traffic_update_frequency = 15

    def __init__(self, state: SimulationState):
        self.state = state
        self.node_ids = list(state.graph.node_indices())
        self.residential_node_ids = list(
            state.graph.filter_nodes(lambda e: e.is_residential)
        )
        self.central_node_ids = list(state.graph.filter_nodes(lambda e: e.is_center))
        self.generate_events = False

    def start(self):
        if self.generate_events:
            return

        self.generate_events = True

        def generate_driver():
            while self.generate_events:
                sleep_timer = self.__get_sleep_timer(
                    self.state.get_time(), SimulationGenerator.driver_frequency
                )
                time.sleep(sleep_timer)
                driver = self.__new_driver(self.state.get_time())
                self.state.post_event(Events.NewDriver, driver=driver)

        def generate_rider():
            while self.generate_events:
                sleep_timer = self.__get_sleep_timer(
                    self.state.get_time(), SimulationGenerator.rider_frequency
                )
                time.sleep(sleep_timer)
                rider = self.__new_rider(self.state.get_time())
                self.state.post_event(Events.NewRider, rider=rider)

        def reevaluate_traffic():
            sleep_timer = self.traffic_update_frequency / self.state.simulation_speed
            while self.generate_events:
                time.sleep(sleep_timer)
                self.state.post_event(Events.TrafficUpdate)

        self.thread_driver = threading.Thread(target=generate_driver, daemon=True)
        self.thread_driver.start()
        self.thread_rider = threading.Thread(target=generate_rider, daemon=True)
        self.thread_rider.start()
        self.thread_traffic = threading.Thread(target=reevaluate_traffic, daemon=True)
        self.thread_traffic.start()

    def stop(self):
        if not self.generate_events:
            return

        self.generate_events = False
        self.thread_rider.join()
        self.thread_driver.join()
        self.thread_traffic.join()

    def __new_driver(self, current_time: DateTime) -> Driver:
        start_node, end_node = self.__generate_nodes(current_time)
        [passenger_count] = random.choices([1, 2, 3, 4], [0.15, 0.2, 0.05, 0.6])
        return Driver(start_node, end_node, self.state, passenger_count)

    def __new_rider(self, current_time: DateTime) -> Rider:
        start_node, end_node = self.__generate_nodes(current_time)
        [riders_count] = random.choices([1, 2, 3], [0.8, 0.15, 0.05])
        return Rider(start_node, end_node, self.state, riders_count)

    def __generate_nodes(self, current_time: DateTime) -> tuple[int, int]:
        start_node, end_node = 0, 0
        is_rush_hour = current_time.is_within_rush_time()
        while start_node == end_node:
            if (
                is_rush_hour == False
                or random.random() >= SimulationGenerator.rush_hour_commute_bias
            ):
                start_node, end_node = random.choices(self.node_ids, k=2)
                continue

            if is_rush_hour == "Morning":
                start_node = random.choice(self.residential_node_ids)
                end_node = random.choice(self.central_node_ids)
            elif is_rush_hour == "Evening":
                start_node = random.choice(self.central_node_ids)
                end_node = random.choice(self.residential_node_ids)

        return start_node, end_node

    def __get_sleep_timer(
        self, current_time: DateTime, standard_frequency: tuple[float, float]
    ) -> float:
        day_time = current_time.day_time
        sleep_timer = random.uniform(*standard_frequency)
        if day_time.is_within_rush_time() != False:
            sleep_timer /= SimulationGenerator.rush_hour_frequency_rate
        if day_time.is_night_time():
            sleep_timer /= SimulationGenerator.night_frequency_rate
        return sleep_timer / self.state.simulation_speed
