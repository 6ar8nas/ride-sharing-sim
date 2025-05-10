import time
from itertools import product

from entity import Driver, Rider
from pso import RideSharingPSOInstance
from simulation_gen import SimulationGenerator
from state import SimulationState

state = SimulationState("Vilnius, Lithuania", benchmarking=True)
sim_gen = SimulationGenerator(state)

param_sets = [
    ((0.7289, 0.7289), (1.49618, 1.49618), (1.49618, 1.49618)),
    ((0.9, 0.4), (2.0, 2.0), (2.0, 2.0)),
    ((0.9, 0.4), (2.5, 0.5), (0.5, 2.5)),
]

iterations = 3
max_drivers_count = 30
max_riders_count = 100

drivers: set[Driver] = set()
curr_time = state.get_time()
drivers_step = max_drivers_count // 5
drivers_step = max_drivers_count // 5

for drivers_count in range(drivers_step * 2, max_drivers_count + 1, drivers_step):
    for _ in range(drivers_count - len(drivers)):
        drivers.add(sim_gen.new_driver(curr_time))

    riders: set[Rider] = set()
    riders_step = max_riders_count // 5
    for riders_count in range(riders_step * 2, max_riders_count + 1, riders_step):
        for _ in range(riders_count - len(riders)):
            riders.add(sim_gen.new_rider(curr_time))

        print(f"\n--- Drivers: {drivers_count}, Riders: {riders_count} ---")
        for w, c1, c2 in param_sets:
            total_time, total_iters = 0.0, 0.0
            total_savings, total_matches = 0.0, 0.0

            for _ in range(iterations):
                riders_copy = {r.copy() for r in riders}
                drivers_copy = {d.copy() for d in drivers}
                matcher = RideSharingPSOInstance(state, w=w, c1=c1, c2=c2)
                t0 = time.time()
                matches, savings = matcher.match_riders(drivers_copy, riders_copy)
                t1 = time.time()

                total_time += t1 - t0
                total_iters += matcher.iters
                total_savings += savings
                total_matches += matches

            avg_time = total_time / iterations
            avg_iters = total_iters / iterations
            avg_savings = total_savings / iterations
            avg_matches = total_matches / iterations

            print(
                f"w={w}, c1={c1}, c2={c2} | "
                f"time={avg_time:6.2f}s, iters={avg_iters:5.1f}, savings={avg_savings:7.2f}, matches={avg_matches:5.1f}"
            )
