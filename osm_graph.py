from dataclasses import dataclass, field
import random
from typing import Literal
import osmnx as ox
import networkx as nx
import rustworkx as rx
import geopandas as gpd
import os

from coordinates import (
    ScreenBounds,
    ScreenBoundedCoordinates,
    ScreenBoundedCoordinatesRadius,
)

FILE_DIR = "graph_files"


class OSMGraph:
    def __init__(
        self,
        location_name: str,
        filters: str = '["highway"~"motorway|trunk|primary|secondary|teriatry|unclassified"]',
        center_areas: list[tuple[tuple[float, float], float]] = [],
        residential_areas: list[tuple[tuple[float, float], float]] = [],
        cache=True,
        screen_size: tuple[int, int] = (800, 600),
    ):
        self.__location = location_name
        self.__file_name = f"{FILE_DIR}/{location_name.split(",")[0] + ".graphml"}"
        self.__filters = filters
        self.__center_areas = center_areas
        self.__residential_areas = residential_areas
        self.__cache = cache
        self.__screen_size = screen_size
        self.center_locations: list[ScreenBoundedCoordinatesRadius] = []
        self.residential_areas: list[ScreenBoundedCoordinatesRadius] = []

        ox_graph = self.__create_ox_graph()
        nodes_gdf = self.__create_gdf(ox_graph)
        self.graph = self.__build_rx_graph(ox_graph, nodes_gdf)
        self.__shortest_paths, self.__shortest_lengths = self.__all_pairs_dijkstras()

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
        gdf = gpd.GeoDataFrame(
            nodes_data,
            geometry=gpd.points_from_xy(
                [n["x"] for n in nodes_data], [n["y"] for n in nodes_data]
            ),
            crs="EPSG:4326",
        ).to_crs(epsg=3346)
        return gdf

    def __build_rx_graph(
        self, graph: nx.MultiDiGraph, gdf: gpd.GeoDataFrame
    ) -> rx.PyGraph["CityNode", "CityEdge"]:
        rx_graph = rx.PyGraph[CityNode, "CityEdge"]()
        screen_bounds = ScreenBounds(gdf.total_bounds, self.__screen_size)

        for coords, radius in self.__center_areas:
            self.center_locations.append(
                ScreenBoundedCoordinatesRadius(coords, screen_bounds, radius)
            )
        for coords, radius in self.__residential_areas:
            self.residential_areas.append(
                ScreenBoundedCoordinatesRadius(coords, screen_bounds, radius)
            )

        node_ids = {}
        for _, row in gdf.iterrows():
            coords = (row.geometry.x, row.geometry.y)
            is_center = any(
                location.is_within_radius(coords) for location in self.center_locations
            )
            is_residential = any(
                location.is_within_radius(coords) for location in self.residential_areas
            )
            node_ids[row["node_id"]] = rx_graph.add_node(
                CityNode(
                    ScreenBoundedCoordinates(coords, screen_bounds),
                    is_center,
                    is_residential,
                )
            )

        for u, v in graph.edges():
            node_u = rx_graph.get_node_data(node_ids[u])
            node_v = rx_graph.get_node_data(node_ids[v])

            x1, y1 = node_u.coords.coords
            x2, y2 = node_v.coords.coords
            dist = ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5
            is_center = node_u.is_center or node_v.is_center
            is_residential = node_u.is_residential or node_v.is_residential

            rx_graph.add_edge(
                node_ids[u],
                node_ids[v],
                CityEdge(dist, is_center=is_center, is_residential=is_residential),
            )

        return rx_graph

    def __all_pairs_dijkstras(
        self,
    ) -> tuple[rx.AllPairsPathMapping, rx.AllPairsPathLengthMapping]:
        shortest_paths = rx.all_pairs_dijkstra_shortest_paths(
            self.graph, edge_cost_fn=lambda e: e.distance / e.traffic_flow_rate
        )
        shortest_lengths = rx.all_pairs_dijkstra_path_lengths(
            self.graph, edge_cost_fn=lambda e: e.distance / e.traffic_flow_rate
        )
        return shortest_paths, shortest_lengths

    def update_traffic(self, is_rush_hour: Literal["Morning", "Evening", False]):
        for edge in self.graph.edges():
            edge.update_traffic(is_rush_hour)

        self.__shortest_paths, self.__shortest_lengths = self.__all_pairs_dijkstras()

    def shortest_length(self, u: int, v: int) -> float:
        return self.__shortest_lengths[u][v] if u != v else 0

    def shortest_path(self, u: int, v: int) -> list[int]:
        return self.__shortest_paths[u][v] if u != v else []


@dataclass
class CityNode:
    coords: ScreenBoundedCoordinates
    is_center: bool
    is_residential: bool


@dataclass
class CityEdge:
    distance: float
    base_speed_limit: float = 50.0
    traffic_flow_rate: float = 1.0
    is_center: bool = False
    is_residential: bool = False
    congestion_range: tuple[float, float] = field(default_factory=lambda: (0.6, 1.0))

    def update_traffic(self, is_rush_hour: Literal["Morning", "Evening", False]):
        if self.is_center:
            if is_rush_hour != False:
                self.traffic_flow_rate = random.uniform(self.congestion_range[0], 0.8)
            else:
                self.traffic_flow_rate = random.uniform(0.9, self.congestion_range[1])
        elif self.is_residential:
            if is_rush_hour != False:
                self.traffic_flow_rate = random.uniform(self.congestion_range[0], 0.85)
            else:
                self.traffic_flow_rate = random.uniform(0.95, self.congestion_range[1])
        else:
            self.traffic_flow_rate = random.uniform(0.9, 1.0)
