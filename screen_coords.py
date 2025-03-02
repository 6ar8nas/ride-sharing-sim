from dataclasses import dataclass
from functools import lru_cache
from typing import Sequence


class ScreenBounds:

    def __init__(self, total_bounds: Sequence[float], screen_size: tuple[float, float]):
        self.min_x, self.min_y, self.max_x, self.max_y = total_bounds
        self.screen_width, self.screen_height = screen_size

    @lru_cache(maxsize=None)
    def get_screen_coords(self, coords: tuple[float, float]) -> tuple[float, float]:
        x_norm = (
            (coords[0] - self.min_x) / (self.max_x - self.min_x)
        ) * self.screen_width
        y_norm = (
            (self.max_y - coords[1]) / (self.max_y - self.min_y)
        ) * self.screen_height
        return x_norm, y_norm


@dataclass
class ScreenBoundedCoordinates:
    coords: tuple[float, float]
    screen_bounds: ScreenBounds

    def move(
        self, coords_dest: "ScreenBoundedCoordinates", speed: float
    ) -> tuple["ScreenBoundedCoordinates", float, bool]:
        dx, dy = (
            coords_dest.coords[0] - self.coords[0],
            coords_dest.coords[1] - self.coords[1],
        )
        distance: float = (dx**2 + dy**2) ** 0.5

        if distance <= speed:
            return coords_dest, distance, True
        else:
            ratio = speed / distance
            step_x = ratio * dx
            step_y = ratio * dy
            new_x, new_y = (self.coords[0] + step_x, self.coords[1] + step_y)

        return (
            ScreenBoundedCoordinates((new_x, new_y), self.screen_bounds),
            speed,
            False,
        )

    @property
    def on_screen(self) -> tuple[float, float]:
        return self.screen_bounds.get_screen_coords(self.coords)
