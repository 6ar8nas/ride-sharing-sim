import osmnx as ox
import networkx as nx
import rustworkx as rx
import geopandas as gpd
import os

from screen_coords import ScreenBoundedCoordinates, ScreenBounds

FILE_DIR = "graph_files"


class OXGraph:
    def __init__(
        self,
        location_name: str,
        filters: str = '["highway"~"motorway|trunk|primary|secondary|teriatry"]',
        cache=True,
        screen_size: tuple[int, int] = (1280, 720),
    ):
        super().__init__()
        self.__location = location_name
        self.__file_name = f"{FILE_DIR}/{location_name.split(",")[0] + ".graphml"}"
        self.__filters = filters
        self.__cache = cache
        self.__screen_size = screen_size

        ox_graph = self.__create_ox_graph()
        nodes_gdf = self.__create_gdf(ox_graph)
        self.graph, self.nodes, self.edges = self.__build_rx_graph(ox_graph, nodes_gdf)

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
    ) -> tuple[
        rx.PyGraph, dict[int, ScreenBoundedCoordinates], dict[tuple[int, int], float]
    ]:
        rx_graph = rx.PyGraph()
        node_ids: dict[int, int] = {}
        screen_bounds = ScreenBounds(gdf.total_bounds, self.__screen_size)
        nodes: dict[int, ScreenBoundedCoordinates] = {}

        node_coords = {
            row["node_id"]: (row.geometry.x, row.geometry.y)
            for _, row in gdf.iterrows()
        }
        for node_id, (x, y) in node_coords.items():
            node_ids[node_id] = rx_graph.add_node((x, y))
            nodes[node_ids[node_id]] = ScreenBoundedCoordinates((x, y), screen_bounds)

        edges: dict[tuple[int, int], float] = {}
        for u, v in graph.edges():
            x1, y1 = node_coords[u]
            x2, y2 = node_coords[v]
            dist = ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5
            rx_graph.add_edge(node_ids[u], node_ids[v], dist)
            edges[(node_ids[u], node_ids[v])] = dist

        return rx_graph, nodes, edges
