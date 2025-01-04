from enum import Enum, StrEnum

class Events(StrEnum):
    NewDriver = "new-driver"
    NewRider = "new-rider"
    RiderMatch = "rider-match"
    RiderPickup = "rider-pickup"
    RiderDropOff = "rider-drop-off"
    RiderCancelled = "rider-cancelled"
    DriverComplete = "driver-complete"

class Colors(Enum):
    Background = (255, 255, 255)
    Building = (100, 100, 100)
    Edge = (140, 140, 140)
    Driver = (0, 0, 255)
    IdleRider = (255, 0, 0)
    WaitingRider = (255, 165, 0)
    DestinationPoint = (0, 255, 100)
    Route = (40, 40, 40)