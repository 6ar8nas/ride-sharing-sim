from functools import lru_cache
from typing import Optional

import pygame
import rustworkx as rx

from constants import Events
from osm_graph import OSMGraph


class SimulationState(OSMGraph):
    def __init__(
        self,
        location: str,
        screen_size: tuple[float, float] = (800, 600),
        frame_rate: int = 30,
    ):
        super().__init__(location_name=location, screen_size=screen_size)
        self.frame_rate = frame_rate
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

    def get_time(self) -> "DateTime":
        # 1 real-life minute = 1 in-simulation hour
        return DateTime(pygame.time.get_ticks() * 0.06)

    def post_event(
        self,
        event_type: Events,
        rider: Optional["Rider"] = None,  # type: ignore
        driver: Optional["Driver"] = None,  # type: ignore
    ):
        pygame.event.post(
            pygame.event.Event(
                pygame.USEREVENT,
                {"event_type": event_type, "rider": rider, "driver": driver},
            )
        )


class DateTime(int):
    SEC_PER_DAY = 86400

    @staticmethod
    def from_hms(hours: int, minutes: int, seconds: int) -> "DateTime":
        return DateTime(hours * 3600 + minutes * 60 + seconds)

    @property
    def day_time(self) -> "DateTime":
        return DateTime(self % DateTime.SEC_PER_DAY)

    def __str__(self):
        minutes, seconds = divmod(self, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}"

    def __add__(self, other: "DateTime") -> "DateTime":
        return DateTime(super().__add__(other))
