from typing import Optional

import pygame

from utils import DateTime
from constants import Events
from osm_graph import OSMGraph


class SimulationState(OSMGraph):
    def __init__(
        self,
        location: str,
        screen_size: tuple[float, float] = (800, 600),
        frame_rate: int = 30,
        simulation_speed: int = 1,
        data_file_name: str = "city_data.json",
    ):
        super().__init__(
            location,
            data_file_name,
            screen_size=screen_size,
        )
        self.frame_rate = frame_rate
        self.simulation_speed = simulation_speed
        self.speed_ratio = (60 / frame_rate) * simulation_speed / 3.6

    def get_time(self) -> "DateTime":
        # 1 real-life minute = 1 in-simulation hour on base simulation_speed
        return DateTime(pygame.time.get_ticks() * 0.06 * self.simulation_speed)

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

    def update_traffic(self):
        time = self.get_time()
        super().update_traffic(time)
