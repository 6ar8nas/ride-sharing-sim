import time

from entity import Driver, Rider
from matching import static_rider_matching
from pso import RideSharingPSOInstance
from simulation_gen import SimulationGenerator
from state import SimulationState

state = SimulationState("Vilnius, Lithuania")
sim_gen = SimulationGenerator(state)
matcher = RideSharingPSOInstance(state)

iterations = 10
drivers_count = 10
riders_count = 10

drivers: set[Driver] = set()

curr_time = state.get_time()
for drivers_count in range(1, drivers_count):
    drivers.add(sim_gen.new_driver(curr_time))
    riders: set[Rider] = set()
    for riders_count in range(1, riders_count):
        riders.add(sim_gen.new_rider(curr_time))
        time_static, time_pso = 0, 0
        for i in range(iterations):
            riders_copy = riders.copy()
            drivers_copy = drivers.copy()
            t0 = time.time()
            static_rider_matching(riders_copy, drivers_copy, state, curr_time)
            t1 = time.time()
            riders_copy = riders.copy()
            drivers_copy = drivers.copy()
            t2 = time.time()
            matcher.match_riders(drivers_copy, riders_copy)
            t3 = time.time()

            time_static += t1 - t0
            time_pso += t3 - t2

        time_static /= iterations
        time_pso /= iterations

        print(f"drivers: {drivers_count}, riders: {riders_count}, avg 1/{iterations}:")
        print(f"{time_static:9.2e} {time_pso:9.2e}")
