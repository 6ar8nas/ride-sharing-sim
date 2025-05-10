from typing import Any, Callable, Optional
from constants import Events
from osm_graph import CityEdge, OSMGraph
from routing import held_karp_pc
from utils import DateTime


class Entity:
    _uid = 0

    def __init__(
        self,
        start_node: int,
        end_node: int,
        time: DateTime,
        state: OSMGraph,
        event_fn: Optional[Callable[[Events, dict[str, Any]], None]] = None,
    ):
        self.id = Entity._uid
        self.start_node, self.end_node = start_node, end_node
        Entity._uid += 1
        self.state = state
        self.departure_time = time
        self.completed_time: Optional[DateTime] = None
        self.shortest_distance = self.state.shortest_distance(start_node, end_node)
        self.distance_paid_for = self.state.shortest_path_distance(start_node, end_node)
        self.single_trip_distance = self.distance_paid_for
        self._event_fn = event_fn

    def _post_event(self, event_type: Events, dict: dict[str, Any] = {}):
        if self._event_fn:
            self._event_fn(event_type, dict)

    def complete(self, time: DateTime):
        self.completed_time = time

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other) -> bool:
        return isinstance(other, Entity) and self.id == other.id


class Rider(Entity):
    cancel_delay = DateTime.from_hms(0, 15, 0)

    def __init__(
        self,
        start_node: int,
        end_node: int,
        time: DateTime,
        state: OSMGraph,
        event_fn: Optional[Callable[[Events, dict[str, Any]], None]] = None,
    ):
        super().__init__(start_node, end_node, time, state, event_fn)
        self.position = self.state.graph.get_node_data(start_node)
        self.driver_id: Optional[int] = None
        self.matched_time: Optional[DateTime] = None
        self.boarded_time: Optional[DateTime] = None
        self.cancelled_time: Optional[DateTime] = None
        self.cancel_time = self.departure_time + Rider.cancel_delay

    def match_driver(self, driver_id: int, cost: float, time: DateTime):
        self.driver_id = driver_id
        self.matched_time = time
        self.distance_paid_for = cost

    def board(self, time: DateTime):
        self.boarded_time = time

    def cancel(self, time: DateTime):
        self.cancelled_time = time
        self._post_event(Events.RiderCancel, {"rider": self})

    def copy(self) -> "Rider":
        return Rider(
            self.start_node,
            self.end_node,
            self.departure_time,
            self.state,
            self._event_fn,
        )


class Driver(Entity):
    speed_kmh = 50

    def __init__(
        self,
        start_node: int,
        end_node: int,
        time: DateTime,
        state: OSMGraph,
        passenger_seats: int = 4,
        event_fn: Optional[Callable[[Events, dict[str, Any]], None]] = None,
    ):
        super().__init__(start_node, end_node, time, state, event_fn)
        self.passenger_seats, self.vacancies = passenger_seats, passenger_seats
        self.riders, self.completed_riders = set[Rider](), set[Rider]()
        self.route = self.__compute_route([start_node, end_node])
        self.current_edge = ActiveEdge(self.route.pop(0))
        self.total_distance = 0.0

    def move(self, speed_ratio: float, time: DateTime):
        if self.current_edge is None:
            return

        distance, reached_dest = self.current_edge.move(speed_ratio)
        self.total_distance += distance

        if reached_dest:
            self.__on_node(self.current_edge.edge.ending_node_index, time)
            self.current_edge = (
                ActiveEdge(self.route.pop(0)) if len(self.route) > 0 else None
            )

    def __on_node(self, node_idx: int, time: DateTime):
        for rider in self.riders.copy():
            if rider.boarded_time is None and rider.start_node == node_idx:
                self.pick_up(rider, time)
            elif rider.boarded_time is not None and rider.end_node == node_idx:
                self.drop_off(rider, time)

        if len(self.route) == 0 and self.end_node == node_idx:
            self.complete(time)

    def match_riders(
        self,
        cost: float,
        riders: list[tuple[Rider, float]],
        node_route: list[int],
        time: DateTime,
    ):
        self.distance_paid_for = cost
        self.route = self.__compute_route(node_route)
        for rider, rider_cost in riders:
            self.vacancies -= 1
            rider.match_driver(self.id, rider_cost, time)
            self.riders.add(rider)
            self._post_event(Events.RiderMatch, {"driver": self, "rider": rider})

    def pick_up(self, rider: Rider, time: DateTime):
        rider.board(time)
        self._post_event(Events.RiderPickup, {"driver": self, "rider": rider})

    def drop_off(self, rider: Rider, time: DateTime):
        rider.complete(time)
        self.vacancies += 1
        self.riders.discard(rider)
        self.completed_riders.add(rider)
        self._post_event(Events.RiderDropOff, {"driver": self, "rider": rider})

    def complete(self, time: DateTime):
        super().complete(time)
        self._post_event(Events.DriverComplete, {"driver": self})

    def __compute_route(self, node_route: list[int]) -> list[CityEdge]:
        full_route = [node_route[0]]
        for i in range(len(node_route) - 1):
            inter_node = node_route[i]
            dest_node = node_route[i + 1]
            if inter_node == dest_node:
                continue

            full_route.extend(self.state.shortest_path(inter_node, dest_node)[1:])

        return [
            self.state.graph.get_edge_data(full_route[i], full_route[i + 1])
            for i in range(len(full_route) - 1)
        ]

    def recalculate_route(self):
        if self.current_edge is None:
            return

        route, route_cost = held_karp_pc(
            self.current_edge.edge.ending_node_index,
            self.end_node,
            [
                (
                    (rid.start_node, rid.end_node)
                    if rid.boarded_time is None
                    else (rid.end_node, self.end_node)
                )
                for rid in (self.riders)
            ],
            self.state,
        )
        self.distance_paid_for = self.cost_fn(route_cost)
        self.route = self.__compute_route(route)
        return

    def cost_fn(self, route_cost: float) -> float:
        return (
            self.total_distance
            + self.current_edge.remaining_distance
            + route_cost
            - sum(
                rider.distance_paid_for
                for rider in (self.riders | self.completed_riders)
            )
        )

    def cost_fn_new_rider(
        self, route_cost: float, new_rider: Rider
    ) -> tuple[float, float]:
        cost = self.cost_fn(route_cost)
        cost_curr = self.distance_paid_for + new_rider.distance_paid_for
        offset = (cost - cost_curr) / 2
        return self.distance_paid_for + offset, new_rider.distance_paid_for + offset

    def copy(self) -> "Driver":
        return Driver(
            self.start_node,
            self.end_node,
            self.departure_time,
            self.state,
            self.passenger_seats,
            self._event_fn,
        )


class ActiveEdge:
    def __init__(self, edge: CityEdge):
        self.edge = edge
        self.current_position = edge.starting_node_coords
        self.remaining_distance = self.edge.distance

    def move(self, speed_ratio: float) -> tuple[float, bool]:
        self.current_position, distance, is_reached_goal = self.current_position.move(
            self.edge.ending_node_coords, self.edge.speed * speed_ratio
        )
        self.remaining_distance -= distance
        return distance, is_reached_goal

    @property
    def on_screen(self) -> tuple[int, int]:
        return self.current_position.on_screen
