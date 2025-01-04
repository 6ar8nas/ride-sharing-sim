from typing import Tuple

import rustworkx as rx
import geopandas as gpd
import osmnx as ox

def map_to_graph(location_name: str, screen_bounds: Tuple[int, int] = (800, 600)) -> Tuple[rx.PyGraph, dict[int, Tuple[float, float]], dict[int, int], dict[Tuple[int, int], float]]:
    G = ox.graph_from_place(location_name, network_type="drive")
    rx_graph = rx.PyGraph()

    node_ids: dict[int, int] = {}
    nodes_data = [
        {"node_id": node_id, "x": node['x'], "y": node['y']}
        for node_id, node in G.nodes(data=True)
    ]
    gdf = gpd.GeoDataFrame(
        nodes_data, geometry=gpd.points_from_xy([n['x'] for n in nodes_data], [n['y'] for n in nodes_data]), crs="EPSG:4326"
    ).to_crs(epsg=3857)

    min_x, min_y, max_x, max_y = gdf.total_bounds
    gdf['x_norm'] = ((gdf.geometry.x - min_x) / (max_x - min_x)) * screen_bounds[0]
    gdf['y_norm'] = ((max_y - gdf.geometry.y) / (max_y - min_y)) * screen_bounds[1]

    nodes: dict[int, Tuple[float, float]] = {}
    for _, row in gdf.iterrows():
        node_ids[row['node_id']] = rx_graph.add_node((row['x_norm'], row['y_norm']))
        nodes[node_ids[row['node_id']]] = (row['x_norm'], row['y_norm'])

    edges: dict[Tuple[int, int], float] = {}
    for u, v, data in G.edges(data=True):
        rx_graph.add_edge(node_ids[u], node_ids[v], float(data['length']))
        edges[(node_ids[u], node_ids[v])] = float(data['length'])

    return rx_graph, nodes, node_ids, edges