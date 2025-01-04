from enum import Enum, StrEnum

class Events(StrEnum):
    NewDriver = "new-driver"
    NewRider = "new-rider"
    DriverComplete = "driver-complete"

class Colors(Enum):
    Background = (255, 255, 255)
    Building = (100, 100, 100)
    Edge = (140, 140, 140)
    Driver = (0, 0, 255)
    IdleRider = (255, 0, 0)
