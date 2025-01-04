from typing import Tuple
import rustworkx as rx

from graph_gen import map_to_graph

class SimulationState:
    def __init__(self, location: str, screen_size: Tuple[int, int]):
        self.__graph, self.nodes, self.__node_ids, self.edges = map_to_graph(location, screen_size)
        self.__shortest_paths = rx.all_pairs_dijkstra_shortest_paths(self.__graph, edge_cost_fn=lambda e: e)
        self.__shortest_lengths = rx.all_pairs_dijkstra_path_lengths(self.__graph, edge_cost_fn=lambda e: e)

    def shortest_length(self, u: int, v: int) -> float:
        return self.__shortest_lengths[u][v] if u != v else 0

    def shortest_path(self, u: int, v: int) -> list[int]:
        return self.__shortest_paths[u][v] if u != v else []