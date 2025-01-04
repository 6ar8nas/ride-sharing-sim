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

    def complete(self, time: int):
        self.completed_time = time

class Rider(Entity):
    def __init__(self, start_node: int, end_node: int, departure_time: int, state: SimulationState, passenger_count: int = 1):
        super().__init__(start_node, end_node, departure_time, state)
        self.passenger_count = passenger_count
        pygame.event.post(pygame.event.Event(pygame.USEREVENT, {"event_type": Events.NewRider, "rider": self}))

class Driver(Entity):
    speed = 5

    def __init__(self, start_node: int, end_node: int, departure_time: int, state: SimulationState, passenger_seats: int = 4):
        super().__init__(start_node, end_node, departure_time, state)
        self.current_node = start_node
        self.passenger_seats = passenger_seats
        self.next_node, self.next_pos = self.route[0]

    def move(self, time: int):
        if self.next_pos is None:
            return

        dx, dy = self.next_pos[0] - self.position[0], self.next_pos[1] - self.position[1]
        distance = (dx**2 + dy**2)**0.5

        if distance <= Driver.speed:
            self.route.pop(0)
            self.next_node, self.next_pos = self.route[0] if self.route else (None, None)
            self.__on_node(time)
        else:
            step_x = Driver.speed * dx / distance
            step_y = Driver.speed * dy / distance
            self.position = (self.position[0] + step_x, self.position[1] + step_y)

    def __on_node(self, time: int):
        if len(self.route) == 0 and self.current_node == self.end_node:
            self.complete(time)

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
