import numpy as np
import osmnx as ox
import networkx as nx
import rustworkx as rx
import geopandas as gpd
import os
from numba import int64, float64

from coordinates import Coordinates
from numba.experimental import jitclass

FILE_DIR = "graph_files"


class OSMGraph:
    def __init__(
        self,
        location_name: str,
        cache=True,
    ):
        self.__location = location_name
        self.__file_name = f"{FILE_DIR}/{location_name.split(",")[0] + ".graphml"}"
        self.__cache = cache

        ox_graph = self.__create_ox_graph()
        nodes_gdf = self.__create_gdf(ox_graph)
        self.graph = self.__build_rx_graph(ox_graph, nodes_gdf)
        self.__update_all_pairs_dijkstras()

    def __create_ox_graph(self) -> nx.MultiDiGraph:
        if os.path.exists(self.__file_name):
            return ox.load_graphml(self.__file_name)

        graph = ox.graph_from_place(
            query=self.__location,
            custom_filter='["highway"~"motorway|trunk|primary|secondary|teriatry|unclassified"]',
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
    ) -> rx.PyDiGraph[Coordinates, "CityEdge"]:
        rx_graph = rx.PyDiGraph[Coordinates, CityEdge]()

        node_ids: dict[int, tuple[int, Coordinates]] = {}
        for _, row in gdf.iterrows():
            coords = Coordinates((row.geometry.x, row.geometry.y))
            node_ids[row["node_id"]] = rx_graph.add_node(coords), coords

        for u, v in graph.edges():
            node_u_idx, node_u = node_ids[u]
            node_v_idx, node_v = node_ids[v]

            dist = node_u.get_offset(node_v)

            rx_graph.add_edge(
                node_u_idx,
                node_v_idx,
                CityEdge(
                    node_u_idx,
                    node_v_idx,
                    dist,
                ),
            )
            rx_graph.add_edge(
                node_v_idx,
                node_u_idx,
                CityEdge(
                    node_v_idx,
                    node_u_idx,
                    dist,
                ),
            )

        return rx_graph

    def __update_all_pairs_dijkstras(self):
        self.__shortest_distances = rx.all_pairs_dijkstra_path_lengths(
            self.graph, edge_cost_fn=lambda e: e.distance
        )

    def build_shortest_path_distances(self) -> np.ndarray:
        arr = np.zeros((len(self.graph), len(self.graph)), dtype=float)
        for u in range(len(self.graph)):
            for v in range(len(self.graph)):
                if u == v:
                    continue

                arr[u][v] = self.__shortest_distances[u][v]

        return arr


class CityEdge:
    def __init__(
        self, starting_node_index: int, ending_node_index: int, distance: float
    ):
        self.starting_node_index = starting_node_index
        self.ending_node_index = ending_node_index
        self.distance = distance
