from typing import Optional

from entity import Driver, Rider
from routing import held_karp_pc
from utils import DateTime
from state import SimulationState


def static_rider_matching(
    rider: Rider, drivers: set[Driver], state: SimulationState, current_time: DateTime
):
    if rider.driver_id is not None:
        return

    best_heuristic = rider.current_cost
    best_driver: Optional[Driver] = None
    best_costs: Optional[tuple[float, float]] = None
    best_route: Optional[list[int]] = None
    for driver in drivers:
        if driver.vacancies < rider.passenger_count:
            continue

        route, route_cost = held_karp_pc(
            driver.next_node if driver.next_node else driver.current_node,
            driver.end_node,
            [(rid.start_node, rid.end_node) for rid in (driver.riders)]
            + [(rider.start_node, rider.end_node)],
            state,
        )
        driver_cost, rider_cost = driver.cost_fn(route_cost, rider)
        if rider_cost + driver_cost - driver.current_cost > best_heuristic:
            continue

        best_driver, best_route = driver, route
        best_heuristic = rider_cost + driver_cost - driver.current_cost
        best_costs = (driver_cost, rider_cost)

    if best_driver is None:
        return

    best_driver.match_rider(rider, best_route, best_costs, current_time)
