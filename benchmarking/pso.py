import numpy as np
from routing import held_karp_pc
from entity import Driver, driver_type, rider_type, Candidate, candidate_type
from numba import njit, int64, types, prange
from numba.typed import List, Dict

int_list_type = types.ListType(types.int64)
driver_score_type = types.Tuple((driver_type, types.float64))
rider_score_list_type = types.ListType(types.Tuple((rider_type, types.float64)))
match_type = types.Tuple((driver_score_type, rider_score_list_type, int_list_type))
pbest_val_type = types.Tuple((types.float64, int_list_type, types.float64))
rider_payments_type = types.Tuple((rider_type, types.float64))


@njit
def evaluate_solution(
    driver: Driver,
    riders: List,
    shortest_lengths: np.ndarray,
) -> tuple[float, List, float]:
    k = len(riders)
    if k == 0 or k > driver.vacancies:
        return 0.0, List.empty_list(int64), 0.0
    orig_dist = shortest_lengths[driver.start_node][driver.end_node]
    for i in range(k):
        orig_dist += riders[i].distance_paid_for

    pairs = np.empty((k, 2), dtype=np.int64)
    for i in range(k):
        pairs[i][0] = riders[i].start_node
        pairs[i][1] = riders[i].end_node

    route, route_cost = held_karp_pc(
        driver.start_node,
        driver.end_node,
        pairs,
        shortest_lengths,
        orig_dist,
    )
    if route_cost > orig_dist:
        return 0.0, List.empty_list(int64), 0.0
    return orig_dist - route_cost, route, route_cost


@njit(parallel=True)
def pso_match_riders(
    riders: List,
    drivers: List,
    shortest_lengths: np.ndarray,
    w_start: float = 0.7298,
    w_step: float = 0.0,
    c1_start: float = 1.49618,
    c1_step: float = 0.0,
    c2_start: float = 1.49618,
    c2_step: float = 0.0,
    num_particles: int = 30,
) -> tuple[List, int, float, List]:
    matches = List.empty_list(match_type)
    iters = List.empty_list(int64)
    matches_count = 0
    expected_savings = 0.0
    unmatched = Dict.empty(key_type=types.int64, value_type=rider_type)
    for r in riders:
        unmatched[r.id] = r

    results = List.empty_list(candidate_type)
    for _ in range(len(drivers)):
        results.append(Candidate(None, None, 0.0, None, 0.0, 0))

    for i in prange(len(drivers)):
        results[i] = get_driver_candidate(
            drivers[i],
            riders,
            shortest_lengths,
            w_start,
            w_step,
            c1_start,
            c1_step,
            c2_start,
            c2_step,
            num_particles,
        )

    candidates = List.empty_list(candidate_type)
    for res in results:
        if res is not None and res.driver is not None:
            candidates.append(res)

    sorted_indices = np.argsort(np.array([c.savings for c in candidates if c]))[::-1]
    for i in sorted_indices:
        candidate = candidates[i]
        unmatched_riders = List.empty_list(rider_type)
        riders_dist = candidate.driver.distance_paid_for
        riders_count = 0
        for idx in range(len(candidate.riders)):
            rid = candidate.riders[idx]
            if idx < candidate.driver.vacancies and rid.id in unmatched:
                unmatched_riders.append(rid)
                riders_dist += rid.distance_paid_for
                riders_count += 1

        actual_savings = (
            riders_dist + candidate.driver.distance_paid_for - candidate.cost
        )
        if actual_savings < 0:
            continue

        for rid in unmatched_riders:
            unmatched.pop(rid.id)

        half_savings = actual_savings * 0.5
        driver_cost = candidate.driver.distance_paid_for - half_savings
        rider_payment_list = List.empty_list(rider_payments_type)
        for rid in unmatched_riders:
            share = (rid.distance_paid_for / riders_dist) * half_savings
            rider_payment_list.append((rid, share))

        matches.append(
            (
                (candidate.driver, driver_cost),
                rider_payment_list,
                candidate.route,
            )
        )
        expected_savings += actual_savings
        matches_count += len(unmatched_riders)
        iters.append(candidate.iter)

    return matches, matches_count, expected_savings, iters


@njit
def get_driver_candidate(
    driver: Driver,
    riders: List,
    shortest_lengths: np.ndarray,
    w_start: float,
    w_step: float,
    c1_start: float,
    c1_step: float,
    c2_start: float,
    c2_step: float,
    num_particles: int,
) -> Candidate:
    if driver.vacancies <= 0 or driver.start_node == driver.end_node:
        return Candidate(None, None, 0.0, None, 0.0, 0)

    orig_dist = shortest_lengths[driver.start_node][driver.end_node]

    compat = List.empty_list(rider_type)
    for rider in riders:
        pickup_route = (
            shortest_lengths[driver.start_node][rider.start_node]
            + shortest_lengths[rider.end_node][driver.end_node]
        )

        # Greedy heuristic to ignore riders that are too far
        if orig_dist < pickup_route:
            continue

        compat.append(rider)

    if len(compat) == 0:
        return Candidate(None, None, 0.0, None, 0.0, 0)

    selected, savings, route, route_cost, best_iter = driver_pso(
        driver,
        compat,
        shortest_lengths,
        w_start,
        w_step,
        c1_start,
        c1_step,
        c2_start,
        c2_step,
        num_particles,
    )
    if len(selected) == 0:
        return Candidate(None, None, 0.0, None, 0.0, 0)

    return Candidate(driver, selected, savings, route, route_cost, best_iter)


@njit
def driver_pso(
    driver: Driver,
    riders: List,
    shortest_lengths: np.ndarray,
    w_start: float,
    w_step: float,
    c1_start: float,
    c1_step: float,
    c2_start: float,
    c2_step: float,
    num_particles: int,
    iterations: int = 300,
    min_improv_particles: int = 0,
    max_no_improv_iter: int = 5,
) -> tuple[List, float, np.ndarray, float, int]:
    num_riders = len(riders)
    if num_riders == 0:
        return List.empty_list(rider_type), 0.0, List.empty_list(int64), 1e18, 0

    swarm = np.empty((num_particles, num_riders), dtype=np.float64)
    velocities = np.empty((num_particles, num_riders), dtype=np.float64)
    pbest = np.empty((num_particles, num_riders), dtype=np.float64)
    pbest_vals = List.empty_list(pbest_val_type)

    for i in range(num_particles):
        # Using max driver.vacancies positive numbers to satisfy constraints
        pos = pseudo_randomize_vector(num_riders, driver.vacancies)
        swarm[i] = pos
        velocities[i] = pseudo_randomize_vector(num_riders, driver.vacancies)
        selected = decode_particle(pos)
        score = evaluate_solution(
            driver, [riders[i] for i in selected], shortest_lengths
        )
        pbest[i] = pos.copy()
        pbest_vals.append(score)

    best_val = pbest_vals[0]
    gb_index = 0
    for i in range(1, len(pbest_vals)):
        if pbest_vals[i][0] > best_val[0]:
            best_val = pbest_vals[i]
            gb_index = i
    gbest_pos = pbest[gb_index].copy()
    gbest_val = (best_val[0], best_val[1], best_val[2])
    gbest_iter = 0
    no_improv_iter = 0
    for it in range(iterations):
        no_improv_iter += 1
        improv_particles = 0
        progress = it / iterations
        w = w_start + w_step * progress
        c1 = c1_start + c1_step * progress
        c2 = c2_start + c2_step * progress
        for i in range(num_particles):
            pos = swarm[i]
            vel = velocities[i]
            for j in range(num_riders):
                r1, r2 = np.random.random(2)
                vel[j] = (
                    w * vel[j]
                    + c1 * r1 * (pbest[i][j] - pos[j])
                    + c2 * r2 * (gbest_pos[j] - pos[j])
                )
                pos[j] += vel[j]
            selected = decode_particle(pos)
            score = evaluate_solution(
                driver, [riders[i] for i in selected], shortest_lengths
            )
            if score[0] > pbest_vals[i][0]:
                pbest_vals[i] = score
                pbest[i] = pos.copy()
                improv_particles += 1
                if score[0] > gbest_val[0]:
                    gbest_val = score
                    gbest_iter = it
                    gbest_pos = pos.copy()
                    no_improv_iter = 0

        if (
            no_improv_iter >= max_no_improv_iter
            or improv_particles < min_improv_particles
        ):
            # Shortcircuit if no improvement was made in a while
            break

    best_indices = decode_particle(gbest_pos)
    rids = List.empty_list(rider_type)
    for i in best_indices:
        rids.append(riders[i])
    return rids, *gbest_val, gbest_iter


@njit
def decode_particle(position: np.ndarray, threshold: float = 0.0) -> np.ndarray:
    indices = np.where(position > threshold)[0]
    values = position[indices]
    return indices[np.argsort(values)[::-1]]


@njit
def pseudo_randomize_vector(len: int, max_positive: int) -> np.ndarray:
    if max_positive >= len:
        return np.random.uniform(-1.0, 1.0, size=len)

    result = np.random.uniform(-1.0, 0.0, size=len)
    num_positive = np.random.randint(0, max_positive + 1)
    permuted = np.random.permutation(len)
    selected = permuted[:num_positive]

    for i in selected:
        result[i] = np.random.uniform(0.0, 1.0)

    return result
