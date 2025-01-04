from typing import Optional, Tuple

import pygame

from constants import Events
from state import SimulationState

class Entity:
    _uid = 0

    def __init__(self, start_node: int, end_node: int, departure_time: int, state: SimulationState):
        self.id = Entity._uid
        Entity._uid += 1
        self.state = state
        self.start_node = start_node
        self.end_node = end_node
        self.position = self.state.nodes[start_node]
        self.departure_time = departure_time
        self.completed_time: Optional[int] = None
        self.direct_cost = self.state.shortest_length(start_node, end_node)
        self.current_cost = self.direct_cost

    def complete(self, time: int):
        self.completed_time = time

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other) -> bool:
        return isinstance(other, Entity) and self.id == other.id

class Rider(Entity):
    cancel_delay = 15000 # 15s

    def __init__(self, start_node: int, end_node: int, departure_time: int, state: SimulationState, passenger_count: int = 1):
        super().__init__(start_node, end_node, departure_time, state)
        self.passenger_count = passenger_count
        self.driver_id: Optional[int] = None
        self.matched_time: Optional[int] = None
        self.boarded_time: Optional[int] = None
        self.cancelled_time: Optional[int] = None
        self.cancel_time = departure_time + Rider.cancel_delay
        pygame.event.post(pygame.event.Event(pygame.USEREVENT, {"event_type": Events.NewRider, "rider": self}))

    def match_driver(self, driver_id: int, cost: float, time: int):
        self.driver_id = driver_id
        self.matched_time = time
        self.current_cost = cost

    def board(self, time: int):
        self.boarded_time = time

    def cancel(self, time: int):
        self.cancelled_time = time
        pygame.event.post(pygame.event.Event(pygame.USEREVENT, {"event_type": Events.RiderCancelled, "rider": self}))

class Driver(Entity):
    speed = 5

    def __init__(self, start_node: int, end_node: int, departure_time: int, state: SimulationState, passenger_seats: int = 4):
        super().__init__(start_node, end_node, departure_time, state)
        self.current_node = start_node
        self.passenger_seats = passenger_seats
        self.vacancies = passenger_seats
        self.riders: set[Rider] = set()
        self.__completed_riders: set[Rider] = set()
        self.route = self.__compute_route([start_node, end_node])
        self.route.pop(0)
        self.next_node, self.next_pos = self.route[0]
        self.total_distance = 0
        pygame.event.post(pygame.event.Event(pygame.USEREVENT, {"event_type": Events.NewDriver, "driver": self}))

    def move(self, time: int):
        if self.next_pos is None:
            return

        dx, dy = self.next_pos[0] - self.position[0], self.next_pos[1] - self.position[1]
        distance = (dx**2 + dy**2)**0.5

        if distance <= Driver.speed:
            self.total_distance += self.state.shortest_length(self.current_node, self.next_node)
            self.current_node, self.position = self.next_node, self.next_pos
            self.route.pop(0)
            self.next_node, self.next_pos = self.route[0] if self.route else (None, None)
            self.__on_node(time)
        else:
            step_x = Driver.speed * dx / distance
            step_y = Driver.speed * dy / distance
            self.position = (self.position[0] + step_x, self.position[1] + step_y)

    def __on_node(self, time: int):
        for rider in self.riders.copy():
            if rider.boarded_time is None and rider.start_node == self.current_node:
                self.pick_up(rider, time)
            elif rider.boarded_time is not None and rider.end_node == self.current_node:
                self.drop_off(rider, time)

        if len(self.route) == 0 and self.current_node == self.end_node:
            self.complete(time)

    def match_rider(self, rider: Rider, node_route: list[int], costs: Tuple[float, float], time: int):
        if self.vacancies < rider.passenger_count:
            return
        
        self.current_cost, rider_cost = costs
        self.vacancies -= rider.passenger_count
        rider.match_driver(self.id, rider_cost, time)
        self.riders.add(rider)
        self.route = self.__compute_route(node_route)
        pygame.event.post(pygame.event.Event(pygame.USEREVENT, {"event_type": Events.RiderMatch, "driver": self, "rider": rider}))

    def pick_up(self, rider: Rider, time: int):
        rider.board(time)
        pygame.event.post(pygame.event.Event(pygame.USEREVENT, {"event_type": Events.RiderPickup, "driver": self, "rider": rider}))

    def drop_off(self, rider: Rider, time: int):
        rider.complete(time)
        self.vacancies += rider.passenger_count
        self.riders.discard(rider)
        self.__completed_riders.add(rider)
        pygame.event.post(pygame.event.Event(pygame.USEREVENT, {"event_type": Events.RiderDropOff, "driver": self, "rider": rider}))

    def complete(self, time: int):
        super().complete(time)
        pygame.event.post(pygame.event.Event(pygame.USEREVENT, {"event_type": Events.DriverComplete, "driver": self}))

    def __compute_route(self, node_route: list[int]) -> list[Tuple[int, Tuple[float, float]]]:
        full_route = [(node_route[0], self.state.nodes[node_route[0]])]
        for i in range(len(node_route) - 1):
            inter_node = node_route[i]
            dest_node = node_route[i + 1]
            if inter_node == dest_node:
                continue

            path_seg = self.state.shortest_path(inter_node, dest_node)[1:]
            full_route.extend((idx, self.state.nodes[idx]) for idx in path_seg)

        return full_route

    def cost_fn(self, route_cost: float, new_rider: Rider) -> Tuple[float, float]:
        cost = self.total_distance + route_cost - sum(rider.current_cost for rider in (self.riders | self.__completed_riders))
        cost_curr = self.current_cost + new_rider.current_cost
        offset = (cost - cost_curr) / 2
        return self.current_cost + offset, new_rider.current_cost + offset