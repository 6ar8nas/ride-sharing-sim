from entity import Driver, Rider

def calculate_rider_statistics(riders: list[Rider]) -> dict:
    total_riders = len(riders)
    matched_riders = sum(1 for rider in riders if rider.matched_time is not None)
    completed_riders = sum(1 for rider in riders if rider.completed_time is not None)
    cancelled_riders = sum(1 for rider in riders if rider.cancelled_time is not None)

    total_waiting_time = sum(r.matched_time - r.departure_time for r in riders if r.matched_time is not None)
    total_boarding_time = sum(r.boarded_time - r.matched_time for r in riders if r.boarded_time is not None)
    total_trip_time = sum(r.completed_time - r.boarded_time for r in riders if r.completed_time is not None)
    total_cost = sum(r.current_cost for r in riders if r.completed_time is not None)
    total_cost_saved = sum(r.direct_cost - r.current_cost for r in riders if r.completed_time is not None)

    return {
        "total_riders": total_riders,
        "matched_riders": matched_riders,
        "completed_riders": completed_riders,
        "cancelled_riders": cancelled_riders,
        "average_waiting_time": total_waiting_time / matched_riders if matched_riders else None,
        "average_boarding_time": total_boarding_time / matched_riders if matched_riders else None,
        "average_rider_trip_time": total_trip_time / completed_riders if completed_riders else None,
        "average_rider_cost": total_cost / completed_riders if completed_riders else None,
        "average_rider_cost_saved": total_cost_saved / completed_riders if completed_riders else None,
    }

def calculate_driver_statistics(drivers: list[Driver]) -> dict:
    total_drivers = len(drivers)
    drivers_with_passengers = sum(1 for driver in drivers if driver.direct_cost != driver.current_cost)
    total_distance = sum(driver.total_distance for driver in drivers)
    total_trip_time = sum(driver.completed_time - driver.departure_time for driver in drivers if driver.completed_time is not None)
    total_cost = sum(d.current_cost for d in drivers if d.completed_time is not None)
    total_cost_saved = sum(d.direct_cost - d.current_cost for d in drivers if d.completed_time is not None)
    total_seats_available = sum(driver.passenger_seats for driver in drivers)

    return {
        "total_drivers": total_drivers,
        "total_distance_traveled": total_distance,
        "total_seats_available": total_seats_available,
        "average_driver_distance": total_distance / total_drivers if total_drivers else None,
        "average_driver_trip_time": total_trip_time / total_drivers if total_drivers else None,
        "average_driver_cost": total_cost / total_drivers if total_drivers else None,
        "average_driver_with_passengers_saved": total_cost_saved / drivers_with_passengers if drivers_with_passengers else None
    }

def calculate_statistics(riders: list[Rider], drivers: list[Driver]) -> dict:
    rider_stats = calculate_rider_statistics(riders)
    driver_stats = calculate_driver_statistics(drivers)

    total_simulation_runtime = (max(d.completed_time for d in drivers if d.completed_time is not None))
    total_seats_available = sum(d.passenger_seats for d in drivers)
    total_direct_distance = sum(e.direct_cost for e in riders) + sum(d.direct_cost for d in drivers)
    total_passengers_served = sum(r.passenger_count for r in riders if r.completed_time is not None)
    occupancy_rate = total_passengers_served / total_seats_available if total_seats_available else None

    return rider_stats | driver_stats | {
        "total_simulation_runtime": total_simulation_runtime,
        "total_seats_available": total_seats_available,
        "total_direct_distance": total_direct_distance,
        "total_passengers_served": total_passengers_served,
        "occupancy_rate": occupancy_rate
    }