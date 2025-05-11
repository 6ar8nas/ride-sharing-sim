import heapq
import itertools
from typing import Callable, Optional, Literal

import numpy as np
from numba import njit, types, int64
from numba.typed import Dict, List


@njit
def held_karp_pc(
    start_node: int,
    end_node: int,
    constrained_node_pairs: np.ndarray,
    shortest_lengths: np.ndarray,
    threshold: float = 1e18,
) -> tuple[List, float]:
    start_city, end_city = 0, 1
    k = constrained_node_pairs.shape[0]
    flat_nodes = constrained_node_pairs.reshape(2 * k)
    city_node_dict = Dict.empty(key_type=types.int64, value_type=types.int64)
    city_node_dict[start_city] = start_node
    city_node_dict[end_city] = end_node
    for i in range(flat_nodes.shape[0]):
        city_node_dict[i + 2] = flat_nodes[i]

    n = 2 + flat_nodes.shape[0]
    size = 1 << n
    dp = np.full((size, n), threshold, dtype=np.float64)
    parent = np.full((size, n), -1, dtype=np.int64)
    dp[1][start_city] = 0.0

    for subset in range(
        1, size, 2
    ):  # There's no need to iterate through subsets not containing the starting city
        # We only consider the starting city to be previous if it's the the only city visited
        prev_cities = (
            np.arange(2, n, dtype=np.int64)
            if subset != 1
            else np.array([start_city], dtype=np.int64)
        )

        for prev_city in prev_cities:
            if (subset & (1 << prev_city)) == 0:
                # Previous city must have been already visited
                continue

            # We only evaluate the end city if it's the last city to visit
            next_cities = (
                np.arange(2, n, dtype=np.int64)
                if subset != (1 << n) - 3
                else np.array([end_city], dtype=np.int64)
            )

            for next_city in next_cities:
                if (subset & (1 << next_city)) or (
                    next_city % 2 == 1 and (subset & (1 << (next_city - 1))) == 0
                ):  # The next city must be unvisited, and if constrained, the predecessor must have been visited
                    continue

                new_subset = subset | (1 << next_city)
                new_cost = (
                    dp[subset][prev_city]
                    + shortest_lengths[city_node_dict[prev_city]][
                        city_node_dict[next_city]
                    ]
                )

                if new_cost < dp[new_subset][next_city]:
                    dp[new_subset][next_city] = new_cost
                    parent[new_subset][next_city] = prev_city

    route = List.empty_list(int64)
    subset, prev = (1 << n) - 1, end_city
    cost = dp[subset][prev]
    while prev != -1:
        new_prev = parent[subset][prev]
        subset ^= 1 << prev
        if new_prev != prev:
            route.append(prev)
            prev = new_prev

    translated_route = List.empty_list(types.int64)
    for i in range(len(route) - 1, -1, -1):
        translated_route.append(city_node_dict[route[i]])

    return translated_route, cost


def dijkstra_routing(
    start_node: int,
    end_node: int,
    constrained_node_pairs: np.ndarray,
    shortest_lengths: np.ndarray,
) -> tuple[list[int], float]:
    routes: list[
        tuple[float, list[int], bool, frozenset[tuple[int, Optional[int]]]]
    ] = [(0, [start_node], True, frozenset(map(tuple, constrained_node_pairs)))]

    min_cost = float("inf")
    while routes:
        cost, node_route, end_node_remaining, available_actions = heapq.heappop(routes)

        if not available_actions:
            if not end_node_remaining:
                return node_route, cost
            heapq.heappush(
                routes, (cost, node_route, False, frozenset({(end_node, None)}))
            )
            final_cost = cost + shortest_lengths[node_route[-1], end_node]
            if final_cost < min_cost:
                min_cost = final_cost
            continue

        for node, extra_node in available_actions:
            new_cost = cost + shortest_lengths[node_route[-1], node]
            if new_cost > min_cost:
                continue
            new_route = node_route + [node]
            new_actions = available_actions - {(node, extra_node)}
            if extra_node is not None:
                new_actions = new_actions | {(extra_node, None)}
            heapq.heappush(
                routes, (new_cost, new_route, end_node_remaining, new_actions)
            )

    return [], float("inf")


def single_link_heuristic(
    current_node: int,
    available_actions: frozenset[tuple[int, Optional[int]]],
    end_node: int,
    shortest_lengths: np.ndarray,
) -> float:
    lb = shortest_lengths[current_node, end_node]
    remaining_nodes = {
        node for node in itertools.chain.from_iterable(available_actions)
    }
    remaining_nodes.add(end_node)
    remaining_nodes.discard(None)

    if len(remaining_nodes) == 1:
        return lb

    lb += sum(
        min(shortest_lengths[node, other] for other in remaining_nodes if node != other)
        for node in remaining_nodes
    )
    return lb


def nearest_neighbor_heuristic(
    current_node: int,
    available_actions: frozenset[tuple[int, Optional[int]]],
    end_node: int,
    shortest_lengths: np.ndarray,
) -> float:
    lb = shortest_lengths[current_node, end_node]
    remaining_nodes = {
        node for node in itertools.chain.from_iterable(available_actions)
    }
    remaining_nodes.add(end_node)
    remaining_nodes.discard(None)

    while remaining_nodes:
        nearest = min(
            remaining_nodes,
            key=lambda node: shortest_lengths[current_node, node],
        )
        lb += shortest_lengths[current_node, nearest]
        remaining_nodes.remove(nearest)
        current_node = nearest

    return lb


heuristic_functions: dict[
    Literal["single-link", "nearest-neighbor"],
    Callable[[int, frozenset[tuple[int, Optional[int]]], int, np.ndarray], float],
] = {
    "single-link": single_link_heuristic,
    "nearest-neighbor": nearest_neighbor_heuristic,
}


def branch_bound_pc(
    start_node: int,
    end_node: int,
    constrained_node_pairs: np.ndarray,
    shortest_lengths: np.ndarray,
    heuristic: Literal["single-link", "nearest-neighbor"] = "single-link",
) -> tuple[list[int], float]:
    routes: list[
        tuple[float, list[int], bool, frozenset[tuple[int, Optional[int]]]]
    ] = [(0, [start_node], True, frozenset(map(tuple, constrained_node_pairs)))]

    best_cost = float("inf")
    best_route = []
    while routes:
        cost, node_route, end_node_remaining, available_actions = heapq.heappop(routes)
        if not available_actions:
            if end_node_remaining:
                heapq.heappush(
                    routes, (cost, node_route, False, frozenset({(end_node, None)}))
                )
            elif cost < best_cost:
                best_cost = cost
                best_route = node_route
            continue

        for node, extra_node in available_actions:
            new_cost = cost + shortest_lengths[node_route[-1], node]
            lower_bound = new_cost + heuristic_functions[heuristic](
                node,
                available_actions - {(node, extra_node)},
                end_node,
                shortest_lengths,
            )
            if lower_bound > best_cost:
                continue

            new_route = node_route + [node]
            new_actions = available_actions - {(node, extra_node)}
            if extra_node is not None:
                new_actions = new_actions | {(extra_node, None)}
            heapq.heappush(
                routes, (new_cost, new_route, end_node_remaining, new_actions)
            )

    return best_route, best_cost


def brute_force_routing(
    start_node: int,
    end_node: int,
    constrained_node_pairs: np.ndarray,
    shortest_lengths: np.ndarray,
) -> tuple[list[int], float]:
    def is_valid_route(route: list[tuple[int, int, int]]) -> bool:
        const_sat = set()
        for _, action, id in route:
            if action == 0:
                const_sat.add(id)
            elif action == 1 and id not in const_sat:
                return False
        return True

    def route_cost(route: list[tuple[int, int, int]]) -> float:
        cost = 0
        current_node = start_node
        for stop in route:
            next_node = stop[0]
            cost += shortest_lengths[current_node, next_node]
            current_node = next_node
        cost += shortest_lengths[current_node, end_node]
        return cost

    all_possible_routes = itertools.permutations(
        [(sn, 0, i) for i, (sn, _) in enumerate(constrained_node_pairs)]
        + [(en, 1, i) for i, (_, en) in enumerate(constrained_node_pairs)]
    )
    valid_routes = filter(is_valid_route, all_possible_routes)
    costs = map(lambda route: (route, route_cost(route)), valid_routes)
    optimal_route, min_cost = min(costs, key=lambda x: x[1])
    result = (
        [start_node] + list(map(lambda route: route[0], optimal_route)) + [end_node]
    )
    return result, min_cost
