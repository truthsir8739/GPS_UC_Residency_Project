from collections import defaultdict
import heapq

class Graph:
    def __init__(self):
        self.adj_list = defaultdict(list)

    def add_edge(self, u, v, weight, crowd='low', tip='', blind_spot=False):
        if weight < 0:
            raise ValueError("Negative weights are not supported in Dijkstra's algorithm.")
        self.adj_list[u].append((v, weight, crowd, tip, blind_spot))

    def dijkstra(self, start, end, learner_mode=False):
        if start not in self.adj_list and start != end:
            return [], [], []
        if start == end:
            return [start], [], []

        nodes = set(self.adj_list.keys()) | {end}
        distances = {node: float('inf') for node in nodes}
        distances[start] = 0
        previous = {node: None for node in nodes}
        pq = [(0, start)]

        while pq:
            dist_u, u = heapq.heappop(pq)
            if dist_u > distances[u]:
                continue
            if u == end:
                break
            for v, w, crowd, tip, blind_spot in self.adj_list.get(u, []):
                if learner_mode:
                    crowd_bias = {'low': 0, 'medium': w * 0.2, 'high': w * 0.5}.get(crowd, 0)
                    blind_spot_penalty = w * 2 if blind_spot else 0
                    bias = crowd_bias + blind_spot_penalty
                else:
                    bias = 0
                
                new_dist = dist_u + w + bias
                if new_dist < distances.get(v, float('inf')):
                    distances[v] = new_dist
                    previous[v] = u
                    heapq.heappush(pq, (new_dist, v))

        path = []
        cur = end
        while cur is not None:
            path.append(cur)
            cur = previous.get(cur)
        path.reverse()

        if not path or path[0] != start:
            return [], [], []

        tips = []
        blind_alerts = []
        for i in range(1, len(path)):
            u, v = path[i-1], path[i]
            for neigh, _, crowd, t, b in self.adj_list.get(u, []):
                if neigh == v:
                    if learner_mode and t:
                        tips.append(t)
                    if b:
                        blind_alerts.append(f"Blind spot at {u} to {v}")
                    break

        return path, tips, blind_alerts
