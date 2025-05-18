import time
from entity import (
    rider_type,
    driver_type,
    sample_rider,
    sample_driver,
    driver_copy,
    rider_copy,
)
from osm_graph import OSMGraph
from pso import pso_match_riders
from static_matching import static_rider_matching
from simulation_gen import SimulationGenerator
from numba.typed import List
from numba import int64

state = OSMGraph("Vilnius, Lithuania")
shortest_lengths = state.build_shortest_path_distances()
sim_gen = SimulationGenerator(shortest_lengths, state)

# region Helper utils
riders_mock = List.empty_list(rider_type)
riders_mock.append(sample_rider)
drivers_mock = List.empty_list(driver_type)
drivers_mock.append(sample_driver)
# Eager compile of the njit functions
pso_match_riders(
    riders_mock,
    drivers_mock,
    shortest_lengths,
)

# endregion

param_sets = [
    ("Static", (), 0),
    ("PSO", ((0.9, 0.0), (2.5, -2.0), (0.5, 2.0)), 40),
]

iterations = 5
max_drivers_count = 1000
max_riders_count = 2500

drivers_step = max_drivers_count // 10
drivers = List.empty_list(driver_type)
for drivers_count in range(drivers_step, max_drivers_count + 1, drivers_step):
    for i in range(drivers_count - len(drivers)):
        drivers.append(sim_gen.new_driver())

    riders = List.empty_list(rider_type)
    riders_step = max_riders_count // 10
    for riders_count in range(riders_step, max_riders_count + 1, riders_step):
        for j in range(riders_count - len(riders)):
            riders.append(sim_gen.new_rider())

        if drivers_count == drivers_step and riders_count == riders_step:
            # Warm up njit code
            riders_copy = [rider_copy(rider) for rider in riders]
            drivers_copy = [driver_copy(driver) for driver in drivers]
            pso_match_riders(
                riders_copy,
                drivers_copy,
                shortest_lengths,
            )

            riders_copy = [rider_copy(rider) for rider in riders]
            drivers_copy = [driver_copy(driver) for driver in drivers]
            static_rider_matching(
                riders_copy, drivers_copy, shortest_lengths
            )

        for model, params, num_particles in param_sets:
            total_savings, total_matches, total_time = 0.0, 0.0, 0.0
            iters_list = List.empty_list(int64)

            for _ in range(iterations):
                riders_copy = [rider_copy(rider) for rider in riders]
                drivers_copy = [driver_copy(driver) for driver in drivers]
                if model == "Static":
                    t0 = time.time()
                    _, matches, savings = static_rider_matching(
                        riders_copy, drivers_copy, shortest_lengths
                    )
                    t1 = time.time()
                else:
                    w_start, w_step = params[0]
                    c1_start, c1_step = params[1]
                    c2_start, c2_step = params[2]
                    t0 = time.time()
                    _, matches, savings, iters = pso_match_riders(
                        riders_copy,
                        drivers_copy,
                        shortest_lengths,
                        w_start,
                        w_step,
                        c1_start,
                        c1_step,
                        c2_start,
                        c2_step,
                        num_particles,
                    )
                    t1 = time.time()
                    for value in iters:
                        iters_list.append(value)

                total_time += t1 - t0
                total_savings += savings
                total_matches += matches

            avg_time = total_time / iterations
            avg_savings = total_savings / iterations
            avg_matches = total_matches / iterations

            total = 0.0
            for value in iters_list:
                total += value
            avg_iter = total / max(len(iters_list), 1)

            print(
                f"{drivers_count}, {riders_count}, {model}, {avg_time:.2f}, {avg_savings:.2f}, {avg_matches:.1f}, {avg_iter:.1f}"
            )
