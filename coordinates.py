from dataclasses import dataclass
from functools import lru_cache
from typing import Sequence


@dataclass(frozen=True)
class Coordinates:
    coords: tuple[float, float]

    def get_offset(self, coords_dest: "Coordinates") -> tuple[float, float, float]:
        dx, dy = (
            coords_dest.coords[0] - self.coords[0],
            coords_dest.coords[1] - self.coords[1],
        )
        return dx, dy, (dx**2 + dy**2) ** 0.5

    def is_within_radius(self, coords_dest: "Coordinates", radius: float) -> bool:
        return (coords_dest.coords[0] - self.coords[0]) ** 2 + (
            coords_dest.coords[1] - self.coords[1]
        ) ** 2 <= radius**2

    def move(
        self, coords_dest: "Coordinates", speed: float
    ) -> tuple["Coordinates", float, bool]:
        dx, dy, distance = self.get_offset(coords_dest)

        if distance <= speed:
            return coords_dest, distance, True
        else:
            ratio = speed / distance
            step_x = ratio * dx
            step_y = ratio * dy
            new_x, new_y = (self.coords[0] + step_x, self.coords[1] + step_y)

        return (Coordinates((new_x, new_y)), speed, False)


class ScreenBounds:
    def __init__(self, total_bounds: Sequence[float], screen_size: tuple[float, float]):
        self.min_x, self.min_y, self.max_x, self.max_y = total_bounds
        self.screen_width, self.screen_height = screen_size

    @lru_cache(maxsize=None)
    def get_screen_coords(self, coords: Coordinates) -> tuple[float, float]:
        x_norm = (
            (coords.coords[0] - self.min_x) / (self.max_x - self.min_x)
        ) * self.screen_width
        y_norm = (
            (self.max_y - coords.coords[1]) / (self.max_y - self.min_y)
        ) * self.screen_height
        return x_norm, y_norm

    @lru_cache(maxsize=None)
    def get_radius(self, distance: float) -> tuple[float, float]:
        width = distance * self.screen_width / (self.max_x - self.min_x)
        height = distance * self.screen_height / (self.max_y - self.min_y)
        return (width, height)


@dataclass(frozen=True)
class ScreenBoundedCoordinates:
    coords: Coordinates
    screen_bounds: ScreenBounds

    def move(
        self, coords_dest: "ScreenBoundedCoordinates", speed: float
    ) -> tuple["ScreenBoundedCoordinates", float, bool]:
        coords, distance, reached_goal = self.coords.move(coords_dest.coords, speed)
        return (
            ScreenBoundedCoordinates(coords, self.screen_bounds),
            distance,
            reached_goal,
        )

    def get_offset(
        self, coords_dest: "ScreenBoundedCoordinates"
    ) -> tuple[float, float, float]:
        return self.coords.get_offset(coords_dest.coords)

    @property
    def on_screen(self) -> tuple[float, float]:
        return self.screen_bounds.get_screen_coords(self.coords)


@dataclass(frozen=True)
class Area:
    coords: Coordinates
    radius: float

    def is_within_radius(self, coords_dest: Coordinates) -> bool:
        return self.coords.is_within_radius(coords_dest, self.radius)


@dataclass(frozen=True)
class ScreenBoundedArea:
    area: Area
    screen_bounds: ScreenBounds

    @property
    def on_screen(self) -> tuple[float, float, float, float]:
        screen_coords = self.screen_bounds.get_screen_coords(self.area.coords)
        screen_radius = self.screen_bounds.get_radius(self.area.radius)
        return (
            screen_coords[0] - screen_radius[0] / 2,
            screen_coords[1] - screen_radius[1] / 2,
            *screen_radius,
        )

    def is_within_radius(self, coords_dest: Coordinates) -> bool:
        return self.area.is_within_radius(coords_dest)
