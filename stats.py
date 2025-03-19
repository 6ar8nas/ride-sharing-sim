from typing import Optional
from entity import Driver, Rider
from utils import DateTime


def calculate_rider_statistics(riders: list[Rider]) -> dict:
    total_riders = len(riders)
    completed_riders = sum(1 for rider in riders if rider.completed_time is not None)
    cancelled_riders = sum(1 for rider in riders if rider.cancelled_time is not None)
    total_trip_time: DateTime = sum(
        (
            r.completed_time - r.departure_time
            for r in riders
            if r.completed_time is not None
        ),
        DateTime(),
    )
    total_matching_time: DateTime = sum(
        (
            r.matched_time - r.departure_time
            for r in riders
            if r.completed_time is not None and r.matched_time is not None
        ),
        DateTime(),
    )
    total_boarding_time: DateTime = sum(
        (
            r.boarded_time - r.matched_time
            for r in riders
            if r.completed_time is not None
            and r.boarded_time is not None
            and r.matched_time is not None
        ),
        DateTime(),
    )
    total_travel_time: DateTime = sum(
        (
            r.completed_time - r.boarded_time
            for r in riders
            if r.completed_time is not None and r.boarded_time is not None
        ),
        DateTime(),
    )
    total_initial_cost = sum(
        r.direct_cost for r in riders if r.completed_time is not None
    )
    total_cost = sum(r.current_cost for r in riders if r.completed_time is not None)

    return {
        "riders_total": total_riders,
        "rider_completed_ratio": (
            completed_riders / total_riders if total_riders else None
        ),
        "rider_cancelled_ratio": (
            cancelled_riders / total_riders if total_riders else None
        ),
        "rider_time_trip_total": (
            total_trip_time / completed_riders if completed_riders else None
        ),
        "rider_time_ratio_matching": (
            total_matching_time / total_trip_time if total_trip_time else None
        ),
        "rider_time_ratio_boarding": (
            total_boarding_time / total_trip_time if total_trip_time else None
        ),
        "rider_time_ratio_traveling": (
            total_travel_time / total_trip_time if total_trip_time else None
        ),
        "rider_price_ratio": (
            total_cost / total_initial_cost if total_initial_cost else None
        ),
    }


def calculate_driver_statistics(drivers: list[Driver]) -> dict:
    total_drivers = len(drivers)
    completed_drivers = sum(
        1 for driver in drivers if driver.completed_time is not None
    )
    drivers_with_passengers = sum(
        1 for driver in drivers if driver.direct_cost != driver.current_cost
    )
    total_trip_time: DateTime = sum(
        (
            driver.completed_time - driver.departure_time
            for driver in drivers
            if driver.completed_time is not None
        ),
        DateTime(),
    )
    total_distance = sum(
        d.total_distance for d in drivers if d.completed_time is not None
    )
    total_initial_cost = sum(
        d.direct_cost for d in drivers if d.completed_time is not None
    )
    total_cost = sum(d.current_cost for d in drivers if d.completed_time is not None)
    total_involved_distance = sum(
        d.total_distance
        for d in drivers
        if d.completed_time is not None and d.current_cost != d.direct_cost
    )
    total_involved_initial_cost = sum(
        d.direct_cost
        for d in drivers
        if d.completed_time is not None and d.current_cost != d.direct_cost
    )
    total_involved_cost = sum(
        d.current_cost
        for d in drivers
        if d.completed_time is not None and d.current_cost != d.direct_cost
    )

    return {
        "drivers_total": total_drivers,
        "driver_matched_ratio": (
            drivers_with_passengers / total_drivers if total_drivers else None
        ),
        "driver_time_trip_total": (
            total_trip_time / completed_drivers if completed_drivers else None
        ),
        "driver_distance_ratio": (
            total_distance / total_initial_cost if total_initial_cost else None
        ),
        "driver_distance_involved_ratio": (
            total_involved_distance / total_involved_initial_cost
            if total_involved_initial_cost
            else None
        ),
        "driver_price_ratio": (
            total_cost / total_initial_cost if total_initial_cost else None
        ),
        "driver_price_involved_ratio": (
            total_involved_cost / total_involved_initial_cost
            if total_involved_initial_cost
            else None
        ),
    }


def calculate_statistics(
    riders: list[Rider], drivers: list[Driver], current_time: Optional[DateTime]
) -> dict:
    rider_stats = calculate_rider_statistics(riders)
    driver_stats = calculate_driver_statistics(drivers)

    total_seats = sum(
        d.passenger_seats for d in drivers if d.completed_time is not None
    )
    total_passengers = sum(
        r.passenger_count for r in riders if r.completed_time is not None
    )
    total_distance = sum(
        d.total_distance for d in drivers if d.completed_time is not None
    )
    total_direct_distance = sum(
        r.direct_cost for r in riders if r.completed_time is not None
    ) + sum(d.direct_cost for d in drivers if d.completed_time is not None)

    return (
        rider_stats
        | driver_stats
        | {
            "simulation_runtime": current_time,
            "total_distance_ratio": (
                total_distance / total_direct_distance
                if total_direct_distance
                else None
            ),
            "seat_occupancy_rate": (
                total_passengers / total_seats if total_seats else None
            ),
        }
    )
