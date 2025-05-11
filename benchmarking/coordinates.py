from dataclasses import dataclass


@dataclass(frozen=True)
class Coordinates:
    coords: tuple[float, float]

    def get_offset(self, coords_dest: "Coordinates") -> float:
        dx, dy = (
            coords_dest.coords[0] - self.coords[0],
            coords_dest.coords[1] - self.coords[1],
        )
        return (dx**2 + dy**2) ** 0.5
