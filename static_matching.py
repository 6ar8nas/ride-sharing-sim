from typing import Optional

from entity import Driver, Rider
from osm_graph import OSMGraph
from routing import held_karp_pc
from utils import DateTime


def static_rider_matching(
    riders: list[Rider], drivers: list[Driver], state: OSMGraph, time: DateTime
) -> tuple[int, float]:
    expected_savings = 0.0
    matches = 0
    for rider in riders:
        if rider.driver_id is not None or rider.cancelled_time is not None:
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

        driver_costs, rider_costs = best_costs
        best_driver.match_rider(driver_costs, (rider, rider_costs), best_route, time)
        matches += 1
        expected_savings += best_heuristic

    return len(matches), expected_savings
