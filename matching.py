from typing import Optional

from entity import Driver, Rider
from routing import held_karp_pc
from utils import DateTime
from state import SimulationState


def static_rider_matching(
    riders: set[Rider],
    drivers: set[Driver],
    state: SimulationState,
    current_time: DateTime,
) -> tuple[int, float]:
    matches = 0
    expected_savings = 0.0
    for rider in riders:
        if rider.driver_id is not None:
            continue

        best_heuristic = 0
        best_driver: Optional[Driver] = None
        best_costs: Optional[tuple[float, float]] = None
        best_route: Optional[list[int]] = None
        for driver in drivers:
            if driver.vacancies == 0 or driver.current_edge is None:
                continue

            route, route_cost = held_karp_pc(
                driver.current_edge.edge.ending_node_index,
                driver.end_node,
                [
                    (
                        (rid.start_node, rid.end_node)
                        if rid.boarded_time is None
                        else (rid.end_node, driver.end_node)
                    )
                    for rid in (driver.riders)
                ]
                + [(rider.start_node, rider.end_node)],
                state,
            )

            heuristic = rider.distance_paid_for + driver.distance_paid_for - route_cost
            if heuristic < best_heuristic:
                continue

            best_driver, best_route = driver, route
            best_heuristic = heuristic
            best_costs = driver.cost_fn_new_rider(route_cost, rider)

        if best_driver is None:
            continue

        best_driver.match_rider(rider, best_route, best_costs, current_time)
        matches += 1
        expected_savings += best_heuristic

    return matches, expected_savings
