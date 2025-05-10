import time

from entity import Driver, Rider
from pso import RideSharingPSOInstance
from matching import static_rider_matching
from simulation_gen import SimulationGenerator
from state import SimulationState

state = SimulationState("Vilnius, Lithuania", benchmarking=True)
sim_gen = SimulationGenerator(state)

param_sets = [
    ("Static", {}),
    (
        "PSO",
        {"w": (0.7289, 0.7289), "c1": (1.49618, 1.49618), "c2": (1.49618, 1.49618)},
    ),
    ("PSO", {"w": (0.9, 0.4), "c1": (2.0, 2.0), "c2": (2.0, 2.0)}),
    ("PSO", {"w": (0.9, 0.4), "c1": (2.5, 0.5), "c2": (0.5, 2.5)}),
]

matching_algorithms = {
    "PSO": RideSharingPSOInstance,
    "Static": static_rider_matching,
}

iterations = 3
max_drivers_count = 50
max_riders_count = 100

drivers: set[Driver] = set()
curr_time = state.get_time()
drivers_step = max_drivers_count // 5
drivers_step = max_drivers_count // 5

for drivers_count in range(drivers_step, max_drivers_count + 1, drivers_step):
    for _ in range(drivers_count - len(drivers)):
        drivers.add(sim_gen.new_driver(curr_time))

    riders: set[Rider] = set()
    riders_step = max_riders_count // 5
    for riders_count in range(riders_step, max_riders_count + 1, riders_step):
        for _ in range(riders_count - len(riders)):
            riders.add(sim_gen.new_rider(curr_time))

        print(f"\n--- Drivers: {drivers_count}, Riders: {riders_count} ---")
        for model, params in param_sets:
            total_time, total_iters = 0.0, 0.0
            total_savings, total_matches = 0.0, 0.0

            for _ in range(iterations):
                riders_copy = {r.copy() for r in riders}
                drivers_copy = {d.copy() for d in drivers}

                t0 = time.time()
                if model == "PSO":
                    matcher = matching_algorithms[model](state, **params)
                    matches, savings = matcher.match_riders(riders_copy, drivers_copy)
                    iters = matcher.iters
                elif model == "Static":
                    matches, savings = matching_algorithms[model](
                        riders_copy, drivers_copy, state
                    )
                    iters = 0.0
                t1 = time.time()

                total_time += t1 - t0
                total_iters += iters
                total_savings += savings
                total_matches += matches

            avg_time = total_time / iterations
            avg_iters = total_iters / iterations
            avg_savings = total_savings / iterations
            avg_matches = total_matches / iterations

            param_string = ""
            if model == "PSO":
                param_string = f"w=({params['w'][0]:.2f}-{params['w'][1]:.2f}), c1=({params['c1'][0]:.2f}-{params['c1'][1]:.2f}), c2=({params['c2'][0]:.2f}-{params['c2'][1]:.2f}) | "
            elif model == "Static":
                param_string = f"{'Static':45} | "

            print(
                f"{param_string}"
                f"time={avg_time:6.2f}s, iters={avg_iters:4.1f}, savings={avg_savings:10.2f}, matches={avg_matches:6.1f}"
            )
