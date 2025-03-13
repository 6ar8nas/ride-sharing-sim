from typing import Optional

from constants import Events
from coordinates import ScreenBoundedCoordinates
from state import DateTime, SimulationState


class Entity:
    _uid = 0

    def __init__(
        self,
        start_node: int,
        end_node: int,
        state: SimulationState,
    ):
        self.id = Entity._uid
        Entity._uid += 1
        self.state = state
        self.start_node, self.end_node = start_node, end_node
        self.position = self.state.graph.get_node_data(start_node)
        self.departure_time = self.state.get_time()
        self.completed_time: Optional[DateTime] = None
        self.direct_cost = self.state.shortest_length(start_node, end_node)
        self.current_cost = self.direct_cost

    def complete(self, time: DateTime):
        self.completed_time = time

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other) -> bool:
        return isinstance(other, Entity) and self.id == other.id


class Rider(Entity):
    CANCEL_DELAY = DateTime.from_hms(0, 15, 0)

    def __init__(
        self,
        start_node: int,
        end_node: int,
        state: SimulationState,
        passenger_count: int = 1,
    ):
        super().__init__(start_node, end_node, state)
        self.passenger_count = passenger_count
        self.driver_id: Optional[int] = None
        self.matched_time: Optional[DateTime] = None
        self.boarded_time: Optional[DateTime] = None
        self.cancelled_time: Optional[DateTime] = None
        self.cancel_time = self.departure_time + Rider.CANCEL_DELAY
        self.state.post_event(Events.NewRider, rider=self)

    def match_driver(self, driver_id: int, cost: float, time: DateTime):
        self.driver_id = driver_id
        self.matched_time = time
        self.current_cost = cost

    def board(self, time: DateTime):
        self.boarded_time = time

    def cancel(self, time: DateTime):
        self.cancelled_time = time
        self.state.post_event(Events.RiderCancelled, rider=self)


class Driver(Entity):
    SPEED_KMH = 50

    def __init__(
        self,
        start_node: int,
        end_node: int,
        state: SimulationState,
        passenger_seats: int = 4,
    ):
        super().__init__(start_node, end_node, state)
        self.current_node = start_node
        self.passenger_seats = passenger_seats
        self.vacancies = passenger_seats
        self.riders: set[Rider] = set()
        self.completed_riders: set[Rider] = set()
        self.route = self.__compute_route([start_node, end_node])
        self.route.pop(0)
        self.next_node, self.next_pos = self.route[0]
        self.total_distance = 0.0
        self.speed = (
            Driver.SPEED_KMH
            / 3.6
            * (60 / state.frame_rate)
            * self.state.simulation_speed
        )
        self.state.post_event(Events.NewDriver, driver=self)

    def move(self, time: DateTime):
        if self.next_pos is None:
            return

        self.position, distance, reached_dest = self.position.move(
            self.next_pos, self.speed
        )
        self.total_distance += distance

        if reached_dest:
            self.current_node = self.next_node
            self.route.pop(0)
            self.next_node, self.next_pos = (
                self.route[0] if self.route else (None, None)
            )
            self.__on_node(time)

    def __on_node(self, time: DateTime):
        for rider in self.riders.copy():
            if rider.boarded_time is None and rider.start_node == self.current_node:
                self.pick_up(rider, time)
            elif rider.boarded_time is not None and rider.end_node == self.current_node:
                self.drop_off(rider, time)

        if len(self.route) == 0 and self.current_node == self.end_node:
            self.complete(time)

    def match_rider(
        self,
        rider: Rider,
        node_route: list[int],
        costs: tuple[float, float],
        time: DateTime,
    ):
        if self.vacancies < rider.passenger_count:
            return

        self.current_cost, rider_cost = costs
        self.vacancies -= rider.passenger_count
        rider.match_driver(self.id, rider_cost, time)
        self.riders.add(rider)
        self.route = self.__compute_route(node_route)
        self.state.post_event(Events.RiderMatch, driver=self, rider=rider)

    def pick_up(self, rider: Rider, time: DateTime):
        rider.board(time)
        self.state.post_event(Events.RiderPickup, driver=self, rider=rider)

    def drop_off(self, rider: Rider, time: DateTime):
        rider.complete(time)
        self.vacancies += rider.passenger_count
        self.riders.discard(rider)
        self.completed_riders.add(rider)
        self.state.post_event(Events.RiderDropOff, driver=self, rider=rider)

    def complete(self, time: DateTime):
        super().complete(time)
        self.state.post_event(Events.DriverComplete, driver=self)

    def __compute_route(
        self, node_route: list[int]
    ) -> list[tuple[int, ScreenBoundedCoordinates]]:
        full_route = [(node_route[0], self.state.graph.get_node_data(node_route[0]))]
        for i in range(len(node_route) - 1):
            inter_node = node_route[i]
            dest_node = node_route[i + 1]
            if inter_node == dest_node:
                continue

            path_seg = self.state.shortest_path(inter_node, dest_node)[1:]
            full_route.extend(
                (idx, self.state.graph.get_node_data(idx)) for idx in path_seg
            )

        return full_route

    def cost_fn(self, route_cost: float, new_rider: Rider) -> tuple[float, float]:
        cost = (
            self.total_distance
            + route_cost
            - sum(rider.current_cost for rider in (self.riders | self.completed_riders))
        )
        cost_curr = self.current_cost + new_rider.current_cost
        offset = (cost - cost_curr) / 2
        return self.current_cost + offset, new_rider.current_cost + offset
