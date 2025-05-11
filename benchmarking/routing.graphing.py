import matplotlib.pyplot as plt
import numpy as np

x = [2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22]

labels = [
    "Brute-force",
    "Dijkstra's-like",
    "Branch and bound, nearest neighbor",
    "Branch and bound, single link",
    "Held-Karp precedence constraints",
]

data = [
    [2.05e-06, 3.12e-06, 1.04e-05, 1.71e-04, 7.67e-03, 6.02e-01, 7.11e01] + [None] * 4,
    [1.49e-06, 2.52e-06, 1.14e-05, 1.21e-04, 2.61e-03, 9.59e-02, 4.72e00] + [None] * 4,
    [1.77e-06, 4.34e-06, 3.59e-05, 5.17e-04, 1.27e-02, 4.82e-01, 2.04e01] + [None] * 4,
    [1.59e-06, 3.63e-06, 3.47e-05, 5.00e-04, 1.23e-02, 4.76e-01, 2.05e01] + [None] * 4,
    [
        2.55e-06,
        3.32e-06,
        8.01e-06,
        3.56e-05,
        2.02e-04,
        1.09e-03,
        5.30e-03,
        2.66e-02,
        1.39e-01,
        7.53e-01,
        3.54e00,
    ],
]


plt.figure(figsize=(10, 6))
for i, label in enumerate(labels):
    y = data[i]
    y = [np.nan if v is None else v for v in y]
    plt.plot(x, y, marker="o", label=label)

plt.yscale("log")
plt.xticks(np.arange(2, 24, 2))
plt.xlabel("Node count")
plt.ylabel("Time (s, logarithmic scale)")

plt.grid(True, axis="x", linestyle="--", alpha=0.3)
plt.grid(True, axis="y", linestyle="--", alpha=0.3)
plt.legend()
plt.tight_layout()
plt.show()
