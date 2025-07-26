from graph import Graph
import time
import matplotlib.pyplot as plt
import tracemalloc

# Updated to ensure all nodes are initialized
def create_graph_with_nodes_fixed(node_count):
    g = Graph()
    for i in range(node_count):
        g.adj_list[f'N{i}']  # Force node initialization
    for i in range(node_count - 1):
        g.add_edge(f'N{i}', f'N{i+1}', 1, crowd='low')
    return g

# Re-run the benchmark
node_sizes = [10, 100, 500, 1000, 2000]
times = []
memories = []

for size in node_sizes:
    g = create_graph_with_nodes_fixed(size)
    start, end = 'N0', f'N{size - 1}'

    tracemalloc.start()
    t0 = time.time()
    g.dijkstra(start, end, learner_mode=True)
    t1 = time.time()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    times.append(t1 - t0)
    memories.append(peak / 1024)  # Convert to KB

# Plot performance results
import matplotlib.pyplot as plt

plt.figure(figsize=(10, 5))
plt.plot(node_sizes, times, marker='o', label="Execution Time (s)")
plt.xlabel("Number of Nodes")
plt.ylabel("Time (seconds)")
plt.title("Dijkstra Learner Mode Runtime vs Graph Size")
plt.grid(True)
plt.legend()
plt.show()

plt.figure(figsize=(10, 5))
plt.plot(node_sizes, memories, marker='s', label="Peak Memory (KB)", color="orange")
plt.xlabel("Number of Nodes")
plt.ylabel("Memory (KB)")
plt.title("Memory Usage vs Graph Size")
plt.grid(True)
plt.legend()
plt.show()
