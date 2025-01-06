import random
import time

from routing import branch_bound_pc, brute_force_routing, dijkstra_routing, held_karp_pc
from state import SimulationState

state = SimulationState("Vilnius, Lithuania")

iterations = 1000
intermediary_nodes = 10

for elem_count in range(0, intermediary_nodes + 1, 2):
    tt1, tt2, tt3, tt4, tt5 = 0, 0, 0, 0, 0
    tw1, tw2, tw3, tw4, tw5 = 0, 0, 0, 0, 0
    for i in range(iterations):
        sn, en = random.choices(list(state.nodes.keys()), k = 2)
        lst = random.choices(list(state.nodes.keys()), k = elem_count)
        lst = [(lst[i], lst[i+1]) for i in range(0, elem_count, 2)]

        t0 = time.time()
        _, weight1 = held_karp_pc(sn, en, lst, state)
        t1 = time.time()
        _, weight2 = dijkstra_routing(sn, en, lst, state)
        t2 = time.time()
        _, weight3 = brute_force_routing(sn, en, lst, state)
        t3 = time.time()
        _, weight4 = branch_bound_pc(sn, en, lst, state, 'single-link')
        t4 = time.time()
        _, weight5 = branch_bound_pc(sn, en, lst, state, 'nearest-neighbor')
        t5 = time.time()

        tt1 += (t1 - t0); tw1 += weight1
        tt2 += (t2 - t1); tw2 += weight2
        tt3 += (t3 - t2); tw3 += weight3
        tt4 += (t4 - t3); tw4 += weight4
        tt5 += (t5 - t4); tw5 += weight5

    tt1 /= iterations; tw1 /= iterations
    tt2 /= iterations; tw2 /= iterations
    tt3 /= iterations; tw3 /= iterations
    tt4 /= iterations; tw4 /= iterations
    tt5 /= iterations; tw5 /= iterations

    print(f"{elem_count + 2}, avg 1/{iterations}:")
    print(f"{tt1:9.2e} {tt2:9.2e} {tt3:9.2e} {tt4:9.2e} {tt5:9.2e}")
    print(f"{tw1:9.2f} {tw2:9.2f} {tw3:9.2f} {tw4:9.2f} {tw5:9.2f}")