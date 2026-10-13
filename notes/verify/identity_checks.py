"""
Numeric / symbolic checks of the conservation identities and worked tables in
  E2.pdf / E2_Example.pdf  (extended ILP with transfers)   and
  Battery_Swap.pdf          (first MILP, no transfers).

Sections
  1. Symbolic derivation of (23), (25) from balance (13) and random-instance
     check of (24) (sum_j N_jt + m_t = sum_j B_j) incl. one-slot services.
  2. E2 Section 8 table (A swap-only, B charge-only, L=2, H=5) vs (13)-(15),(22).
  3. E2_Example page-15 table vs (39)-(47), objective (48), and an exact ILP
     solve of the toy instance (Gurobi) to confirm J* = 12.5; no-swap variant.
  4. Battery_Swap page-7 queue table vs (9)-(12),(15)-(17).
Run:  python3 identity_checks.py
"""
import itertools, random
import sympy as sp

OK = True
def report(name, cond, detail=""):
    global OK
    OK &= bool(cond)
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f"  -- {detail}" if detail else ""))

# --------------------------------------------------------------------------
# 1. Symbolic: sum over q and q-weighted sum of balance (13)
# --------------------------------------------------------------------------
print("\n=== 1. Symbolic derivation of (23) and (25) from (13) ===")
L = 4   # any L>=1 works; use a concrete L for sympy
c = sp.symbols(f"c0:{L}")          # c_q, q=0..L-1   (c_{-1}=c_L=0 : zero conventions)
s = sp.symbols(f"s0:{L}")          # s_q, q=0..L-1   (s_L = 0 : zero convention)
D = sp.symbols(f"D0:{L+1}")        # D_q, q=0..L
A = sp.symbols(f"A0:{L+1}")        # A_{q,t+1}, q=0..L
n = sp.symbols(f"n0:{L+1}")
def cc(q):  return c[q] if 0 <= q <= L-1 else 0     # c_{j,-1,t}=c_{jLt}=0
def ss(q):  return s[q] if q <= L-1 else 0          # s_{jLt}=0
S = sum(s)                                          # S_jt = sum_{q<L} s_jqt
n_next = [n[q] - cc(q) + cc(q-1) + ss(q) - (S if q == L else 0) - D[q] + A[q] for q in range(L+1)]
lhs23 = sp.expand(sum(n_next) - sum(n))
rhs23 = sp.expand(-sum(D) + sum(A))
report("(23)  N_{t+1}-N_t = -sum_q D + sum_q A_{t+1}", sp.simplify(lhs23 - rhs23) == 0, str(lhs23))
lhs25 = sp.expand(sum(q*n_next[q] for q in range(L+1)) - sum(q*n[q] for q in range(L+1)))
rhs25 = sp.expand(sum(c) - sum((L-q)*s[q] for q in range(L)) - sum(q*D[q] for q in range(L+1)) + sum(q*A[q] for q in range(L+1)))
report("(25)  weighted: sum c - sum (L-q)s - sum qD + sum qA", sp.simplify(lhs25 - rhs25) == 0, str(lhs25))
# which conventions are needed: redo WITHOUT the c_L=0 / c_{-1}=0 / s_L=0 conventions
cm1, cL, sL = sp.symbols("c_m1 c_L s_L")
def cc2(q): return c[q] if 0 <= q <= L-1 else (cm1 if q == -1 else cL)
def ss2(q): return s[q] if q <= L-1 else sL
n_next2 = [n[q] - cc2(q) + cc2(q-1) + ss2(q) - (S if q == L else 0) - D[q] + A[q] for q in range(L+1)]
resid = sp.expand(sum(n_next2) - sum(n) - rhs23)
print("   residual of (23) if zero conventions dropped:", resid, " -> need c_{-1}=c_L=s_L=0")

# Random check of (24) by forward recursion of (13), including one-slot services
print("\n--- (24) random instances: sum_j N_jt + m_t == sum_j B_j for t=0..H ---")
def check24(seed, strict=True):
    rng = random.Random(seed)
    J, L, H = 3, 3, 7
    B = [rng.randint(0, 3) for _ in range(J)]
    # services: (o,d,l,u,z[q])  with 0<=l<u<=H ; force some one-slot (u=l+1) services
    E = []
    for _ in range(6):
        o, d = rng.sample(range(J), 2)
        l = rng.randint(0, H-1); u = rng.randint(l+1, H)
        if rng.random() < 0.4: u = l+1
        E.append((o, d, l, u, [rng.randint(0, 2) for _ in range(L+1)]))
    Dv = lambda j, q, t: sum(z[q] for (o, d, l, u, z) in E if o == j and l == t)
    Av = lambda j, q, t: sum(z[q] for (o, d, l, u, z) in E if d == j and u == t)
    n = {(j, q, 0): (B[j] if q == L else 0) for j in range(J) for q in range(L+1)}
    for t in range(H):
        for j in range(J):
            cq = [rng.randint(0, 2) for _ in range(L)]
            sq = [rng.randint(0, 2) for _ in range(L)]
            Sj = sum(sq)
            for q in range(L+1):
                cqq = cq[q] if q < L else 0
                cqm = cq[q-1] if q >= 1 else 0
                sqq = sq[q] if q < L else 0
                n[(j, q, t+1)] = n[(j, q, t)] - cqq + cqm + sqq - (Sj if q == L else 0) - Dv(j, q, t) + Av(j, q, t+1)
    ok = True
    for t in range(H+1):
        if strict:
            m = sum(sum(z) for (o, d, l, u, z) in E if l < t < u)
        else:
            m = sum(sum(z) for (o, d, l, u, z) in E if l <= t < u)   # wrong variant
        N = sum(n[(j, q, t)] for j in range(J) for q in range(L+1))
        ok &= (N + m == sum(B))
    return ok
report("(24) with strict l_e<t<u_e, 200 random instances", all(check24(sd) for sd in range(200)))
report("(24) FAILS with non-strict l_e<=t<u_e (as expected -> counterexample)", not all(check24(sd, strict=False) for sd in range(200)))

# --------------------------------------------------------------------------
# Generic forward simulator of (13) with joint-availability (14), storage (15)
# --------------------------------------------------------------------------
def simulate(sites, L, H, B, K, services, swaps, charges, Mpos=None, sigma=1, Cslots=None, verbose=True):
    """
    sites: list of site names; B,K: dict site->int; services: list of dict(o,d,l,u,z={q:cnt})
    swaps: dict (site,t)->list of return levels q (<L) of swaps starting at t
    charges: dict (site,t)->dict q->count  (c_{jqt})
    Returns dict n[(j,q,t)], m[t], and list of violations.
    """
    viol = []
    n = {(j, q, 0): (B[j] if q == L else 0) for j in sites for q in range(L+1)}
    Dv = lambda j, q, t: sum(e['z'].get(q, 0) for e in services if e['o'] == j and e['l'] == t)
    Av = lambda j, q, t: sum(e['z'].get(q, 0) for e in services if e['d'] == j and e['u'] == t)
    m = {t: sum(sum(e['z'].values()) for e in services if e['l'] < t < e['u']) for t in range(H+1)}
    for t in range(H):
        for j in sites:
            cq = {q: charges.get((j, t), {}).get(q, 0) for q in range(L)}
            sq = {q: swaps.get((j, t), []).count(q) for q in range(L)}
            Sj = sum(sq.values())
            # (14) joint availability
            for q in range(L):
                if cq[q] + Dv(j, q, t) > n[(j, q, t)]:
                    viol.append(f"(14) t={t} {j} q={q}: c+D={cq[q]+Dv(j,q,t)} > n={n[(j,q,t)]}")
            if Sj + Dv(j, L, t) > n[(j, L, t)]:
                viol.append(f"(14) t={t} {j} full: S+D={Sj+Dv(j,L,t)} > n={n[(j,L,t)]}")
            if Cslots is not None and sum(cq.values()) > Cslots.get(j, 0):
                viol.append(f"(20) t={t} {j}: charging {sum(cq.values())} > C_j={Cslots.get(j,0)}")
            for q in range(L+1):
                n[(j, q, t+1)] = (n[(j, q, t)] - (cq[q] if q < L else 0) + (cq[q-1] if q >= 1 else 0)
                                  + (sq[q] if q < L else 0) - (Sj if q == L else 0) - Dv(j, q, t) + Av(j, q, t+1))
    for t in range(H+1):
        for j in sites:
            tot = sum(n[(j, q, t)] for q in range(L+1))
            if tot > K[j]:
                viol.append(f"(15) t={t} {j}: stock {tot} > K_j={K[j]}")
            if any(n[(j, q, t)] < 0 for q in range(L+1)):
                viol.append(f"negative stock t={t} {j}")
    # (22) swap positions
    if Mpos:
        for j in sites:
            for tau in range(H):
                ongoing = sum(len(v) for (jj, t0), v in swaps.items() if jj == j and t0 <= tau < t0 + sigma)
                if ongoing > Mpos.get(j, 0):
                    viol.append(f"(22) slot {tau} {j}: {ongoing} swaps > M_j={Mpos.get(j,0)}")
    if verbose:
        for t in range(H+1):
            row = "  ".join(f"{j}:{tuple(n[(j,q,t)] for q in range(L+1))}" for j in sites)
            print(f"   t={t}  {row}  m={m[t]}  total={sum(n[(j,q,t)] for j in sites for q in range(L+1))+m[t]}")
    return n, m, viol

# --------------------------------------------------------------------------
# 2. E2 Section 8 table
# --------------------------------------------------------------------------
print("\n=== 2. E2 Section 8 table: A swap-only, B charge-only, L=2, H=5 ===")
L2, H2 = 2, 5
services2 = [dict(o='A', d='B', l=1, u=3, z={0: 1}),   # empty A->B
             dict(o='B', d='A', l=1, u=3, z={2: 1})]   # full  B->A
swaps2 = {('A', 0): [0], ('A', 3): [0]}
charges2 = {('B', 3): {0: 1}, ('B', 4): {1: 1}}
n2, m2, viol2 = simulate(['A', 'B'], L2, H2, B={'A': 1, 'B': 1}, K={'A': 1, 'B': 1},
                         services=services2, swaps=swaps2, charges=charges2, Mpos={'A': 1}, sigma=1, Cslots={'B': 1})
table2 = {0: ((0,0,1),(0,0,1),0), 1: ((1,0,0),(0,0,1),0), 2: ((0,0,0),(0,0,0),2),
          3: ((0,0,1),(1,0,0),0), 4: ((1,0,0),(0,1,0),0), 5: ((1,0,0),(0,0,1),0)}
rows_ok = all(tuple(n2[('A',q,t)] for q in range(3)) == table2[t][0] and
              tuple(n2[('B',q,t)] for q in range(3)) == table2[t][1] and m2[t] == table2[t][2] for t in range(6))
report("Section 8 table rows reproduce from (13)", rows_ok)
report("Section 8: no (14)/(15)/(20)/(22) violation", not viol2, "; ".join(viol2))
report("Section 8: sum N + m_t == 2 for all t", all(sum(n2[(j,q,t)] for j in 'AB' for q in range(3)) + m2[t] == 2 for t in range(6)))
report("Section 8: c_{B,0,3}=1 <= n_{B,0,3}", n2[('B',0,3)] >= 1, f"n_B03={n2[('B',0,3)]}")
report("Section 8: departures at t=1: n_A01>=1 and n_B21>=1", n2[('A',0,1)] >= 1 and n2[('B',2,1)] >= 1)

# --------------------------------------------------------------------------
# 3. E2_Example toy: page-15 table, objective, and exact ILP
# --------------------------------------------------------------------------
print("\n=== 3. E2_Example toy: page-15 table vs (39)-(47) ===")
services3 = [dict(o='C', d='A', l=1, u=3, z={2: 1}),   # e1: full C->A
             dict(o='A', d='C', l=4, u=6, z={0: 1})]   # e2: empty A->C
swaps3 = {('A', 3): [0]}
charges3 = {('C', 6): {0: 1}, ('C', 7): {1: 1}}
n3, m3, viol3 = simulate(['A', 'C'], 2, 8, B={'A': 0, 'C': 1}, K={'A': 1, 'C': 1},
                         services=services3, swaps=swaps3, charges=charges3, Mpos={'A': 1}, sigma=1, Cslots={'C': 1})
table3 = {0: ((0,0,0),(0,0,1),0), 1: ((0,0,0),(0,0,1),0), 2: ((0,0,0),(0,0,0),1), 3: ((0,0,1),(0,0,0),0),
          4: ((1,0,0),(0,0,0),0), 5: ((0,0,0),(0,0,0),1), 6: ((0,0,0),(1,0,0),0), 7: ((0,0,0),(0,1,0),0),
          8: ((0,0,0),(0,0,1),0)}
rows_ok3 = all(tuple(n3[('A',q,t)] for q in range(3)) == table3[t][0] and
               tuple(n3[('C',q,t)] for q in range(3)) == table3[t][1] and m3[t] == table3[t][2] for t in range(9))
report("page-15 table rows reproduce from (39)-(41)", rows_ok3)
report("page-15: no (42)/(43)/(44)/(46) violation", not viol3, "; ".join(viol3))
report("page-15: end target n_A28+n_C28>=1 (47)", n3[('A',2,8)] + n3[('C',2,8)] >= 1)
report("page-15: sum N + m_t == 1 for all t", all(sum(n3[(j,q,t)] for j in 'AC' for q in range(3)) + m3[t] == 1 for t in range(9)))

# objective (48) from the listed actions
delta = {('A','B'):1, ('B','A'):1, ('A','C'):1, ('C','A'):1, ('B','C'):2, ('C','B'):2, ('A','A'):0, ('B','B'):0, ('C','C'):0}
orders = {1: dict(r=0, b=2), 2: dict(r=0, b=2), 3: dict(r=4, b=6)}
def theta(i, ua): return (ua - orders[i]['r']) + 2*max(ua - orders[i]['b'], 0)
# listed arcs: (bike, kind, v_start, t_start, q_start, ...)
travel = (delta[('A','A')]+1) + (delta[('B','A')]) + (delta[('A','A')]+1) + (delta[('A','A')]+1)   # deliver1, move B->A, deliver3, deliver2
resp = theta(1, 2) + theta(3, 6) + theta(2, 2)
elec = 0.05 * 2
transport = 2 * (1 + 0.2)
J = travel + elec + 0 + resp + transport
report("objective (48) from listed actions == 12.5", abs(J - 12.5) < 1e-9, f"travel={travel} elec={elec} resp={resp} transport={transport} J={J}")
report("theta_ia >= 2 for every candidate delivery arc (u_a - r_i = delta(v,A)+2 >= 2)",
       all(theta(i, t + delta[(v,'A')] + 2) >= 2 for i in orders for v in 'ABC' for t in range(orders[i]['r'], 9) if t + delta[(v,'A')] + 2 <= 8))
report("bike 2 at (B,2,1): delivery arc needs q>=delta(B,A)+1=2 -> none", 1 < delta[('B','A')] + 1)

# ---- exact ILP of the toy instance (E2_Example (34)-(48)) ----
print("\n--- exact ILP of toy instance (Gurobi) ---")
def solve_toy(allow_swap=True, allow_services=True, force_bike2_order3=False, verbose=False):
    import gurobipy as gp
    from gurobipy import GRB
    H, Lv = 8, 2
    V = ['A', 'B', 'C']
    mdl = gp.Model("toy"); mdl.Params.OutputFlag = 0
    arcs = {}  # per bike: list of (name, src, dst, d, cost_extra, order, swap_q)
    for k in (1, 2):
        lst = []
        for v in V:
            for t in range(H+1):
                for q in range(Lv+1):
                    src = (v, t, q)
                    if t < H:
                        lst.append(("wait", src, (v, t+1, q), 0, 0, None, None))
                        for w in V:
                            if w != v and q >= delta[(v,w)] and t + delta[(v,w)] <= H:
                                lst.append(("move", src, (w, t+delta[(v,w)], q-delta[(v,w)]), delta[(v,w)], 0, None, None))
                        for i in orders:
                            ua = t + delta[(v,'A')] + 2
                            if t >= orders[i]['r'] and q >= delta[(v,'A')] + 1 and ua <= H:
                                lst.append((f"deliver{i}", src, ('B', ua, q-delta[(v,'A')]-1), delta[(v,'A')]+1, theta(i, ua), i, None))
                        if allow_swap and v == 'A' and q < Lv:
                            lst.append(("swap", src, ('A', t+1, Lv), 0, 0, None, q))
                    else:
                        if q >= delta[(v,'A')]:
                            lst.append(("term", src, ('sink',), 0, 0, None, None))
        arcs[k] = lst
    x = {(k, idx): mdl.addVar(vtype=GRB.BINARY, name=f"x{k}_{idx}") for k in arcs for idx in range(len(arcs[k]))}
    u = {i: mdl.addVar(vtype=GRB.BINARY, name=f"u{i}") for i in orders}
    n = {(j, q, t): mdl.addVar(vtype=GRB.INTEGER, lb=0, name=f"n{j}{q}{t}") for j in 'AC' for q in range(Lv+1) for t in range(H+1)}
    cC = {(q, t): mdl.addVar(vtype=GRB.INTEGER, lb=0, name=f"c{q}{t}") for q in range(Lv) for t in range(H)}
    h = {e: mdl.addVar(vtype=GRB.BINARY, name=f"h{e}") for e in (1, 2)}
    z = {(e, q): mdl.addVar(vtype=GRB.INTEGER, lb=0, name=f"z{e}{q}") for e in (1, 2) for q in range(Lv+1)}
    # (34) flow
    for k in arcs:
        nodes = set()
        for a in arcs[k]: nodes.add(a[1]); nodes.add(a[2])
        for w in nodes:
            out = gp.quicksum(x[(k, idx)] for idx, a in enumerate(arcs[k]) if a[1] == w)
            inn = gp.quicksum(x[(k, idx)] for idx, a in enumerate(arcs[k]) if a[2] == w)
            rhs = 1 if w == ('A', 0, 2) else (-1 if w == ('sink',) else 0)
            mdl.addConstr(out - inn == rhs)
    # (35)
    for i in orders:
        mdl.addConstr(gp.quicksum(x[(k, idx)] for k in arcs for idx, a in enumerate(arcs[k]) if a[5] == i) + u[i] == 1)
    if force_bike2_order3:
        mdl.addConstr(gp.quicksum(x[(2, idx)] for idx, a in enumerate(arcs[2]) if a[5] == 3) == 1)
    # (36) swap counts
    sA = {(q, t): gp.quicksum(x[(k, idx)] for k in arcs for idx, a in enumerate(arcs[k]) if a[0] == "swap" and a[1][1] == t and a[6] == q) for q in range(Lv) for t in range(H)}
    SA = {t: sA[(0, t)] + sA[(1, t)] for t in range(H)}
    # (37)
    for e in (1, 2):
        mdl.addConstr(gp.quicksum(z[(e, q)] for q in range(Lv+1)) == h[e])
        if not allow_services: mdl.addConstr(h[e] == 0)
    # (38)
    Dv = lambda j, q, t: (z[(1, q)] if (j == 'C' and t == 1) else 0) + (z[(2, q)] if (j == 'A' and t == 4) else 0)
    Av = lambda j, q, t: (z[(1, q)] if (j == 'A' and t == 3) else 0) + (z[(2, q)] if (j == 'C' and t == 6) else 0)
    # (39)-(41)
    for j in 'AC':
        for t in range(H):
            c0 = cC[(0, t)] if j == 'C' else 0
            c1 = cC[(1, t)] if j == 'C' else 0
            s0 = sA[(0, t)] if j == 'A' else 0
            s1 = sA[(1, t)] if j == 'A' else 0
            Sj = SA[t] if j == 'A' else 0
            mdl.addConstr(n[(j, 0, t+1)] == n[(j, 0, t)] - c0 + s0 - Dv(j, 0, t) + Av(j, 0, t+1))
            mdl.addConstr(n[(j, 1, t+1)] == n[(j, 1, t)] - c1 + c0 + s1 - Dv(j, 1, t) + Av(j, 1, t+1))
            mdl.addConstr(n[(j, 2, t+1)] == n[(j, 2, t)] + c1 - Sj - Dv(j, 2, t) + Av(j, 2, t+1))
            # (42)
            mdl.addConstr(c0 + Dv(j, 0, t) <= n[(j, 0, t)])
            mdl.addConstr(c1 + Dv(j, 1, t) <= n[(j, 1, t)])
            mdl.addConstr(Sj + Dv(j, 2, t) <= n[(j, 2, t)])
        for t in range(H+1):  # (43)
            mdl.addConstr(n[(j, 0, t)] + n[(j, 1, t)] + n[(j, 2, t)] <= 1)
    for t in range(H):
        mdl.addConstr(cC[(0, t)] + cC[(1, t)] <= 1)          # (44)
        mdl.addConstr(0.3*(cC[(0, t)] + cC[(1, t)]) <= 0.3)  # (45)
        mdl.addConstr(SA[t] <= 1)                             # (46)
    # (47)
    for q in range(3):
        mdl.addConstr(n[('A', q, 0)] == 0)
        mdl.addConstr(n[('C', q, 0)] == (1 if q == 2 else 0))
    mdl.addConstr(n[('A', 2, 8)] + n[('C', 2, 8)] >= 1)
    # (48)
    obj = (gp.quicksum(a[3]*x[(k, idx)] for k in arcs for idx, a in enumerate(arcs[k]))
           + 0.05*gp.quicksum(cC.values()) + 100*gp.quicksum(u.values())
           + gp.quicksum(a[4]*x[(k, idx)] for k in arcs for idx, a in enumerate(arcs[k]))
           + gp.quicksum(h[e] + 0.2*gp.quicksum(z[(e, q)] for q in range(Lv+1)) for e in (1, 2)))
    mdl.setObjective(obj, GRB.MINIMIZE)
    mdl.optimize()
    if mdl.Status != GRB.OPTIMAL:
        return None, None
    sol = []
    for k in arcs:
        for idx, a in enumerate(arcs[k]):
            if x[(k, idx)].X > 0.5 and a[0] != "wait":
                sol.append((k, a[0], a[1], a[2]))
    return mdl.ObjVal, sol

Jopt, sol = solve_toy()
report("ILP optimum of toy instance == 12.5", Jopt is not None and abs(Jopt - 12.5) < 1e-6, f"J*={Jopt}")
for s_ in sorted(sol): print("   ", s_)
# count optimal solutions with the two bikes swapped: solve forcing bike 2 to do order 3
J2, sol2 = solve_toy(force_bike2_order3=True)
report("symmetric plan (bike 2 returns, swaps, does order 3) also costs 12.5", J2 is not None and abs(J2 - 12.5) < 1e-6, f"J={J2}")
Jns, solns = solve_toy(allow_swap=False)
report("no-swap variant: best cost (one order must be unserved)", Jns is not None and Jns > 100, f"J={Jns}")
Jnsv, _ = solve_toy(allow_services=False)
report("no-transfer variant (h=0): best cost", Jnsv is not None and Jnsv > 100, f"J={Jnsv}")

# --------------------------------------------------------------------------
# 4. Battery_Swap page-7 queue table (no transfers)
# --------------------------------------------------------------------------
print("\n=== 4. Battery_Swap page-7 queue table: one station, L=2, B=C=M=1, sigma=1 ===")
n4, m4, viol4 = simulate(['J'], 2, 4, B={'J': 1}, K={'J': 1}, services=[],
                         swaps={('J', 0): [0], ('J', 3): [0]}, charges={('J', 1): {0: 1}, ('J', 2): {1: 1}},
                         Mpos={'J': 1}, sigma=1, Cslots={'J': 1})
table4 = {0: (0,0,1), 1: (1,0,0), 2: (0,1,0), 3: (0,0,1), 4: (1,0,0)}
report("page-7 table rows reproduce from (9)-(11)", all(tuple(n4[('J',q,t)] for q in range(3)) == table4[t] for t in range(5)))
report("page-7: no (12)/(15)/(16) violation", not viol4, "; ".join(viol4))
report("page-7: (17) sum_q n_qt == B == 1 for all t", all(sum(n4[('J',q,t)] for q in range(3)) == 1 for t in range(5)))
# can the second swap start earlier than t=3?  need n_{2,t} >= 1 for t in {1,2}
report("page-7: next swap cannot start before t=3 (n_2t = 0 for t=1,2)", n4[('J',2,1)] == 0 and n4[('J',2,2)] == 0)
# charging the returned battery in slot 0 would violate (12): c_{0,0} <= n_{0,0} = 0
report("page-7: charging the t=0 return in slot 0 violates (12) (n_00=0)", n4[('J',0,0)] == 0)

print("\nALL CHECKS PASSED" if OK else "\nSOME CHECKS FAILED")
