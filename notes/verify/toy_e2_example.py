#!/usr/bin/env python3
"""
Independent reproduction of the E2 toy example (E2_Example.pdf, Sections 10-15):
"Delivery Bike Operations and Battery Rebalancing" -- 2 bikes, road nodes {A,B,C},
3 orders, swap-only site A, charge-only site C, two optional battery transport services.

Built from the document rules only:
  arcs            : Section 11 (wait / move / labelled delivery / swap / terminal)
  constraints     : (34)-(47)
  objective       : (48)
Expected optimum: J = 12.5.

Usage:
  python toy_e2_example.py                 # base case + the three what-ifs
  python toy_e2_example.py --no-whatif     # base case only
"""
import sys
import itertools
import gurobipy as gp
from gurobipy import GRB

# ----------------------------------------------------------------------------
# Instance data (Section 10-11, 14)
# ----------------------------------------------------------------------------
V = ["A", "B", "C"]                 # road nodes
N = ["A", "C"]                      # facilities: A swap-only, C charge-only
K = [1, 2]                          # bikes
H = 8                               # horizon boundary
T = range(H)                        # operating slots 0..7
L = 2                               # full level
Q = range(L + 1)                    # 0,1,2
START = ("A", 0, 2)                 # both bikes start at (A,0,2)

def delta(v, w):
    """edges on the unique shortest road route (time = energy = km)."""
    if v == w:
        return 0
    if {v, w} == {"A", "B"} or {v, w} == {"A", "C"}:
        return 1
    return 2                        # B <-> C via A

# Orders: (restaurant, customer, release=ready, promise)
ORDERS = {1: dict(o="A", d="B", r=0, b=2),
          2: dict(o="A", d="B", r=0, b=2),
          3: dict(o="A", d="B", r=4, b=6)}
HP, HD = 1, 0                       # pickup / handoff durations

# Transport services: (origin, dest, depart, arrive, capacity)
SERVICES = {1: dict(o="C", d="A", l=1, u=3, U=1),
            2: dict(o="A", d="C", l=4, u=6, U=1)}

# Fixed facilities
Y = {"A": 1, "C": 1}
B0 = {"A": 0, "C": 1}               # initial full spares
K_STORE = {"A": 1, "C": 1}          # storage capacity
CHARGERS = {"A": 0, "C": 1}
M_SWAP = {"A": 1}                   # swap positions at A, sigma = 1
P_CH = 0.3                          # kW per charging step
P_SITE = {"C": 0.3}
P_GRID = 0.3

# Costs (Section 14)
KAPPA = 1.0                         # per km
ELEC = 0.05                         # pi * eps / eta per charging step
P_UNSERVED = 100.0
W_RESP = 1.0                        # w_i * Delta
V_LATE = 2.0                        # v_i * Delta
F_SERVICE = 1.0
V_REB = 0.2
RHO = 1.0
Q_RES = 0


# ----------------------------------------------------------------------------
# Arc construction (Section 11)
# ----------------------------------------------------------------------------
def build_arcs():
    """Return list of arcs. Each arc: dict(kind, src, dst, d, order, theta).
    src/dst are (v,t,q) states or 'SINK'."""
    arcs = []
    for v, t, q in itertools.product(V, range(H + 1), Q):
        # Wait
        if t < H:
            arcs.append(dict(kind="wait", src=(v, t, q), dst=(v, t + 1, q), d=0))
        # Move
        for w in V:
            if w == v:
                continue
            dl = delta(v, w)
            if q >= dl and t + dl <= H:
                arcs.append(dict(kind="move", src=(v, t, q),
                                 dst=(w, t + dl, q - dl), d=dl))
        # Delivery (one labelled arc per order), allowed from ANY v in V
        for i, od in ORDERS.items():
            dA = delta(v, od["o"])                   # travel to restaurant A
            dBC = delta(od["o"], od["d"])            # A -> B = 1
            ua = max(t + dA, od["r"]) + HP + dBC + HD          # eq (2): t+dA+2
            ga = dA + dBC                                       # eq (3)
            if t >= od["r"] and q >= ga and ua <= H:
                theta = W_RESP * (ua - od["r"]) + V_LATE * max(ua - od["b"], 0)
                arcs.append(dict(kind="deliver", src=(v, t, q),
                                 dst=(od["d"], ua, q - ga), d=dA + dBC,
                                 order=i, theta=theta))
        # Swap at A (sigma = 1), q < L, t < H  (so a swap may start at t = 7)
        if v == "A" and q < L and t < H:
            arcs.append(dict(kind="swap", src=(v, t, q), dst=(v, t + 1, L), d=0))
        # Terminal arcs: (v,H,q) -> sink if q >= delta(v,A) + q_res
        if t == H and q >= delta(v, "A") + Q_RES:
            arcs.append(dict(kind="terminal", src=(v, t, q), dst="SINK", d=0))
    return arcs


# ----------------------------------------------------------------------------
# Model
# ----------------------------------------------------------------------------
def build_model(h_fixed_zero=False, rho=RHO, k_store=None, verbose=False):
    k_store = k_store or K_STORE
    arcs = build_arcs()
    m = gp.Model("E2_toy")
    m.Params.OutputFlag = 1 if verbose else 0

    # --- independent variables -------------------------------------------
    x = {(k, a): m.addVar(vtype=GRB.BINARY, name=f"x_{k}_{a}")
         for k in K for a in range(len(arcs))}
    u = {i: m.addVar(vtype=GRB.BINARY, name=f"u_{i}") for i in ORDERS}
    n = {(j, q, t): m.addVar(vtype=GRB.INTEGER, lb=0, name=f"n_{j}_{q}_{t}")
         for j in N for q in Q for t in range(H + 1)}
    c = {(q, t): m.addVar(vtype=GRB.INTEGER, lb=0, name=f"c_C_{q}_{t}")
         for q in range(L) for t in T}
    h = {e: m.addVar(vtype=GRB.BINARY, name=f"h_{e}") for e in SERVICES}
    z = {(e, q): m.addVar(vtype=GRB.INTEGER, lb=0, name=f"z_{e}_{q}")
         for e in SERVICES for q in Q}

    def cC(q, t):   # c at C with zero conventions (c_{-1}=c_L=0)
        return c[(q, t)] if (0 <= q < L and (q, t) in c) else 0

    def cj(j, q, t):
        return cC(q, t) if j == "C" else 0

    # --- (34) one continuous path per bike -------------------------------
    nodes = set()
    for a in arcs:
        nodes.add(a["src"])
        nodes.add(a["dst"])
    out_arcs = {w: [] for w in nodes}
    in_arcs = {w: [] for w in nodes}
    for idx, a in enumerate(arcs):
        out_arcs[a["src"]].append(idx)
        in_arcs[a["dst"]].append(idx)
    for k in K:
        for w in nodes:
            rhs = 1 if w == START else (-1 if w == "SINK" else 0)
            m.addConstr(gp.quicksum(x[k, a] for a in out_arcs[w])
                        - gp.quicksum(x[k, a] for a in in_arcs[w]) == rhs,
                        name=f"flow_{k}_{w}")

    # --- (35) each order served once or unserved -------------------------
    for i in ORDERS:
        m.addConstr(gp.quicksum(x[k, idx] for k in K for idx, a in enumerate(arcs)
                                if a["kind"] == "deliver" and a["order"] == i)
                    + u[i] == 1, name=f"order_{i}")

    # --- (36) swap counts (derived linear expressions) -------------------
    s = {}
    S = {}
    for t in T:
        for q in range(L):
            s[("A", q, t)] = gp.quicksum(
                x[k, idx] for k in K for idx, a in enumerate(arcs)
                if a["kind"] == "swap" and a["src"] == ("A", t, q))
        S[("A", t)] = s[("A", 0, t)] + s[("A", 1, t)]

    def sj(j, q, t):
        return s[(j, q, t)] if j == "A" else 0

    def Sj(j, t):
        return S[(j, t)] if j == "A" else 0

    # --- (37) service activation (U_e = 1) ------------------------------
    for e, sv in SERVICES.items():
        m.addConstr(gp.quicksum(z[e, q] for q in Q) == h[e], name=f"act_{e}")
        if h_fixed_zero:
            m.addConstr(h[e] == 0, name=f"h0_{e}")

    # --- (38) departures / arrivals -------------------------------------
    def D(j, q, t):
        return gp.quicksum(z[e, q] for e, sv in SERVICES.items()
                           if sv["o"] == j and sv["l"] == t)

    def Aarr(j, q, t):
        return gp.quicksum(z[e, q] for e, sv in SERVICES.items()
                           if sv["d"] == j and sv["u"] == t)

    # --- (39)-(41) level balances ---------------------------------------
    for j in N:
        for t in T:
            m.addConstr(n[j, 0, t + 1] == n[j, 0, t] - cj(j, 0, t) + sj(j, 0, t)
                        - D(j, 0, t) + Aarr(j, 0, t + 1), name=f"bal0_{j}_{t}")
            m.addConstr(n[j, 1, t + 1] == n[j, 1, t] - cj(j, 1, t) + cj(j, 0, t)
                        + sj(j, 1, t) - D(j, 1, t) + Aarr(j, 1, t + 1),
                        name=f"bal1_{j}_{t}")
            m.addConstr(n[j, 2, t + 1] == n[j, 2, t] + cj(j, 1, t) - Sj(j, t)
                        - D(j, 2, t) + Aarr(j, 2, t + 1), name=f"bal2_{j}_{t}")

    # --- (42) joint availability ----------------------------------------
    for j in N:
        for t in T:
            m.addConstr(cj(j, 0, t) + D(j, 0, t) <= n[j, 0, t], name=f"av0_{j}_{t}")
            m.addConstr(cj(j, 1, t) + D(j, 1, t) <= n[j, 1, t], name=f"av1_{j}_{t}")
            m.addConstr(Sj(j, t) + D(j, 2, t) <= n[j, 2, t], name=f"av2_{j}_{t}")

    # --- (43) storage -----------------------------------------------------
    for j in N:
        for t in range(H + 1):
            m.addConstr(gp.quicksum(n[j, q, t] for q in Q) <= k_store[j] * Y[j],
                        name=f"store_{j}_{t}")
    # --- (44) chargers, (45) power, (46) swap positions ------------------
    for t in T:
        m.addConstr(c[0, t] + c[1, t] <= CHARGERS["C"], name=f"charger_{t}")
        m.addConstr(P_CH * (c[0, t] + c[1, t]) <= P_SITE["C"], name=f"power_{t}")
        m.addConstr(P_CH * (c[0, t] + c[1, t]) <= P_GRID, name=f"grid_{t}")
        m.addConstr(S[("A", t)] <= M_SWAP["A"], name=f"swapcap_{t}")

    # --- (47) initial stock and end target ------------------------------
    for j in N:
        for q in Q:
            m.addConstr(n[j, q, 0] == (B0[j] if q == L else 0), name=f"init_{j}_{q}")
    m.addConstr(gp.quicksum(n[j, L, H] for j in N) >= rho * sum(B0.values()),
                name="end_target")

    # --- (48) objective ---------------------------------------------------
    travel = KAPPA * gp.quicksum(a["d"] * x[k, idx] for k in K for idx, a in enumerate(arcs))
    elec = ELEC * gp.quicksum(c[q, t] for q in range(L) for t in T)
    unserved = P_UNSERVED * gp.quicksum(u.values())
    response = gp.quicksum(a["theta"] * x[k, idx] for k in K
                           for idx, a in enumerate(arcs) if a["kind"] == "deliver")
    transport = gp.quicksum(F_SERVICE * h[e] + V_REB * gp.quicksum(z[e, q] for q in Q)
                            for e in SERVICES)
    m.setObjective(travel + elec + unserved + response + transport, GRB.MINIMIZE)
    m._parts = dict(travel=travel, elec=elec, unserved=unserved,
                    response=response, transport=transport)
    m._vars = dict(x=x, u=u, n=n, c=c, h=h, z=z)
    m._arcs = arcs
    return m


def val(expr):
    return expr.getValue() if hasattr(expr, "getValue") else expr.X


def report(m, title):
    arcs, V_ = m._arcs, m._vars
    x, u, n, c, h, z = (V_[k] for k in ("x", "u", "n", "c", "h", "z"))
    print("=" * 72)
    print(title)
    print("=" * 72)
    if m.Status != GRB.OPTIMAL:
        print("Status:", m.Status)
        return None
    print(f"J = {m.ObjVal:.4f}   (" +
          ", ".join(f"{k}={val(v):.3f}" for k, v in m._parts.items()) + ")")
    print(f"#vars={m.NumVars}  #constrs={m.NumConstrs}  (#arcs per bike={len(arcs)})")
    for k in K:
        print(f"-- Bike {k} schedule")
        cur = START
        while cur != "SINK":
            nxt = [idx for idx, a in enumerate(arcs) if a["src"] == cur and x[k, idx].X > 0.5]
            assert len(nxt) == 1, (cur, nxt)
            a = arcs[nxt[0]]
            lab = a["kind"] + (f" order {a['order']} (theta={a['theta']:.0f})" if a["kind"] == "deliver" else "")
            print(f"   {a['src']} -> {a['dst']}   {lab}  d={a['d']}")
            cur = a["dst"]
    print("-- Orders: u =", {i: int(round(u[i].X)) for i in ORDERS})
    print("-- Services: h =", {e: int(round(h[e].X)) for e in SERVICES},
          " z =", {(e, q): int(round(z[e, q].X)) for e in SERVICES for q in Q if z[e, q].X > 0.5})
    print("-- Charging c_{C,q,t} =", {(q, t): int(round(c[q, t].X)) for q in range(L) for t in T if c[q, t].X > 0.5})
    print("-- Inventory n_{j,q,t}   t : A(n0,n1,n2)  C(n0,n1,n2)  m_t")
    for t in range(H + 1):
        mt = sum(int(round(z[e, q].X)) for e, sv in SERVICES.items() for q in Q
                 if sv["l"] < t < sv["u"])
        rowA = tuple(int(round(n["A", q, t].X)) for q in Q)
        rowC = tuple(int(round(n["C", q, t].X)) for q in Q)
        print(f"   {t} : A{rowA}  C{rowC}  m={mt}  total={sum(rowA)+sum(rowC)+mt}")
    return m.ObjVal


if __name__ == "__main__":
    m = build_model()
    m.optimize()
    J = report(m, "BASE CASE (document: J = 12.5)")
    print(f"\nMatches document optimum 12.5: {abs(J - 12.5) < 1e-6}")

    if "--no-whatif" not in sys.argv:
        m_a = build_model(h_fixed_zero=True); m_a.optimize()
        report(m_a, "WHAT-IF (a): no transport services (h = 0)")
        m_b = build_model(rho=0.0); m_b.optimize()
        report(m_b, "WHAT-IF (b): rho = 0 (no end target), services available")
        m_c = build_model(k_store={"A": 2, "C": 2}); m_c.optimize()
        report(m_c, "WHAT-IF (c): storage capacity K_A = K_C = 2")
