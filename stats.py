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
    total_single_trip_distance = sum(
        r.single_trip_distance for r in riders if r.completed_time is not None
    )
    total_distance_paid_for = sum(
        r.distance_paid_for for r in riders if r.completed_time is not None
    )

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
        "rider_time_matching": (
            total_matching_time / completed_riders if completed_riders else None
        ),
        "rider_time_boarding": (
            total_boarding_time / completed_riders if completed_riders else None
        ),
        "rider_time_traveling": (
            total_travel_time / completed_riders if completed_riders else None
        ),
        "rider_price_ratio": (
            total_distance_paid_for / total_single_trip_distance
            if total_single_trip_distance
            else None
        ),
    }


def calculate_driver_statistics(drivers: list[Driver]) -> dict:
    total_drivers = len(drivers)
    completed_drivers = sum(
        1 for driver in drivers if driver.completed_time is not None
    )
    drivers_with_passengers = sum(
        1
        for driver in drivers
        if len(driver.completed_riders) > 0 and driver.completed_time is not None
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
    total_single_trip_distance = sum(
        d.single_trip_distance for d in drivers if d.completed_time is not None
    )
    total_cost = sum(
        d.distance_paid_for for d in drivers if d.completed_time is not None
    )
    total_involved_distance = sum(
        d.total_distance
        for d in drivers
        if len(d.completed_riders) > 0 and d.completed_time is not None
    )
    total_involved_single_trip_distance = sum(
        d.single_trip_distance
        for d in drivers
        if len(d.completed_riders) > 0 and d.completed_time is not None
    )
    total_involved_cost = sum(
        d.distance_paid_for
        for d in drivers
        if len(d.completed_riders) > 0 and d.completed_time is not None
    )

    return {
        "drivers_total": total_drivers,
        "driver_involved_ratio": (
            drivers_with_passengers / total_drivers if total_drivers else None
        ),
        "driver_time_trip_total": (
            total_trip_time / completed_drivers if completed_drivers else None
        ),
        "driver_distance_ratio": (
            total_distance / total_single_trip_distance
            if total_single_trip_distance
            else None
        ),
        "driver_distance_involved_ratio": (
            total_involved_distance / total_involved_single_trip_distance
            if total_involved_single_trip_distance
            else None
        ),
        "driver_price_ratio": (
            total_cost / total_single_trip_distance
            if total_single_trip_distance
            else None
        ),
        "driver_price_involved_ratio": (
            total_involved_cost / total_involved_single_trip_distance
            if total_involved_single_trip_distance
            else None
        ),
    }


def calculate_statistics(
    riders: list[Rider],
    drivers: list[Driver],
    current_time: Optional[DateTime],
    fps: float,
) -> dict:
    rider_stats = calculate_rider_statistics(riders)
    driver_stats = calculate_driver_statistics(drivers)

    total_seats = sum(
        d.passenger_seats for d in drivers if d.completed_time is not None
    )
    total_passengers = sum(1 for r in riders if r.completed_time is not None)
    total_no_traffic_distance = sum(
        d.shortest_distance for d in drivers if d.completed_time is not None
    ) + sum(r.shortest_distance for r in riders if r.completed_time is not None)
    total_traffic_distance = sum(
        d.single_trip_distance for d in drivers if d.completed_time is not None
    ) + sum(r.single_trip_distance for r in riders if r.completed_time is not None)

    return (
        rider_stats
        | driver_stats
        | {
            "simulation_runtime": current_time,
            "fps": fps,
            "seat_occupancy_rate": (
                total_passengers / total_seats if total_seats else None
            ),
            "traffic_distance_increase": (
                (total_traffic_distance / total_no_traffic_distance) - 1
                if total_no_traffic_distance
                else None
            ),
        }
    )
