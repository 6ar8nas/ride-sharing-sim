import heapq
import itertools
from typing import Callable, Optional, Tuple, Literal

from state import SimulationState

def held_karp_pc(start_node: int, end_node: int, constrained_node_pairs: list[Tuple[int, int]], state: SimulationState) -> Tuple[list[int], float]:
    start_city, end_city = 0, 1
    city_node_dict = {start_city: start_node, end_city: end_node} | \
                     {i + 2: node for i, node in enumerate(itertools.chain.from_iterable(constrained_node_pairs))}

    n = len(city_node_dict)
    float_inf_arr, none_arr, range_2n = [float('inf')], [None], range(2, n)
    dp: list[list[Optional[float]]] = [float_inf_arr * n if i % 2 else None for i in range(1 << n)]
    parent: list[list[Optional[int]]] = [none_arr * n if i % 2 else None for i in range(1 << n)]

    dp[1][start_city] = 0

    for subset in range(1, 1 << n, 2): # There's no need to iterate through subsets not containing the starting city
        for prev_city in range_2n if subset != 1 else [start_city]: # We only consider the starting city to be previous if it's the the only city visited
            if not (subset & (1 << prev_city)): # Previous city must have been already visited
                continue

            for next_city in range_2n if subset != (1 << n) - 3 else [end_city]: # We only evaluate the end city if it's the last city to visit
                if (subset & (1 << next_city)) or \
                    (next_city % 2 == 1 and not (subset & (1 << (next_city - 1)))): # The next city must be unvisited, and if constrained, the predecessor must have been visited
                    continue

                new_subset = subset | (1 << next_city)
                new_cost = dp[subset][prev_city] + state.shortest_length(city_node_dict[prev_city], city_node_dict[next_city])
                if new_cost < dp[new_subset][next_city]:
                    dp[new_subset][next_city] = new_cost
                    parent[new_subset][next_city] = prev_city

    route: list[int] = []
    subset, prev = (1 << n) - 1, end_city
    cost = dp[subset][prev]
    while prev is not None:
        new_prev = parent[subset][prev]
        subset ^= (1 << prev)
        if new_prev is not prev:
            route.append(prev)
            prev = new_prev

    return [city_node_dict[idx] for idx in reversed(route)], cost

def dijkstra_routing(start_node: int, end_node: int, constrained_node_pairs: list[Tuple[int, int]], state: SimulationState) -> Tuple[list[int], float]:
    routes: list[Tuple[float, list[int], bool, frozenset[Tuple[int, Optional[int]]]]] = [(0, [start_node], True, frozenset(constrained_node_pairs))]

    min_cost = float('inf')
    while routes:
        cost, node_route, end_node_remaining, available_actions = heapq.heappop(routes)

        if not available_actions:
            if not end_node_remaining:
                return node_route, cost
            heapq.heappush(routes, (cost, node_route, False, frozenset({(end_node, None)})))
            min_cost = cost + state.shortest_length(node_route[-1], end_node)
            continue

        for node, extra_node in available_actions:
            new_cost = cost + state.shortest_length(node_route[-1], node)
            if new_cost > min_cost:
                continue
            new_route = node_route + [node]
            new_actions = available_actions - {(node, extra_node)}
            if extra_node is not None:
                new_actions = new_actions | {(extra_node, None)}
            heapq.heappush(routes, (new_cost, new_route, end_node_remaining, new_actions))

    return [], float('inf')

def single_link_heuristic(current_node: int, available_actions: frozenset[Tuple[int, Optional[int]]], end_node: int, state: SimulationState) -> float:
    lb = state.shortest_length(current_node, end_node)
    remaining_nodes = {node for node in itertools.chain.from_iterable(available_actions)}
    remaining_nodes.add(end_node)
    remaining_nodes.discard(None)

    if len(remaining_nodes) == 1:
        return lb

    lb += sum(min(state.shortest_length(node, other) for other in remaining_nodes if node != other)
                for node in remaining_nodes)
    return lb

def nearest_neighbor_heuristic(current_node: int, available_actions: frozenset[Tuple[int, Optional[int]]], end_node: int, state: SimulationState) -> float:
    lb = state.shortest_length(current_node, end_node)
    remaining_nodes = {node for node in itertools.chain.from_iterable(available_actions)}
    remaining_nodes.add(end_node)
    remaining_nodes.discard(None)

    while remaining_nodes:
        nearest = min(remaining_nodes, key=lambda node: state.shortest_length(current_node, node))
        lb += state.shortest_length(current_node, nearest)
        remaining_nodes.remove(nearest)
        current_node = nearest

    return lb

heuristic_functions: dict[Literal["single-link", "nearest-neighbor"], Callable[[int, frozenset[Tuple[int, Optional[int]]], int, SimulationState], float]] = {
    'single-link': single_link_heuristic,
    'nearest-neighbor': nearest_neighbor_heuristic
}

def branch_bound_routing(start_node: int, end_node: int, constrained_node_pairs: list[Tuple[int, int]], state: SimulationState, heuristic: Literal["single-link", "nearest-neighbor"] = "single-link") -> Tuple[list[int], float]:
    routes: list[Tuple[float, list[int], bool, frozenset[Tuple[int, Optional[int]]]]] = [(0, [start_node], True, frozenset(constrained_node_pairs))]

    min_cost = float('inf')
    while routes:
        cost, node_route, end_node_remaining, available_actions = heapq.heappop(routes)

        if not available_actions:
            if not end_node_remaining:
                return node_route, cost
            heapq.heappush(routes, (cost, node_route, False, frozenset({(end_node, None)})))
            min_cost = cost + state.shortest_length(node_route[-1], end_node)
            continue

        for node, extra_node in available_actions:
            new_cost = cost + state.shortest_length(node_route[-1], node)
            lower_bound = new_cost + heuristic_functions[heuristic](node, available_actions - {(node, extra_node)}, end_node, state)
            if lower_bound > min_cost:
                continue

            new_route = node_route + [node]
            new_actions = available_actions - {(node, extra_node)}
            if extra_node is not None:
                new_actions = new_actions | {(extra_node, None)}
            heapq.heappush(routes, (new_cost, new_route, end_node_remaining, new_actions))

    raise ValueError("No route found")

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