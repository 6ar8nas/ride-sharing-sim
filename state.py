from functools import lru_cache
import rustworkx as rx

from osm_graph import OSMGraph


class SimulationState(OSMGraph):
    def __init__(self, location: str, screen_size: tuple[float, float] = (800, 600)):
        super().__init__(location_name=location, screen_size=screen_size)
        self.__shortest_paths = rx.all_pairs_dijkstra_shortest_paths(
            self.graph, edge_cost_fn=lambda e: e
        )
        self.__shortest_lengths = rx.all_pairs_dijkstra_path_lengths(
            self.graph, edge_cost_fn=lambda e: e
        )

    @lru_cache(maxsize=None)
    def shortest_length(self, u: int, v: int) -> float:
        return self.__shortest_lengths[u][v] if u != v else 0

    @lru_cache(maxsize=None)
    def shortest_path(self, u: int, v: int) -> list[int]:
        return self.__shortest_paths[u][v] if u != v else []
