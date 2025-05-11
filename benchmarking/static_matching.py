import numpy as np

from entity import Driver, cost_fn_new_rider, driver_type, rider_type
from routing import held_karp_pc
from numba import types, int64, njit
from numba.typed import List

driver_score_type = types.Tuple((driver_type, types.float64))
rider_score_type = types.Tuple((rider_type, types.float64))
rider_score_list_type = types.ListType(rider_score_type)
match_type = types.Tuple(
    (driver_score_type, rider_score_list_type, types.ListType(types.int64))
)


@njit
def static_rider_matching(
    riders: List,
    drivers: List,
    shortest_lengths: np.ndarray,
) -> tuple[List, int, float]:
    matches = List.empty_list(match_type)
    expected_savings = 0.0
    for rider in riders:
        best_heuristic = 0
        empty_rider_list = List.empty_list(rider_type)
        best_driver = Driver(-1, 0, 0, 0, empty_rider_list, 0)
        best_costs = (1e18, 1e18)
        best_route = List.empty_list(int64)
        for driver in drivers:
            if driver.vacancies == 0:
                continue

            pairs = np.array(
                [((rid.start_node, rid.end_node)) for rid in (driver.riders)]
                + [(rider.start_node, rider.end_node)]
            )
            route, route_cost = held_karp_pc(
                driver.start_node,
                driver.end_node,
                pairs,
                shortest_lengths,
            )

            heuristic = rider.distance_paid_for + driver.distance_paid_for - route_cost
            if heuristic < best_heuristic:
                continue

            best_driver, best_route = driver, route
            best_heuristic = heuristic
            best_costs = cost_fn_new_rider(driver, rider, route_cost)

        if best_driver.id == -1:
            continue

        driver_costs, rider_costs = best_costs
        typed_rider_costs = List.empty_list(rider_score_type)
        typed_rider_costs.append((rider, rider_costs))
        matches.append(((best_driver, driver_costs), typed_rider_costs, best_route))
        best_driver.riders.append(rider)
        expected_savings += best_heuristic

    return matches, len(matches), expected_savings
