from dataclasses import dataclass, field
import random
from typing import Literal
import osmnx as ox
import networkx as nx
import rustworkx as rx
import geopandas as gpd
import os

from parse_data import parse_city_data
from utils import DateTime
from coordinates import (
    Coordinates,
    ScreenBounds,
    ScreenBoundedArea,
    ScreenBoundedCoordinates,
)

FILE_DIR = "graph_files"


class OSMGraph:
    def __init__(
        self,
        location_name: str,
        data_file_name: str = "city_data.json",
        cache=True,
        screen_size: tuple[int, int] = (800, 600),
    ):
        self.__location = location_name
        self.__file_name = f"{FILE_DIR}/{location_name.split(",")[0] + ".graphml"}"
        self.__cache = cache
        self.__screen_size = screen_size
        self.__center_areas, self.__residential_areas, self.__filters = parse_city_data(
            data_file_name, location_name
        )

        self.center_locations: list[ScreenBoundedArea] = []
        self.residential_areas: list[ScreenBoundedArea] = []

        ox_graph = self.__create_ox_graph()
        nodes_gdf = self.__create_gdf(ox_graph)
        self.graph = self.__build_rx_graph(ox_graph, nodes_gdf)
        self.__update_all_pairs_dijkstras(init=True)

    def __create_ox_graph(self) -> nx.MultiDiGraph:
        if os.path.exists(self.__file_name):
            return ox.load_graphml(self.__file_name)

        graph = ox.graph_from_place(
            query=self.__location,
            custom_filter=self.__filters,
            network_type="drive",
            simplify=True,
        )
        if self.__cache:
            ox.save_graphml(graph, filepath=self.__file_name)

        return graph

    def __create_gdf(self, graph: nx.MultiDiGraph) -> gpd.GeoDataFrame:
        nodes_data = [
            {"node_id": node_id, "x": node["x"], "y": node["y"]}
            for node_id, node in graph.nodes(data=True)
        ]
        return gpd.GeoDataFrame(
            nodes_data,
            geometry=gpd.points_from_xy(
                [n["x"] for n in nodes_data], [n["y"] for n in nodes_data]
            ),
            crs="EPSG:4326",
        ).to_crs(epsg=3346)

    def __build_rx_graph(
        self, graph: nx.MultiDiGraph, gdf: gpd.GeoDataFrame
    ) -> rx.PyDiGraph["CityNode", "CityEdge"]:
        rx_graph = rx.PyDiGraph[CityNode, CityEdge]()
        screen_bounds = ScreenBounds(gdf.total_bounds, self.__screen_size)

        for area in self.__center_areas:
            self.center_locations.append(ScreenBoundedArea(area, screen_bounds))
        for area in self.__residential_areas:
            self.residential_areas.append(ScreenBoundedArea(area, screen_bounds))

        node_ids: dict[int, tuple[int, CityNode]] = {}
        for _, row in gdf.iterrows():
            coords = Coordinates((row.geometry.x, row.geometry.y))
            is_center = any(
                location.is_within_radius(coords) for location in self.center_locations
            )
            is_residential = any(
                location.is_within_radius(coords) for location in self.residential_areas
            )
            node = CityNode(
                ScreenBoundedCoordinates(coords, screen_bounds),
                is_center,
                is_residential,
            )
            node_ids[row["node_id"]] = rx_graph.add_node(node), node

        for u, v in graph.edges():
            node_u_idx, node_u = node_ids[u]
            node_v_idx, node_v = node_ids[v]

            _, _, dist = node_u.coords.get_offset(node_v.coords)
            is_center = node_u.is_center or node_v.is_center
            is_residential = node_u.is_residential or node_v.is_residential

            rx_graph.add_edge(
                node_u_idx,
                node_v_idx,
                CityEdge(
                    node_u_idx,
                    node_v_idx,
                    node_u.coords,
                    node_v.coords,
                    dist,
                    is_center,
                    is_residential,
                ),
            )
            rx_graph.add_edge(
                node_v_idx,
                node_u_idx,
                CityEdge(
                    node_v_idx,
                    node_u_idx,
                    node_v.coords,
                    node_u.coords,
                    dist,
                    is_center,
                    is_residential,
                ),
            )

        return rx_graph

    def __update_all_pairs_dijkstras(self, init=False):
        self.__shortest_paths = rx.all_pairs_dijkstra_shortest_paths(
            self.graph, edge_cost_fn=lambda e: e.distance / e.speed
        )
        # Hacking to get around the fact that rustworkx does not support tuple edge cost functions
        self.__shortest_path_distances = rx.all_pairs_dijkstra_path_lengths(
            self.graph, edge_cost_fn=lambda e: ((1000 * e.distance) / e.speed)
        )
        self.__shortest_path_distances_hacked = rx.all_pairs_dijkstra_path_lengths(
            self.graph,
            edge_cost_fn=lambda e: ((1000 * e.distance) / e.speed) + e.distance,
        )
        if init == True:
            # Distances of the graph do not change - there is no need to recompute
            self.__shortest_distances = rx.all_pairs_dijkstra_path_lengths(
                self.graph, edge_cost_fn=lambda e: e.distance
            )

    def update_traffic(self, current_time: DateTime):
        is_rush_hour = current_time.is_within_rush_time()
        for edge in self.graph.edges():
            edge.update_traffic(is_rush_hour)
            self.graph.update_edge(
                edge.starting_node_index, edge.ending_node_index, edge
            )

        self.__update_all_pairs_dijkstras()

    def shortest_distance(self, u: int, v: int) -> float:
        return self.__shortest_distances[u][v] if u != v else 0.0

    def shortest_path(self, u: int, v: int) -> list[int]:
        return self.__shortest_paths[u][v] if u != v else []

    def shortest_path_distance(self, u: int, v: int) -> float:
        if u == v:
            return 0.0

        return (
            self.__shortest_path_distances_hacked[u][v]
            - self.__shortest_path_distances[u][v]
        )


@dataclass(frozen=True)
class CityNode:
    coords: ScreenBoundedCoordinates
    is_center: bool = False
    is_residential: bool = False

    @property
    def on_screen(self) -> tuple[int, int]:
        return self.coords.on_screen


@dataclass
class CityEdge:
    starting_node_index: int
    ending_node_index: int
    starting_node_coords: ScreenBoundedCoordinates
    ending_node_coords: ScreenBoundedCoordinates
    distance: float
    is_center: bool = False
    is_residential: bool = False
    base_speed: float = 50.0
    speed = base_speed
    rush_congestion: tuple[float, float] = field(default_factory=lambda: (0.5, 0.9))
    relaxed_congestion: tuple[float, float] = field(default_factory=lambda: (0.9, 1.0))

    def update_traffic(self, is_rush_hour: Literal["Morning", "Evening", False]):
        self.speed = self.base_speed
        if (self.is_center or self.is_residential) and is_rush_hour != False:
            self.speed *= random.uniform(*self.rush_congestion)
        else:
            self.speed *= random.uniform(*self.relaxed_congestion)
