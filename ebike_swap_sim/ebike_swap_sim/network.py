"""Road network abstraction.

`RoadNetwork` is the only thing the rest of the simulator talks to, so a real
OSM/NYC LION graph can be dropped in later by implementing the same interface:
    nodes            : dict node_id -> (x, y) metres
    node_zone        : dict node_id -> zone_id
    route(u, v)      : -> Route(length_m, climb_m, n_lights, path)
    nearest_node(x,y)
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import networkx as nx


@dataclass
class Route:
    length_m: float
    climb_m: float
    n_lights: int
    path: list


class RoadNetwork:
    def route(self, u, v) -> Route:
        raise NotImplementedError

    def dist(self, u, v) -> float:
        return self.route(u, v).length_m


class GridNetwork(RoadNetwork):
    """Synthetic Manhattan-style grid with smooth random elevation and signals."""

    def __init__(self, nx_: int, ny_: int, block_m: float, light_prob: float,
                 n_zones_side: int, rng: np.random.Generator):
        self.G = nx.grid_2d_graph(nx_, ny_)
        self.nx_, self.ny_, self.block_m = nx_, ny_, block_m
        self.nodes = {n: (n[0] * block_m, n[1] * block_m) for n in self.G.nodes}
        # smooth elevation field: sum of a few random gaussian bumps (metres)
        xs = np.arange(nx_) * block_m
        ys = np.arange(ny_) * block_m
        X, Y = np.meshgrid(xs, ys, indexing="ij")
        elev = np.zeros_like(X, dtype=float)
        for _ in range(4):
            cx, cy = rng.uniform(0, nx_ * block_m), rng.uniform(0, ny_ * block_m)
            s = rng.uniform(0.2, 0.5) * nx_ * block_m
            elev += rng.uniform(5, 25) * np.exp(-((X - cx) ** 2 + (Y - cy) ** 2) / (2 * s * s))
        self.elev = {n: float(elev[n]) for n in self.G.nodes}
        self.light = {n: bool(rng.random() < light_prob) for n in self.G.nodes}
        for u, v in self.G.edges:
            self.G.edges[u, v]["length"] = block_m
        # zones: n_zones_side x n_zones_side tiles
        zx = np.minimum((np.arange(nx_) * n_zones_side) // nx_, n_zones_side - 1)
        zy = np.minimum((np.arange(ny_) * n_zones_side) // ny_, n_zones_side - 1)
        self.node_zone = {n: int(zx[n[0]] * n_zones_side + zy[n[1]]) for n in self.G.nodes}
        self.n_zones = n_zones_side ** 2
        self.zone_nodes = {z: [] for z in range(self.n_zones)}
        for n, z in self.node_zone.items():
            self.zone_nodes[z].append(n)
        self._node_list = list(self.G.nodes)
        self._xy = np.array([self.nodes[n] for n in self._node_list])

    def route(self, u, v) -> Route:
        """Shortest grid path ``u -> v`` with length, climb and signal count.

        Memoised in a per-instance dict (``self._route_cache``): a
        ``functools.lru_cache`` on the method would key on ``self`` and keep every
        GridNetwork alive for the process lifetime.  The returned quantities are the
        raw inputs of E2 (1) via ``generator.route_physics``.
        """
        cache = self.__dict__.setdefault("_route_cache", {})
        key = (u, v)
        hit = cache.get(key)
        if hit is not None:
            return hit
        if u == v:
            r = Route(0.0, 0.0, 0, [u])
        else:
            path = nx.shortest_path(self.G, u, v, weight="length")
            length = self.block_m * (len(path) - 1)
            climb = sum(max(0.0, self.elev[b] - self.elev[a]) for a, b in zip(path[:-1], path[1:]))
            lights = sum(1 for n in path[1:-1] if self.light[n])
            r = Route(length, climb, lights, path)
        cache[key] = r
        return r

    def nearest_node(self, x, y):
        i = int(np.argmin(((self._xy - np.array([x, y])) ** 2).sum(1)))
        return self._node_list[i]

    def random_node(self, rng, zone=None):
        pool = self.zone_nodes[zone] if zone is not None else self._node_list
        return pool[rng.integers(len(pool))]

    def euclid(self, u, v):
        (x1, y1), (x2, y2) = self.nodes[u], self.nodes[v]
        return abs(x1 - x2) + abs(y1 - y2)   # manhattan metric = grid distance lower bound
