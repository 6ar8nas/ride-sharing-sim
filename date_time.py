from typing import Literal


class DateTime(int):
    sec_per_day = 86400

    @staticmethod
    def from_hms(hours: int, minutes: int, seconds: int) -> "DateTime":
        return DateTime(hours * 3600 + minutes * 60 + seconds)

    @property
    def day_time(self) -> "DateTime":
        return DateTime(self % DateTime.sec_per_day)

    def is_within_rush_time(self) -> Literal["Morning", "Evening", False]:
        time = self.day_time
        if time >= DateTime.from_hms(7, 00, 0) and time <= DateTime.from_hms(10, 0, 0):
            return "Morning"
        if time >= DateTime.from_hms(16, 00, 0) and time <= DateTime.from_hms(19, 0, 0):
            return "Evening"
        return False

    def is_night_time(self) -> bool:
        return self.day_time < DateTime.from_hms(6, 0, 0)

    def __str__(self) -> str:
        minutes, seconds = divmod(self, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.__str__()})"

    def __add__(self, value: "DateTime") -> "DateTime":
        return DateTime(super().__add__(value))

    def __sub__(self, value: "DateTime") -> "DateTime":
        return DateTime(super().__sub__(value))

    def __truediv__(self, value: int) -> "DateTime":
        return DateTime(super().__floordiv__(value))
