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
            return orig_dist, [], 0.0
        if k > driver.vacancies:
            return float("inf"), [], 0.0
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
            return float("inf"), [], 0.0
        return orig_dist - route_cost, route, route_cost

    def _driver_pso(
        self,
        driver: Driver,
        riders: list[Rider],
        num_particles: int = 30,
        iterations: int = 50,
    ) -> tuple[list[Rider], float, list[int], float]:
        num_riders = len(riders)
        if num_riders == 0:
            return [], 0.0, [], float("inf")

        swarm: list[list[float]] = []
        velocities: list[list[float]] = []
        pbest: list[list[float]] = []
        pbest_vals: list[tuple[float, list[int], float]] = []
        for _ in range(num_particles):
            pos = [random.uniform(-1, 1) for _ in range(num_riders)]
            vel = [random.uniform(-1, 1) for _ in range(num_riders)]
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

        for _ in range(iterations):
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
                if res[0] > gbest_val[0]:
                    gbest_val = res
                    gbest_pos = pos.copy()

        best_indices = self._decode_particle(gbest_pos)
        rids = [riders[i] for i in best_indices]
        return rids, *gbest_val

    def match_riders(self, drivers: list[Driver], riders: list[Rider]):
        unmatched = {r.id: r for r in riders}

        candidates: list[tuple[Driver, list[Rider], float, list[int], float]] = []
        for driver in drivers:
            if driver.vacancies <= 0:
                continue
            orig_dist = self.state.shortest_path_distance(
                driver.current_edge.edge.ending_node_index, driver.end_node
            )

            compat: list[Rider] = []
            for rider in riders:
                if rider.id not in unmatched or rider.matched_time is not None:
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
            riders_count = 0
            for idx, rid in enumerate(rids):
                if idx < dr.vacancies and rid.id in unmatched:
                    unmatched.pop(rid.id, None)
                    unmatched_riders.append(rid)
                    riders_count += 1

            savings_pp = savings / (riders_count + 1)
            driver_cost = dr.distance_paid_for - savings_pp
            for idx, rid in enumerate(unmatched_riders):
                rider_cost = rid.distance_paid_for - savings_pp
                dr.match_rider(
                    rid,
                    route,
                    (driver_cost, rider_cost),
                    time,
                    idx == riders_count - 1,
                )
