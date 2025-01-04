import itertools
from typing import Tuple

from state import SimulationState

def brute_force_routing(start_node: int, end_node: int, constrained_node_pairs: list[Tuple[int, int]], state: SimulationState) -> Tuple[list[int], float]:
    def is_valid_route(route: list[Tuple[int, int, int]]) -> bool:
        const_sat = set()
        for _, action, id in route:
            if action == 0:
                const_sat.add(id)
            elif action == 1 and id not in const_sat:
                return False
        return True

    def route_cost(route: list[Tuple[int, int, int]]) -> float:
        cost = 0
        current_node = start_node
        for stop in route:
            next_node = stop[0]
            cost += state.shortest_length(current_node, next_node) if current_node != next_node else 0
            current_node = next_node
        cost += state.shortest_length(current_node, end_node) if current_node != end_node else 0
        return cost

    all_possible_routes = itertools.permutations([(sn, 0, i) for i, (sn, _) in enumerate(constrained_node_pairs)] + \
                                                 [(en, 1, i) for i, (_, en) in enumerate(constrained_node_pairs)])
    valid_routes = filter(is_valid_route, all_possible_routes)
    costs = map(lambda route: (route, route_cost(route)), valid_routes)
    optimal_route, min_cost = min(costs, key=lambda x: x[1])
    result = [start_node] + list(map(lambda route: route[0], optimal_route)) + [end_node]
    return result, min_cost