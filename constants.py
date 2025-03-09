from enum import StrEnum


class Events(StrEnum):
    NewDriver = "new-driver"
    NewRider = "new-rider"
    RiderMatch = "rider-match"
    RiderPickup = "rider-pickup"
    RiderDropOff = "rider-drop-off"
    RiderCancelled = "rider-cancelled"
    DriverComplete = "driver-complete"


class Colors(StrEnum):
    Background = "#ffffff"
    Building = "#646464"
    CenterArea = "#e3e3e3"
    ResidentialArea = "#f7faed"
    Edge = "#8c8c8c"
    Driver = "#0000ff"
    IdleRider = "#ff0000"
    WaitingRider = "#ffa500"
    DestinationPoint = "#00ff64"
    Route = "#282828"
    Text = "#000000"
