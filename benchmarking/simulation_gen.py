import random

import numpy as np
from entity import Driver, Rider, rider_type
from osm_graph import OSMGraph
from numba.typed import List


class SimulationGenerator:
    def __init__(self, shortest_lengths: np.ndarray, state: OSMGraph):
        self.shortest_lengths = shortest_lengths
        self.node_ids = list(state.graph.node_indices())
        self.entity_id = 0

    def new_driver(self) -> Driver:
        start_node, end_node = self.__generate_nodes()
        [passenger_count] = random.choices([1, 2, 3, 4], [0.15, 0.2, 0.05, 0.6])
        self.entity_id += 1
        riders_list = List.empty_list(rider_type)
        return Driver(
            self.entity_id,
            start_node,
            end_node,
            self.shortest_lengths[start_node][end_node],
            riders_list,
            passenger_count,
        )

    def new_rider(self) -> Rider:
        start_node, end_node = self.__generate_nodes()
        self.entity_id += 1
        return Rider(
            self.entity_id,
            start_node,
            end_node,
            self.shortest_lengths[start_node][end_node],
        )

    def __generate_nodes(self) -> tuple[int, int]:
        start_node, end_node = 0, 0
        while start_node == end_node:
            start_node, end_node = random.choices(self.node_ids, k=2)
        return start_node, end_node
