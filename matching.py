
from typing import Optional

from entity import Driver, Rider
from routing import held_karp_pc
from state import SimulationState

def rider_matching(rider: Rider, drivers: set[Driver], state: SimulationState, current_time: int):
    if rider.driver_id is not None:
        return
    best_driver: Optional[Driver] = None
    best_cost = float('inf') # rider.direct_cost
    best_route: Optional[list[int]] = None
    for driver in drivers:
        if driver.vacancies < rider.passenger_count:
            continue
        route, cost = held_karp_pc(driver.next_node if driver.next_node else driver.current_node, driver.end_node, [(rid.start_node, rid.end_node) for rid in (driver.riders)] + [(rider.start_node, rider.end_node)], state)
        if driver.cost_fn(cost, rider.passenger_count) > driver.direct_cost:
            continue

        # cost manipulation for rider rider.cost_fn
        if cost < best_cost:
            best_driver = driver
            best_cost = cost
            best_route = route

    if best_driver is None:
        return

    best_driver.match_rider(rider, best_route, current_time)
