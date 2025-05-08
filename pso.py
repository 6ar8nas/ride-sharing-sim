import random
from entity import Driver, Rider
from routing import held_karp_pc
from state import SimulationState


class RideSharingPSOInstance:
    w = 0.729
    c1 = 1.5
    c2 = 1.5

    def __init__(self, state: SimulationState):
        self.state = state

    def _decode_particle(
        self, position: list[float], threshold: float = 0.0
    ) -> list[int]:
        selected = [(i, val) for i, val in enumerate(position) if val > threshold]
        selected = sorted(selected, key=lambda i: i[1], reverse=True)
        return [particle[0] for particle in selected]

    def _evaluate_solution(
        self, driver: Driver, riders: list[Rider]
    ) -> tuple[float, list[int], float]:
        orig_dist = self.state.shortest_path_distance(
            driver.current_edge.edge.ending_node_index, driver.end_node
        )
        k = len(riders)
        if k == 0:
            return 0, [], 0.0
        if k > driver.vacancies:
            return 0.0, [], 0.0
        orig_dist = orig_dist + sum(rider.distance_paid_for for rider in riders)
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

    def _driver_pso(
        self,
        driver: Driver,
        riders: list[Rider],
        num_particles: int = 30,
        iterations: int = 50,
        min_improv_particles: int = 5,
        max_no_improv_iter: int = 5,
    ) -> tuple[list[Rider], float, list[int], float]:
        num_riders = len(riders)
        if num_riders == 0:
            return [], 0.0, [], float("inf")

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
            sel = self._decode_particle(pos)
            rids = [riders[i] for i in sel]
            res = self._evaluate_solution(driver, rids)
            pbest.append(pos.copy())
            pbest_vals.append(res)

        gb_index = max(range(num_particles), key=lambda i: pbest_vals[i][0])
        gbest_pos = pbest[gb_index].copy()
        gbest_val = pbest_vals[gb_index]

        no_improv_iter = 0
        for _ in range(iterations):
            no_improv_iter += 1
            improv_particles = 0
            for i in range(num_particles):
                pos = swarm[i]
                vel = velocities[i]
                for j in range(num_riders):
                    r1, r2 = random.random(), random.random()
                    vel[j] = (
                        RideSharingPSOInstance.w * vel[j]
                        + RideSharingPSOInstance.c1 * r1 * (pbest[i][j] - pos[j])
                        + RideSharingPSOInstance.c2 * r2 * (gbest_pos[j] - pos[j])
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
        return rids, *gbest_val

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
        self, drivers: set[Driver], riders: set[Rider]
    ) -> tuple[int, float]:
        matches = 0
        expected_savings = 0.0
        unmatched = {r.id: r for r in riders}
        candidates: list[tuple[Driver, list[Rider], float, list[int], float]] = []
        for driver in drivers:
            if (
                driver.vacancies <= 0
                or driver.current_edge.edge.ending_node_index == driver.end_node
            ):
                continue

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
                continue

            selected, savings, route, route_cost = self._driver_pso(driver, compat)
            if len(selected) != 0:
                candidates.append((driver, selected, savings, route, route_cost))

        candidates.sort(key=lambda x: x[2], reverse=True)
        time = self.state.get_time()
        for dr, rids, savings, route, route_cost in candidates:
            unmatched_riders: list[Rider] = []
            riders_dist = dr.distance_paid_for
            riders_count = 0
            for idx, rid in enumerate(rids):
                if (
                    idx < dr.vacancies
                    and rid.id in unmatched
                    and rid.cancelled_time is None
                ):
                    unmatched.pop(rid.id, None)
                    unmatched_riders.append(rid)
                    riders_dist += rid.distance_paid_for
                    riders_count += 1

            savings = riders_dist + dr.distance_paid_for - route_cost
            half_savings = savings * 0.5
            driver_cost = dr.distance_paid_for - half_savings
            for idx, rid in enumerate(unmatched_riders):
                rider_cost = (rid.distance_paid_for / riders_dist) * half_savings
                dr.match_rider(
                    rid,
                    route,
                    (driver_cost, rider_cost),
                    time,
                    idx == riders_count - 1,
                )
            expected_savings += savings
            matches += len(unmatched_riders)

        return matches, expected_savings
