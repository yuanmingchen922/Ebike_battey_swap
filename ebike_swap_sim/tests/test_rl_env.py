"""Tests of the A7 RL comparator (``ebike_swap_sim.rl_env``, ``experiments/a7_rl.py``):
gymnasium step/reset contract, reward = negative E2 cost increment (evaluate.cost, (26)-(32))
on the deterministic toy instance, parity of the in-environment station layer with
``baseline.run_baseline``, and a 2k-step PPO smoke run."""
from __future__ import annotations

import math

import numpy as np
import pytest

gym = pytest.importorskip("gymnasium")

from ebike_swap_sim import baseline as bl  # noqa: E402
from ebike_swap_sim import build_arcs, toy_instance  # noqa: E402
from ebike_swap_sim.evaluate import check, cost  # noqa: E402
from ebike_swap_sim.rl_env import (EnvConfig, StationEnv, adjusted_cost,  # noqa: E402
                                   end_state_adjustment, resolve_rider_variant)

REPORT_ONLY = {"(9)", "(17)", "(18)"}


@pytest.fixture(scope="module")
def toy():
    inst = toy_instance()
    return inst, build_arcs(inst)


def _env(toy, **cfg):
    return StationEnv(instances=[toy], config=EnvConfig(**cfg))


def _rollout(env, policy):
    obs, info = env.reset(options={"seed": 0})
    total, steps, done = 0.0, 0, False
    while not done:
        obs, r, done, trunc, info = env.step(policy(env))
        total += r
        steps += 1
        assert not trunc
    return total, steps, info


# ---------------------------------------------------------------- contract
def test_spaces_and_reset_step_contract(toy):
    inst, _ = toy
    env = _env(toy)
    # toy: one charge hub C (C_j = 1, P_j / p_ch = 1) and two services with U_e = 1
    assert isinstance(env.action_space, gym.spaces.MultiDiscrete)
    assert list(env.action_space.nvec) == [2, 2, 2]
    obs, info = env.reset(seed=3)
    assert env.observation_space.contains(obs)
    assert obs.dtype == np.float32 and obs.shape == env.observation_space.shape
    assert info["t"] == 0 and "phi0" in info
    env.action_space.seed(0)
    for t in range(inst.H):
        obs, r, term, trunc, info = env.step(env.action_space.sample())
        assert env.observation_space.contains(obs)
        assert isinstance(r, float) and math.isfinite(r)
        assert trunc is False
        assert term == (t == inst.H - 1)
        assert info["t"] == t + 1
    for key in ("schedule", "cost", "episode_cost", "end_adj", "adjusted_total", "flags"):
        assert key in info
    # a second reset starts a fresh episode on the same instance
    obs2, info2 = env.reset(options={"seed": 0})
    assert info2["t"] == 0 and env.run.t == 0


def test_rider_variant_aliases():
    assert resolve_rider_variant("r2") == "default"
    assert resolve_rider_variant("round1") == "round1"
    with pytest.raises(KeyError):
        resolve_rider_variant("no_such_variant")


# ---------------------------------------------------------------- reward
@pytest.mark.parametrize("scale", [1.0, 0.1])
def test_reward_equals_cost_difference_toy(toy, scale):
    inst, lib = toy
    env = _env(toy, reward_scale=scale)
    env.action_space.seed(7)
    obs, info = env.reset(options={"seed": 0})
    phi_prev = cost(inst, lib, env.partial_schedule())["total"]
    assert phi_prev == pytest.approx(info["phi0"])
    total = 0.0
    done = False
    while not done:
        obs, r, done, _, info = env.step(env.action_space.sample())
        if not done:
            phi = cost(inst, lib, env.partial_schedule())["total"]
        else:
            sched = info["schedule"]
            adj = adjusted_cost(inst, lib, sched)
            phi = cost(inst, lib, sched)["total"] + adj["end_adj"]
            assert info["episode_cost"] == pytest.approx(cost(inst, lib, sched)["total"])
        assert r == pytest.approx(-(phi - phi_prev) * scale, abs=1e-9)
        phi_prev = phi
        total += r
    # telescoping: return = -(J + adj - Phi_0) * scale
    assert total == pytest.approx(-(info["episode_cost"] + info["end_adj"] - info["phi0"]) * scale)


def test_end_state_adjustment_toy_value(toy):
    inst, _ = toy
    # one empty battery at the station (L = 2 steps) and no fleet deficit: pi * eps/eta * 2
    adj = end_state_adjustment(inst, {"A": [0, 0, 0], "C": [1, 0, 0]}, {b.id: b.q0 for b in inst.bikes})
    assert adj["station_steps"] == 2 and adj["fleet_steps"] == 0
    assert adj["total"] == pytest.approx(inst.price("C", inst.H - 1) * inst.disc.kwh_per_step * 2)


# ---------------------------------------------------------------- parity / feasibility
@pytest.mark.parametrize("rule,expected", [("NONE", 108.0), ("REORDER_POINT", 14.5)])
def test_replay_matches_baseline_toy(toy, rule, expected):
    inst, lib = toy
    env = _env(toy, station_policy="baseline", rider_overrides={"transfer_rule": rule})
    _, _, info = _rollout(env, lambda e: e.action_space.sample())
    sched, _ = bl.run_baseline(inst, lib, {"transfer_rule": rule})
    assert info["episode_cost"] == pytest.approx(cost(inst, lib, sched)["total"])
    assert info["episode_cost"] == pytest.approx(expected)


def test_agent_actions_toy(toy):
    inst, lib = toy
    env = _env(toy)
    _, steps, info_none = _rollout(env, lambda e: np.zeros(3, dtype=np.int64))
    assert steps == inst.H
    assert info_none["episode_cost"] == pytest.approx(108.0)      # no transfers -> baseline NONE
    _, _, info_all = _rollout(env, lambda e: np.ones(3, dtype=np.int64))
    assert info_all["episode_cost"] == pytest.approx(14.5)        # ship + charge -> REORDER_POINT value
    assert info_all["episode_cost"] >= 12.5 - 1e-9                # never below the ILP optimum J* = 12.5


def test_random_actions_feasible_toy(toy):
    inst, lib = toy
    env = _env(toy)
    rng = np.random.default_rng(0)
    for _ in range(10):
        _, _, info = _rollout(env, lambda e: rng.integers(0, e.action_space.nvec))
        rep = check(inst, lib, info["schedule"])
        assert set(rep["families"]) <= REPORT_ONLY, rep["families"]
        assert rep["identity_24_ok"]
        assert info["episode_cost"] >= 12.5 - 1e-9


def test_demand_aware_heuristic_matches_baseline_small():
    common = pytest.importorskip("experiments.common")
    inst = common.make_instance("small", 0)
    lib, _ = common.build_library(inst, common.pruning_for(inst))
    assert not inst.services
    env = StationEnv(instances=[(inst, lib)], config=EnvConfig())
    _, _, info = _rollout(env, lambda e: e.heuristic_action("demand_aware"))
    sched, _ = bl.run_baseline(inst, lib)
    assert info["episode_cost"] == pytest.approx(cost(inst, lib, sched)["total"])
    assert info["schedule"].c == sched.c


# ---------------------------------------------------------------- training smoke
def test_ppo_smoke_training_2k_steps(toy, tmp_path):
    pytest.importorskip("stable_baselines3")
    a7 = pytest.importorskip("experiments.a7_rl")
    rec = a7.train(family="toy", train_seeds=[0], timesteps=2048, seed=0,
                   factory=lambda s: toy, out=str(tmp_path),
                   ppo={"n_steps": 256, "batch_size": 64, "n_epochs": 2})
    assert (tmp_path / "ppo_station.zip").exists()
    assert rec["timesteps"] == 2048
    from stable_baselines3 import PPO
    model = PPO.load(str(tmp_path / "ppo_station.zip"), device="cpu")
    env = _env(toy)
    ep = a7.run_env_episode(env, 0, "rl", model)
    assert ep["E2_total"] >= 12.5 - 1e-9
    assert set(check(toy[0], toy[1], ep["schedule"])["families"]) <= REPORT_ONLY
