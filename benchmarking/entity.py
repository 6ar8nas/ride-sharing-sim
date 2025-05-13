from numba import int64, int32, float64
from numba.experimental import jitclass
from numba.typed import List
from numba import njit, types, typeof


rider_spec = [
    ("id", int64),
    ("start_node", int64),
    ("end_node", int64),
    ("distance_paid_for", float64),
]


@jitclass(rider_spec)
class Rider:
    def __init__(self, id, start_node, end_node, distance_paid_for):
        self.id = id
        self.start_node = start_node
        self.end_node = end_node
        self.distance_paid_for = distance_paid_for


sample_rider = Rider(0, 0, 0, 5.4)
rider_type = typeof(sample_rider)
rider_list_type = types.ListType(rider_type)

driver_spec = [
    ("id", int64),
    ("start_node", int64),
    ("end_node", int64),
    ("passenger_seats", int32),
    ("vacancies", int32),
    ("distance_paid_for", float64),
    ("riders", rider_list_type),
]


@jitclass(driver_spec)
class Driver:
    def __init__(
        self, id, start_node, end_node, distance_paid_for, riders, passenger_seats=4
    ):
        self.id = id
        self.start_node = start_node
        self.end_node = end_node
        self.distance_paid_for = distance_paid_for
        self.riders = riders
        self.passenger_seats = passenger_seats
        self.vacancies = passenger_seats


sample_rider_list = List.empty_list(rider_type)
sample_rider_list.append(sample_rider)
sample_driver = Driver(-1, 0, 0, 4.3, sample_rider_list)
driver_type = typeof(sample_driver)


@njit
def cost_fn_new_rider(
    driver: Driver, new_rider: Rider, route_cost: float
) -> tuple[float, float]:
    new_cost = route_cost
    for rider in driver.riders:
        new_cost -= rider.distance_paid_for
    cost_curr = driver.distance_paid_for + new_rider.distance_paid_for
    offset = (new_cost - cost_curr) / 2
    return driver.distance_paid_for + offset, new_rider.distance_paid_for + offset


@njit
def rider_copy(rider: Rider) -> Rider:
    return Rider(rider.id, rider.start_node, rider.end_node, rider.distance_paid_for)


@njit
def driver_copy(driver: Driver) -> Driver:
    empty_riders_list = List.empty_list(rider_type)
    return Driver(
        driver.id,
        driver.start_node,
        driver.end_node,
        driver.distance_paid_for,
        empty_riders_list,
        driver.passenger_seats,
    )


candidate_spec = [
    ("driver", types.Optional(driver_type)),
    ("riders", types.Optional(types.ListType(rider_type))),
    ("savings", float64),
    ("route", types.Optional(types.ListType(int64))),
    ("cost", float64),
    ("iter", int64),
]


@jitclass(candidate_spec)
class Candidate:
    def __init__(self, driver, riders, savings, route, cost, iter):
        self.driver = driver
        self.riders = riders
        self.savings = savings
        self.route = route
        self.cost = cost
        self.iter = iter


sample_int_list = List.empty_list(int64)
sample_int_list.append(51)
sample_int_list.append(13)
sample_candidate = Candidate(
    sample_driver, sample_rider_list, 51.12, sample_int_list, 192.41, 12
)
candidate_type = typeof(sample_candidate)
