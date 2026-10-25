"""Tests of ``ebike_swap_sim.costs`` (DECISIONS.md R2.1): the documented
coefficients of every cost variant, the window scaling of F / F_hub / bB / bC,
the toy numbers of round 1 and the generator-compatible key layout."""
from __future__ import annotations

import json
import os

import pytest

from ebike_swap_sim import costs as cm
from ebike_swap_sim.generator import DEFAULT_COSTS, DEFAULT_DEMAND_SPEC, DEFAULT_SERVICES_SPEC


def _json():
    with open(cm.DEFAULT_CALIBRATION_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


def test_calibration_file_and_variant_listing():
    assert os.path.exists(cm.DEFAULT_CALIBRATION_PATH)
    names = list(cm.cost_variants())
    assert names == ["toy", "usd_A", "usd_sunk", "usd_B", "usd_low", "usd_high", "usd_r6"]
    assert all(isinstance(doc, str) and doc for doc in cm.cost_variants().values())
    with pytest.raises(KeyError):
        cm.load_cost_calibration(variant="usd_Z")
    with pytest.raises(ValueError):
        cm.load_cost_calibration(variant="usd_A", window_h=0.0)


def test_key_layout_matches_generator_defaults():
    for name in cm.cost_variants():
        cal = cm.load_cost_calibration(variant=name, window_h=4.0)
        assert set(cal["costs"]) == set(DEFAULT_COSTS) - {"q_res", "rho"}
        assert set(cal["demand_spec"]) == {"P", "w", "v"} <= set(DEFAULT_DEMAND_SPEC)
        assert set(cal["services_spec"]) == {"f", "vreb"} <= set(DEFAULT_SERVICES_SPEC)
        assert cal["variant"] == name and cal["window_h"] == 4.0
        flat = cm.flat_coefficients(cal)
        for key in ("kappa", "pi", "pi_peak", "F", "F_hub", "bB", "bC", "Fhat", "bhat", "chat",
                    "P", "w", "v", "f", "vreb", "variant", "window_h", "source"):
            assert key in flat


def test_toy_variant_is_round_one():
    cal = cm.load_cost_calibration(variant="toy", window_h=4.0)
    assert cal["costs"] == {"kappa": 1.0, "pi": 2.0, "pi_peak": None, "F": 20.0, "F_hub": 40.0,
                            "bB": 3.0, "bC": 2.0, "Fhat": 5000.0, "bhat": 500.0, "chat": 300.0}
    assert cal["demand_spec"] == {"P": 100.0, "w": 12.0, "v": 24.0}
    assert cal["services_spec"] == {"f": 5.0, "vreb": 0.2}
    # equals the generator defaults (minus q_res / rho) and does not scale with the window
    assert cal["costs"] == {k: v for k, v in DEFAULT_COSTS.items() if k not in ("q_res", "rho")}
    assert cm.load_cost_calibration(variant="toy", window_h=8.0)["costs"] == cal["costs"]
    assert cal["window_scale"] == 1.0 and cal["window_scaled_keys"] == []


def test_usd_A_documented_numbers():
    cal = cm.load_cost_calibration(variant="usd_A", window_h=4.0)
    c, d, s = cal["costs"], cal["demand_spec"], cal["services_spec"]
    # R2.1: kappa 0.50, w 40, v 80, P 30, pi 0.32, f_e 20, v_reb 1.0, F 12.0 / F_hub 29.2,
    # bB 0.332, bC 0.082 per 4 h; budget Fhat 50,000, bhat 450, chat 400
    assert c["kappa"] == 0.5 and c["pi"] == pytest.approx(0.32) and c["pi_peak"] is None
    assert c["F"] == pytest.approx(12.03) and c["F"] == pytest.approx(12.0, abs=0.05)
    assert c["F_hub"] == pytest.approx(29.19) and c["F_hub"] == pytest.approx(29.2, abs=0.05)
    assert c["bB"] == pytest.approx(0.332) and c["bC"] == pytest.approx(0.082)
    assert (c["Fhat"], c["bhat"], c["chat"]) == (50000.0, 450.0, 400.0)
    assert (d["P"], d["w"], d["v"]) == (30.0, 40.0, 80.0)
    assert (s["f"], s["vreb"]) == (20.0, 1.0)
    # it is the JSON 'base' block verbatim at the reference window
    block = _json()["generator_overrides"]["base"]
    assert c == {k: (float(v) if v is not None else None) for k, v in block["costs"].items()}


def test_usd_sunk_default_and_usd_B():
    a = cm.load_cost_calibration(variant="usd_A", window_h=4.0)
    sunk = cm.load_cost_calibration(variant="usd_sunk", window_h=4.0)
    # R2.1: usd_sunk = usd_A with kappa 0.12, w 18, v 36; everything else as usd_A
    assert sunk["costs"]["kappa"] == 0.12
    assert (sunk["demand_spec"]["w"], sunk["demand_spec"]["v"]) == (18.0, 36.0)
    assert sunk["demand_spec"]["P"] == a["demand_spec"]["P"] == 30.0
    assert {k: v for k, v in sunk["costs"].items() if k != "kappa"} == \
        {k: v for k, v in a["costs"].items() if k != "kappa"}
    assert sunk["services_spec"] == a["services_spec"]
    assert "DEFAULT" in cm.cost_variants()["usd_sunk"]
    b = cm.load_cost_calibration(variant="usd_B", window_h=4.0)
    assert b["costs"]["kappa"] == 1.6 and (b["demand_spec"]["w"], b["demand_spec"]["v"]) == (18.0, 36.0)
    assert {k: v for k, v in b["costs"].items() if k != "kappa"} == \
        {k: v for k, v in a["costs"].items() if k != "kappa"}
    # cross-check with the JSON option_B block
    opt_b = _json()["variants"]["option_B_clean_split"]
    assert b["costs"]["kappa"] == opt_b["costs"]["kappa"]
    assert b["demand_spec"]["w"] == opt_b["demand_spec"]["w"]
    assert b["demand_spec"]["v"] == opt_b["demand_spec"]["v"]


def test_low_high_envelopes():
    lo = cm.load_cost_calibration(variant="usd_low", window_h=4.0)
    hi = cm.load_cost_calibration(variant="usd_high", window_h=4.0)
    base = cm.load_cost_calibration(variant="usd_A", window_h=4.0)
    assert lo["costs"]["kappa"] == 0.12 and hi["costs"]["kappa"] == 1.6
    assert (lo["demand_spec"]["P"], hi["demand_spec"]["P"]) == (15.0, 60.0)
    assert (lo["demand_spec"]["w"], hi["demand_spec"]["w"]) == (22.0, 60.0)
    for key in ("kappa", "pi", "F", "F_hub", "bB", "bC", "Fhat", "bhat", "chat"):
        assert lo["costs"][key] <= base["costs"][key] <= hi["costs"][key]
    for key in ("P", "w", "v"):
        assert lo["demand_spec"][key] <= base["demand_spec"][key] <= hi["demand_spec"][key]
    for key in ("f", "vreb"):
        assert lo["services_spec"][key] <= base["services_spec"][key] <= hi["services_spec"][key]


@pytest.mark.parametrize("variant", ["usd_A", "usd_sunk", "usd_B", "usd_low", "usd_high"])
def test_window_scaling(variant):
    ref = cm.load_cost_calibration(variant=variant, window_h=4.0)
    for window_h in (2.0, 4.0, 8.0, 6.0):
        cal = cm.load_cost_calibration(variant=variant, window_h=window_h)
        scale = window_h / 4.0
        assert cal["window_scale"] == pytest.approx(scale)
        assert cal["window_scaled_keys"] == ["F", "F_hub", "bB", "bC"]
        for key in ("F", "F_hub", "bB", "bC"):
            assert cal["costs"][key] == pytest.approx(ref["costs"][key] * scale)
        # kappa, pi, budget coefficients, P / w / v, f / vreb do not scale
        for key in ("kappa", "pi", "pi_peak", "Fhat", "bhat", "chat"):
            assert cal["costs"][key] == ref["costs"][key]
        assert cal["demand_spec"] == ref["demand_spec"]
        assert cal["services_spec"] == ref["services_spec"]


def test_window_scaling_matches_json_variants():
    data = _json()
    eight = cm.load_cost_calibration(variant="usd_A", window_h=8.0)["costs"]
    two = cm.load_cost_calibration(variant="usd_A", window_h=2.0)["costs"]
    for key, val in data["variants"]["window_8h_H96"]["costs"].items():
        assert eight[key] == pytest.approx(val, abs=0.011)
    for key, val in data["variants"]["window_2h_H24"]["costs"].items():
        assert two[key] == pytest.approx(val, abs=0.011)
    assert eight["F"] == pytest.approx(24.06) and eight["bB"] == pytest.approx(0.664)


def test_apply_cost_calibration_explicit_keys_win():
    cal = cm.load_cost_calibration(variant="usd_sunk", window_h=4.0)
    c, d, s = cm.apply_cost_calibration(cal, costs={"kappa": 0.7, "pi_peak": 0.44},
                                        demand_spec={"P": 45.0}, services_spec={"f": 1.0})
    assert c["kappa"] == 0.7 and c["pi_peak"] == 0.44 and c["F"] == cal["costs"]["F"]
    assert d["P"] == 45.0 and d["w"] == 18.0
    assert s["f"] == 1.0 and s["vreb"] == 1.0
    rows = cm.variant_table(window_h=4.0)
    assert [r["variant"] for r in rows] == list(cm.cost_variants())


def test_window_scaling_note_on_bB_initial_charge():
    """Units review F5: the one-off initial charge inside bB is window-scaled per R2.1;
    load_cost_calibration documents the resulting over-/understatement in 'notes'."""
    assert cm.BB_INITIAL_CHARGE_USD == 0.213
    assert cm.load_cost_calibration(variant="usd_A", window_h=4.0)["notes"] == []
    assert cm.load_cost_calibration(variant="toy", window_h=8.0)["notes"] == []
    eight = cm.load_cost_calibration(variant="usd_A", window_h=8.0)
    assert len(eight["notes"]) == 1 and "0.213" in eight["notes"][0] and "+0.213" in eight["notes"][0]
    assert eight["costs"]["bB"] == pytest.approx(0.664)          # unchanged (spec as written)
    two = cm.load_cost_calibration(variant="usd_sunk", window_h=2.0)
    assert "-0.106" in two["notes"][0] or "-0.107" in two["notes"][0]


# ---------------------------------------------------------------------------
# round 5 (notes/reading_to_model.md M5, A6, M10): tariffs, allocations, levers
# ---------------------------------------------------------------------------
def test_tou_tariff_from_the_json():
    data = _json()["variants"]["tou_electricity"]
    tou = cm.load_tariff("tou")
    assert tou["costs"] == {"pi": data["costs"]["pi"], "pi_peak": data["costs"]["pi_peak"]}
    assert tou["costs"] == {"pi": 0.132, "pi_peak": 0.442}
    assert tou["facilities_spec"]["price_peak_hours"] == (8.0, 22.0)
    assert cm.load_tariff("tou_summer")["costs"]["pi_peak"] == 0.74
    assert cm.load_tariff("flat")["costs"] == {} and list(cm.TARIFFS) == ["flat", "tou", "tou_summer"]
    with pytest.raises(KeyError):
        cm.load_tariff("critical_peak")
    # the R2.1 variant table is unchanged: pi_peak is None in every variant
    assert all(cm.load_cost_calibration(variant=v)["costs"]["pi_peak"] is None for v in cm.cost_variants())


def test_allocation_reproduces_the_json_setup_costs():
    assert cm.crf(0.07, 10) == pytest.approx(0.1424, abs=1e-4)
    assert cm.crf(0.0, 4) == 0.25
    with pytest.raises(ValueError):
        cm.crf(0.07, 0)
    # F_j: capex 50,000, CRF(7 %, 10 y), opex 10,200 -> 12.03 per 4 h; b^C_j: 400 at CRF(7 %, 5 y) + 5 %
    assert cm.allocate_per_window(50000, 0.07, 10, 10200, 4.0) == pytest.approx(12.03, abs=0.005)
    assert cm.allocate_per_window(400, 0.07, 5, 20, 4.0) == pytest.approx(0.082, abs=0.001)
    assert cm.allocate_per_window(400, 0.07, 5, 20, 8.0) == pytest.approx(2 * cm.allocate_per_window(400, 0.07, 5, 20, 4.0))
    assert cm.position_cost_per_window() == pytest.approx(400 * cm.crf(0.07, 10) / 360 / 4)


def test_allocated_bike_cost_and_pack_scaling():
    a = cm.allocated_bike_cost(4.0)
    assert a["bike_capex_per_window"] == pytest.approx(1600 * cm.crf(0.07, 3) / 360 / 4)
    assert a["rider_wage_per_window"] == pytest.approx(22.13 * 4)
    assert a["allocated_per_bike_window"] == pytest.approx(a["bike_capex_per_window"] + a["rider_wage_per_window"])
    b = cm.allocated_bike_cost(8.0, include_rider=False, bike_life_years=2.0)
    assert b["rider_wage_per_window"] == 0.0 and b["parameters"]["bike_life_years"] == 2.0
    with pytest.raises(KeyError):
        cm.allocated_bike_cost(4.0, bike_colour=1.0)
    base = cm.load_cost_calibration(variant="usd_sunk")["costs"]
    big = cm.pack_cost_scaling(base, 1.2)
    assert big["bB"] == pytest.approx(2 * base["bB"]) and big["bhat"] == pytest.approx(900.0)
    assert big["F"] == base["F"] and base["bhat"] == 450.0                 # input not mutated
    with pytest.raises(ValueError):
        cm.pack_cost_scaling(base, 0.0)


def test_demand_charge_proxy():
    assert cm.demand_charge_per_window(30.0, 4.0) == pytest.approx(30.0 / 30 * 4 / 16)
    rows = cm.demand_charge_proxy({0.0: None, 0.5: 100.0, 1.0: 99.9}, 30.0, 4.0, n_sites=2)
    assert rows["p_dem_per_kw_window"] == pytest.approx(0.25)
    assert [r["P_kw"] for r in rows["rows"]] == [0.0, 0.5, 1.0] and rows["rows"][0]["total"] is None
    assert rows["best"]["P_kw"] == 0.5 and rows["best"]["total"] == pytest.approx(100.25)
    assert cm.demand_charge_proxy({0.0: None}, 30.0)["best"] is None
