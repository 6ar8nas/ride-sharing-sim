import time

from entity import Driver, Rider
from matching import static_rider_matching
from pso import RideSharingPSOInstance
from simulation_gen import SimulationGenerator
from state import SimulationState

state = SimulationState("Vilnius, Lithuania", benchmarking=True)
sim_gen = SimulationGenerator(state)
matcher = RideSharingPSOInstance(state)

iterations = 10
max_drivers_count = 10
max_riders_count = 10

drivers: set[Driver] = set()
curr_time = state.get_time()
drivers_step = max_drivers_count // 10
for drivers_count in range(drivers_step, max_drivers_count + 1, drivers_step):
    for _ in range(drivers_count - len(drivers)):  # Add the *remaining* drivers
        drivers.add(sim_gen.new_driver(curr_time))
    riders: set[Rider] = set()
    riders_step = max_riders_count // 10
    for riders_count in range(riders_step, max_riders_count + 1, riders_step):
        for _ in range(riders_count - len(riders)):  # Add the *remaining* riders
            riders.add(sim_gen.new_rider(curr_time))
        time_static, time_pso = 0.0, 0.0
        matches_static, matches_pso = 0.0, 0.0
        savings_static, savings_pso = 0.0, 0.0
        for i in range(iterations):
            riders_copy = riders.copy()
            drivers_copy = drivers.copy()
            t0 = time.time()
            m0, s0 = static_rider_matching(riders_copy, drivers_copy, state, curr_time)
            t1 = time.time()
            riders_copy = riders.copy()
            drivers_copy = drivers.copy()
            t2 = time.time()
            m1, s1 = matcher.match_riders(drivers_copy, riders_copy)
            t3 = time.time()

            time_static += t1 - t0
            time_pso += t3 - t2

            matches_static += m0
            matches_pso += m1
            savings_static += s0
            savings_pso += s1

        time_static /= iterations
        time_pso /= iterations
        matches_static /= iterations
        matches_pso /= iterations
        savings_static /= iterations
        savings_pso /= iterations

        print(f"drivers: {drivers_count}, riders: {riders_count}, avg 1/{iterations}:")
        print(f"{time_static:9.2e} {time_pso:9.2e}")
        print(f"{matches_static:9.2} {matches_pso:9.2}")
        print(f"{savings_static:9.2e} {savings_pso:9.2e}")
