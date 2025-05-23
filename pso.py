import random
from typing import Mapping, Optional
from entity import Driver, Rider
from routing import held_karp_pc
from state import OSMGraph
from concurrent.futures import ThreadPoolExecutor, as_completed

from utils import DateTime


class RideSharingPSOInstance:
    def __init__(
        self,
        state: OSMGraph,
        w: tuple[float, float] = (0.7298, 0.7298),
        c1: tuple[float, float] = (1.49618, 1.49618),
        c2: tuple[float, float] = (1.49618, 1.49618),
    ):
        self.state = state
        self.w_start, self.w_step = w[0], w[1] - w[0]
        self.c1_start, self.c1_step = c1[0], c1[1] - c1[0]
        self.c2_start, self.c2_step = c2[0], c2[1] - c2[0]
        self.iters = 0

    def _decode_particle(
        self, position: list[float], threshold: float = 0.0
    ) -> list[int]:
        selected = [(i, val) for i, val in enumerate(position) if val > threshold]
        selected = sorted(selected, key=lambda i: i[1], reverse=True)
        return [particle[0] for particle in selected]

    def _evaluate_solution(
        self, driver: Driver, riders: list[Rider]
    ) -> tuple[float, list[int], float]:
        k = len(riders)
        if k == 0 or k > driver.vacancies:
            return 0, [], 0.0
        orig_dist = self.state.shortest_path_distance(
            driver.current_edge.edge.ending_node_index, driver.end_node
        ) + sum(rider.distance_paid_for for rider in riders)
        route, route_cost = held_karp_pc(
            driver.current_edge.edge.ending_node_index,
            driver.end_node,
            [
                (
                    (rid.start_node, rid.end_node)
                    if rid.boarded_time is None
                    else (rid.end_node, driver.end_node)
                )
                for rid in (driver.riders)
            ]
            + [(rid.start_node, rid.end_node) for rid in (riders)],
            self.state,
            orig_dist,
        )
        if route_cost > orig_dist:
            return 0.0, [], 0.0
        return orig_dist - route_cost, route, route_cost

    def _pseudo_randomize_vector(self, len: int, max_positive: int) -> list[float]:
        if max_positive >= len:
            return [random.uniform(-1, 1) for _ in range(len)]

        result = [random.uniform(-1, 0) for _ in range(len)]
        num_positive = random.randint(0, max_positive)
        positive_indices = random.sample(range(len), num_positive)

        for index in positive_indices:
            result[index] = random.uniform(0, 1)

        return result

    def match_riders(
        self, riders: set[Rider], drivers: set[Driver], time: DateTime
    ) -> tuple[
        int,
        float,
    ]:
        matches_count = 0
        expected_savings = 0.0
        unmatched = {r.id: r for r in riders}
        candidates: list[tuple[Driver, list[Rider], float, list[int], float]] = []
        # ThreadPoolExecutor actually doesn't do anything with CPU-bound operations
        # Just imitating parallelization with this here. Benchmark-ready version includes parallelization.
        with ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(self._get_driver_candidate, dr, riders, unmatched)
                for dr in drivers
            ]
            for future in as_completed(futures):
                result = future.result()
                if result is not None:
                    candidates.append(result)

        candidates.sort(key=lambda x: x[2], reverse=True)
        for dr, rids, _, route, route_cost in candidates:
            unmatched_riders: list[Rider] = []
            riders_dist = dr.distance_paid_for
            riders_count = 0
            for idx, rid in enumerate(rids):
                if (
                    idx < dr.vacancies
                    and rid.id in unmatched
                    and rid.cancelled_time is None
                ):
                    unmatched_riders.append(rid)
                    riders_dist += rid.distance_paid_for
                    riders_count += 1

            actual_savings = riders_dist + dr.distance_paid_for - route_cost
            if actual_savings < 0:
                continue

            for rid in unmatched_riders:
                unmatched.pop(rid.id, None)

            half_savings = actual_savings * 0.5
            driver_cost = dr.distance_paid_for - half_savings
            dr.match_riders(
                driver_cost,
                [
                    (rid, (rid.distance_paid_for / riders_dist) * half_savings)
                    for rid in unmatched_riders
                ],
                route,
                time,
            )
            expected_savings += actual_savings
            matches_count += len(unmatched_riders)

        return matches_count, expected_savings

    def _get_driver_candidate(
        self,
        driver: Driver,
        riders: set[Rider],
        unmatched: Mapping[int, Rider],
    ) -> Optional[tuple[Driver, list[Rider], float, list[int], float]]:
        if (
            driver.vacancies <= 0
            or driver.current_edge is None
            or driver.current_edge.edge.ending_node_index == driver.end_node
        ):
            return None

        orig_dist = self.state.shortest_path_distance(
            driver.current_edge.edge.ending_node_index, driver.end_node
        )

        compat: list[Rider] = []
        for rider in riders:
            if (
                rider.id not in unmatched
                or rider.driver_id is not None
                or rider.cancelled_time is not None
            ):
                continue

            pickup_route = self.state.shortest_path_distance(
                driver.current_edge.edge.ending_node_index, rider.start_node
            ) + self.state.shortest_path_distance(rider.end_node, driver.end_node)

            # Greedy heuristic to ignore riders that are too far
            if orig_dist < pickup_route:
                continue

            compat.append(rider)

        if len(compat) == 0:
            return None

        selected, savings, route, route_cost = self._driver_pso(driver, compat)
        if len(selected) == 0:
            return None

        return (driver, selected, savings, route, route_cost)

    def _driver_pso(
        self,
        driver: Driver,
        riders: list[Rider],
        num_particles: int = 40,
        iterations: int = 50,
        min_improv_particles: int = 40,
        max_no_improv_iter: int = 3,
    ) -> tuple[list[Rider], float, list[int], float]:
        num_riders = len(riders)
        if num_riders == 0:
            return [], 0.0, [], 1e18

        swarm: list[list[float]] = []
        velocities: list[list[float]] = []
        pbest: list[list[float]] = []
        pbest_vals: list[tuple[float, list[int], float]] = []
        for _ in range(num_particles):
            # Using max driver.vacancies positive numbers to satisfy constraints
            pos = self._pseudo_randomize_vector(num_riders, driver.vacancies)
            vel = self._pseudo_randomize_vector(num_riders, driver.vacancies)
            swarm.append(pos)
            velocities.append(vel)
            selected = self._decode_particle(pos)
            rids = [riders[i] for i in selected]
            res = self._evaluate_solution(driver, rids)
            pbest.append(pos.copy())
            pbest_vals.append(res)

        gb_index = max(range(num_particles), key=lambda i: pbest_vals[i][0])
        gbest_pos = pbest[gb_index].copy()
        gbest_val = pbest_vals[gb_index]

        no_improv_iter = 0
        for it in range(iterations):
            no_improv_iter += 1
            improv_particles = 0
            progress = it / iterations
            w = self.w_start + self.w_step * progress
            c1 = self.c1_start + self.c1_step * progress
            c2 = self.c2_start + self.c2_step * progress
            for i in range(num_particles):
                pos = swarm[i]
                vel = velocities[i]
                for j in range(num_riders):
                    r1, r2 = random.random(), random.random()
                    vel[j] = (
                        w * vel[j]
                        + c1 * r1 * (pbest[i][j] - pos[j])
                        + c2 * r2 * (gbest_pos[j] - pos[j])
                    )
                    pos[j] += vel[j]
                sel = self._decode_particle(pos)
                rids = [riders[i] for i in sel]
                res = self._evaluate_solution(driver, rids)
                if res[0] > pbest_vals[i][0]:
                    pbest_vals[i] = res
                    pbest[i] = pos.copy()
                    improv_particles += 1
                    if res[0] > gbest_val[0]:
                        gbest_val = res
                        gbest_pos = pos.copy()
                        no_improv_iter = 0

            if (
                no_improv_iter >= max_no_improv_iter
                or improv_particles < min_improv_particles
            ):
                # Shortcircuit if no improvement was made in a while
                break

        best_indices = self._decode_particle(gbest_pos)
        rids = [riders[i] for i in best_indices]
        self.iters += it
        return rids, *gbest_val
