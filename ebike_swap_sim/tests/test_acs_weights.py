"""Tests of ``ebike_swap_sim.acs_weights`` (DECISIONS R2.4 "Zone weights", literature
formula of notes/literature_demand_model.md section 5.1): hand-computed multipliers
on a synthetic 3-zone ACS table, synthetic polygons, the real ACS 2020-24 / NTA-2020
files, the GeoDa fallback switch and the report files."""
from __future__ import annotations

import math
import os
import warnings

import numpy as np
import pandas as pd
import pytest

from ebike_swap_sim import acs_weights as aw
from ebike_swap_sim import data_nyc as dn

REAL = aw.acs_tables_available() and os.path.exists(dn.DEFAULT_PATHS["nta_geojson"])
needs_real = pytest.mark.skipif(not REAL, reason="ACS 2020-24 tables / NTA-2020 polygons missing under data/raw/acs")


# ---------------------------------------------------------------------------
# synthetic 3-zone table (raw ACS column names) with hand-computed shares
# ---------------------------------------------------------------------------
def _zone(code: str, name: str, **kw) -> dict:
    base = {c: 0.0 for cols in aw.ACS_COLUMNS.values() for c in cols}
    base.update({"GeoType": "NTA2020", "NTAType": 0, "GeogName": name, "GeoID": code, "Borough": "Test"})
    base.update(kw)
    return base


ZONE_A = _zone(  # young zone: 40 % 18-29, 30 % 30-44, 20 % 45-59, 10 % 60+
    "ZA", "Young", Pop_1E=1300, PopU181E=300, PopU5E=100, Pop5t9E=80, Pop10t14E=70, Pop15t19E=150,
    Pop20t24E=150, Pop25t29E=150, Pop30t34E=100, Pop35t39E=100, Pop40t44E=100,
    Pop45t49E=70, Pop50t54E=70, Pop55t59E=60, Pop60t64E=40, Pop65pl1E=60,
    FemE=650, PopU18FE=150, WtNHE=650, BlNHE=130, Hsp1E=260,
    HH1E=500, FamChU18E=100, NFamAE=250, HHPopE=1300, SE_ClgGScE=100,
    OChU6E=60, OCh6t17E=120, HH2E=500, Inc_SNAPE=100, PopPvU2E=1000,
    Pv200t299E=200, Pv300t399E=200, Pv400t499E=200, Pv500plE=200)
ZONE_B = _zone(  # old zone: 10 / 20 / 30 / 40 %, everything else at the reference level
    "ZB", "Old", Pop_1E=1000, PopU181E=0, Pop15t19E=0, Pop20t24E=50, Pop25t29E=50,
    Pop30t34E=100, Pop35t39E=50, Pop40t44E=50, Pop45t49E=100, Pop50t54E=100, Pop55t59E=100,
    Pop60t64E=100, Pop65pl1E=300, FemE=0, PopU18FE=0, WtNHE=1000, HH1E=400, HH2E=400,
    HHPopE=1000, PopPvU2E=1000)
ZONE_C = _zone("ZC", "Park", NTAType=9)  # no population at all


@pytest.fixture(scope="module")
def synth_raw() -> pd.DataFrame:
    return pd.DataFrame([ZONE_A, ZONE_B, ZONE_C])


def _square(lat0: float, lon0: float, d: float = 0.01) -> dict:
    return {"type": "Polygon", "coordinates": [[[lon0, lat0], [lon0 + d, lat0], [lon0 + d, lat0 + d],
                                                [lon0, lat0 + d], [lon0, lat0]]]}


@pytest.fixture(scope="module")
def synth_geojson() -> dict:
    feats = []
    for code, name, lat0, lon0 in (("ZA", "Young", 40.74, -74.00), ("ZB", "Old", 40.74, -73.99), ("ZC", "Park", 40.74, -73.98)):
        feats.append({"type": "Feature", "geometry": _square(lat0, lon0),
                      "properties": {"nta2020": code, "ntaname": name, "boroname": "Test", "ntatype": "9" if code == "ZC" else "0"}})
    return {"type": "FeatureCollection", "features": feats}


def test_shares_hand_computed(synth_raw):
    sh = aw.acs_shares(synth_raw).set_index("GeoID")
    a = sh.loc["ZA"]
    assert a["pop18"] == 1000 and a["a18_19"] == 100           # 15-19 (150) minus 15-17 (300-100-80-70 = 50)
    assert (a["s18_29"], a["s30_44"], a["s45_59"], a["s60p"]) == pytest.approx((0.4, 0.3, 0.2, 0.1))
    assert a["s_female"] == pytest.approx(0.5)                   # (650 - 150) / 1000
    assert (a["s_white"], a["s_black"], a["s_hisp"], a["s_other"]) == pytest.approx((0.5, 0.1, 0.2, 0.2))
    assert a["s_adequate"] == pytest.approx(0.8)
    assert a["h_kid"] == pytest.approx(0.2) and a["h_pre"] == pytest.approx(0.2 / 3) and a["h_school"] == pytest.approx(0.4 / 3)
    assert a["s_alone"] == pytest.approx(0.5) and a["s_student"] == pytest.approx(0.1) and a["s_snap"] == pytest.approx(0.2)
    assert a["gq_share"] == 0.0
    b = sh.loc["ZB"]
    assert (b["s18_29"], b["s30_44"], b["s45_59"], b["s60p"]) == pytest.approx((0.1, 0.2, 0.3, 0.4))
    assert b["s_white"] == 1.0 and b["s_female"] == 0.0 and b["s_adequate"] == 0.0
    c = sh.loc["ZC"]
    assert c["pop18"] == 0 and all(c[k] == 0.0 for k in aw.SHARE_COLUMNS)
    # every share documented
    assert set(aw.SHARE_COLUMNS) <= set(aw.SHARE_DERIVATIONS) and {"pop18", "pop_total"} <= set(aw.SHARE_DERIVATIONS)


def test_multipliers_hand_computed(synth_raw):
    wt = aw.compute_zone_weights(synth_raw).set_index("GeoID")
    a = wt.loc["ZA"]
    m_age = 3.4 * 0.4 + 3.0 * 0.3 + 1.9 * 0.2 + 1.0 * 0.1            # 2.74
    m_eth = 1.0 * 0.5 + 1.17 * 0.1 + 1.26 * 0.2 + 1.12 * 0.2        # 1.093
    m_sex = 1 - 0.09 * 0.5                                           # 0.955
    m_inc = 1 + 0.17 * 0.8                                           # 1.136
    m_kid = 1 + 0.22 * (0.2 / 3) + 0.29 * (0.4 / 3)
    m_alone = 1 + 0.10 * 0.5
    m_stu = 1 + 0.12 * 0.1
    assert a["M_age"] == pytest.approx(2.74) and a["M_eth"] == pytest.approx(1.093)
    assert a["M_sex"] == pytest.approx(0.955) and a["M_inc"] == pytest.approx(1.136)
    assert a["M_kid"] == pytest.approx(m_kid) and a["M_alone"] == pytest.approx(1.05) and a["M_stu"] == pytest.approx(1.012)
    assert a["M_fi"] == 1.0                                          # R2.4: M_FI OFF by default
    total = m_age * m_eth * m_sex * m_inc * m_kid * m_alone * m_stu
    assert a["M_total"] == pytest.approx(total) and a["w_z"] == pytest.approx(1000 * total)
    b = wt.loc["ZB"]
    assert b["M_age"] == pytest.approx(0.34 + 0.6 + 0.57 + 0.4)      # 1.91
    assert b["M_total"] == pytest.approx(1.91) and b["w_z"] == pytest.approx(1910)
    c = wt.loc["ZC"]
    assert c["w_z"] == 0.0 and c["M_total"] == 1.0 and c["pi_z"] == 0.0
    assert wt["pi_z"].sum() == pytest.approx(1.0)
    assert a["M_total"] > b["M_total"]                               # young zone beats old zone per adult
    # sensitivity switches
    fi = aw.compute_zone_weights(synth_raw, food_insecurity=True).set_index("GeoID")
    assert fi.loc["ZA", "M_fi"] == pytest.approx(1 + 0.38 * 0.2) and fi.loc["ZA", "w_z"] == pytest.approx(a["w_z"] * (1 + 0.38 * 0.2))
    cap = aw.compute_zone_weights(synth_raw, student_cap=1.005).set_index("GeoID")
    assert cap.loc["ZA", "M_stu"] == pytest.approx(1.005)


def test_synthetic_zone_weights_object(synth_raw, synth_geojson):
    zw = aw.ACSZoneWeights(acs_table=synth_raw, geojson=synth_geojson, fallback="never")
    assert isinstance(zw, dn.ZoneWeights) and not zw.is_fallback and zw.warning is None
    assert zw.source == aw.ACS_SOURCE and zw.vintage == "NTA2020" and zw.zones() == ["ZA", "ZB", "ZC"]
    area_a = dn.polygon_area_km2(_square(40.74, -74.00))
    assert zw.zone_at(40.745, -73.995) == "ZA" and zw.zone_at(40.745, -73.985) == "ZB" and zw.zone_at(40.745, -73.975) == "ZC"
    assert zw.weight_at(40.745, -73.995) == pytest.approx(zw.zone_total("ZA") / area_a)
    assert zw.weight_at(40.745, -73.975) == 0.0 and zw.zone_total("ZC") == 0.0   # park ~0
    assert zw.zone_at(41.0, -73.0) is None and zw.weight_at(41.0, -73.0) == 0.0
    tab = zw.table()
    assert list(tab["code"]) == ["ZA", "ZB", "ZC"] and tab["acs_matched"].all()
    assert zw.info("ZA")["M_age"] == pytest.approx(2.74) and zw.info("ZB")["ntatype"] == 0 and zw.info("ZC")["ntatype"] == 9
    assert dn.as_zone_weight_fn(zw) == zw.weight_at
    m = zw.meta()
    assert m["zone_weights_source"] == aw.ACS_SOURCE and m["zone_weights_warning"] is None and m["zone_weights_n_zones"] == 3
    # a box that only touches ZA restricts zones()
    box = dn.StudyBox(lat_min=40.741, lat_max=40.749, lon_min=-73.999, lon_max=-73.991)
    assert aw.ACSZoneWeights(acs_table=synth_raw, geojson=synth_geojson, box=box, fallback="never").zones() == ["ZA"]
    # polygon vintage mismatch (codes not in the table) must not pass silently
    bad = {"type": "FeatureCollection", "features": [dict(f, properties=dict(f["properties"], nta2020="MN" + f["properties"]["nta2020"]))
                                                     for f in synth_geojson["features"]]}
    with pytest.raises(ValueError, match="vintage"):
        aw.ACSZoneWeights(acs_table=synth_raw, geojson=bad, fallback="never")


def test_synthetic_destination_sampler(synth_raw, synth_geojson):
    zw = aw.ACSZoneWeights(acs_table=synth_raw, geojson=synth_geojson, fallback="never")
    box = dn.StudyBox(lat_min=40.74, lat_max=40.75, lon_min=-74.0, lon_max=-73.97)
    dest = dn.NYCDestinationSampler(box, zw, np.random.default_rng(1))
    mass = dest.zone_totals()
    assert set(mass) <= {"ZA", "ZB"} and mass["ZA"] > mass["ZB"] > 0 and "ZC" not in mass
    # equal-area squares: node mass ratio ~ w_A / w_B (grid discretisation aside)
    ratio = mass["ZA"] / mass["ZB"]
    assert 0.7 * (zw.zone_total("ZA") / zw.zone_total("ZB")) < ratio < 1.3 * (zw.zone_total("ZA") / zw.zone_total("ZB"))
    draws = [dest.sample() for _ in range(50)]
    assert all(dest.zone_of(d) in (0, 1) for d in draws)


# ---------------------------------------------------------------------------
# fallback switch (R2.4): wraps GeoDaZoneWeights with a loud warning
# ---------------------------------------------------------------------------
@pytest.mark.skipif(not os.path.exists(dn.DEFAULT_PATHS["nta_geojson"]), reason="GeoDa GeoJSON missing")
def test_fallback_when_tables_missing(tmp_path):
    missing = {"dem": str(tmp_path / "nope.xlsx")}
    with pytest.warns(UserWarning, match="FALLBACK"):
        zw = aw.ACSZoneWeights(paths=missing, box=dn.DEFAULT_BOX)
    assert zw.is_fallback and zw.source == "geoda_fallback" and zw.vintage == "NTA2010"
    assert "FileNotFoundError" in zw.warning and "GeoDa" in zw.warning and "medianinco" in zw.warning
    assert isinstance(zw, dn.ZoneWeights) and isinstance(zw.fallback, dn.GeoDaZoneWeights)
    assert all(z.startswith("MN") and len(z) == 4 for z in zw.zones()) and "MN17" in zw.zones()
    assert zw.zone_at(40.7484, -73.9857) == "MN17" and zw.weight_at(40.7484, -73.9857) == zw.fallback.weight_at(40.7484, -73.9857)
    assert zw.meta()["zone_weights_source"] == "geoda_fallback" and "FALLBACK" in zw.meta()["zone_weights_warning"]
    assert not aw.acs_tables_available(missing)
    with pytest.raises(FileNotFoundError):
        aw.ACSZoneWeights(paths=missing, fallback="never")
    with pytest.raises(FileNotFoundError):
        aw.load_acs_tables(missing)
    forced = aw.ACSZoneWeights(box=dn.DEFAULT_BOX, fallback="force", warn=False)
    assert forced.is_fallback and "forced" in forced.warning
    with pytest.raises(RuntimeError, match="fallback"):
        aw.weights_table(box=dn.DEFAULT_BOX, zw=forced)


# ---------------------------------------------------------------------------
# real files: ACS 2020-24 + NTA-2020 polygons (MANIFEST section 5)
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def zw_city():
    if not REAL:
        pytest.skip("real ACS files missing")
    with warnings.catch_warnings():
        warnings.simplefilter("error")          # the formula path must not warn
        return aw.ACSZoneWeights(box=None, fallback="never")


@pytest.fixture(scope="module")
def zw_box():
    if not REAL:
        pytest.skip("real ACS files missing")
    return aw.ACSZoneWeights(box=dn.DEFAULT_BOX, fallback="never")


@needs_real
def test_real_tables_and_shares():
    raw = aw.load_acs_tables()
    assert len(raw) == 262 and raw["GeoID"].is_unique and raw["GeoType"].eq("NTA2020").all()
    for cols in aw.ACS_COLUMNS.values():
        assert set(cols) <= set(raw.columns)
    sh = aw.acs_shares(raw)
    pos = sh["pop18"] > 0
    assert pos.sum() >= 200
    assert np.allclose(sh.loc[pos, ["s18_29", "s30_44", "s45_59", "s60p"]].sum(axis=1), 1.0)       # age bands exact
    assert np.allclose(sh.loc[sh["pop_total"] > 0, ["s_white", "s_black", "s_hisp", "s_other"]].sum(axis=1), 1.0)
    assert sh["a18_19"].ge(0).all() and sh.loc[pos, "s_female"].between(0, 1).all()
    assert sh.loc[pos, ["s_adequate", "s_alone", "s_student", "s_snap", "h_kid", "h_pre", "h_school", "gq_share"]].ge(0).all().all()
    assert sh.loc[pos, ["s_adequate", "s_alone", "s_snap", "h_kid"]].le(1).all().all()
    assert sh["pop18"].sum() == pytest.approx(6_771_234)                                              # MANIFEST section 5
    wt = aw.literature_multipliers(sh)
    assert np.isfinite(wt[list(aw.MULTIPLIER_COLUMNS) + ["w_z"]].to_numpy()).all()
    assert (wt["w_z"] >= 0).all() and (wt.loc[pos, "w_z"] > 0).all() and (wt.loc[~pos, "w_z"] == 0).all()
    assert wt.loc[pos, "M_age"].between(1.0, 3.4).all() and wt.loc[pos, "M_total"].between(1.0, 5.0).all()


@needs_real
def test_real_zone_weights_default_box(zw_box, zw_city):
    assert not zw_box.is_fallback and zw_box.warning is None and zw_box.source == aw.ACS_SOURCE
    expected = {"MN0202", "MN0203", "MN0401", "MN0402", "MN0501", "MN0502", "MN0601", "MN0602", "MN0603",
                "MN0604", "MN0661", "MN0701", "MN0801", "MN0802", "MN6491"}
    assert set(zw_box.zones()) == expected and len(zw_city.zones()) == 262
    assert zw_box.zone_at(40.7484, -73.9857) == "MN0501"                       # Empire State Building -> Midtown South
    assert zw_city.zone_at(40.7812, -73.9665) == "MN6491"                      # Central Park
    assert zw_city.weight_at(40.7812, -73.9665) == 0.0 and zw_city.zone_total("MN6491") == 0.0   # park ~0
    assert zw_box.zone_at(40.0, -73.0) is None and zw_box.weight_at(40.0, -73.0) == 0.0
    tab = zw_box.table()
    assert tab["acs_matched"].all() and np.isfinite(tab[["w_total", "density"]].to_numpy()).all()
    res = tab[(tab["ntatype"] == 0)]
    assert (res["w_total"] > 0).all() and (res["density"] > 0).all()
    assert (tab.loc[tab["ntatype"] != 0, "w_total"] == 0).all()
    for code in ("MN0501", "MN0401"):
        info = zw_box.info(code)
        assert info["w_total"] == pytest.approx(info["pop18"] * info["M_total"])
        assert zw_box.weight_at(*_centroid_inside(zw_box, code)) == pytest.approx(info["w_total"] / info["area_km2"])
    # young zones (Flatiron / Chelsea / East Village) beat the 60+ Upper East Side per adult
    assert zw_city.info("MN0303")["name"] == "East Village"
    for young in ("MN0303", "MN0501", "MN0401"):
        assert zw_city.info(young)["M_total"] > zw_city.info("MN0802")["M_total"]   # Carnegie Hill
        assert zw_city.info(young)["M_age"] > zw_city.info("MN0802")["M_age"]
    assert zw_city.info("MN0802")["s60p"] > 0.4 > zw_city.info("MN0303")["s60p"]


def _centroid_inside(zw: aw.ACSZoneWeights, code: str):
    f = zw._by_code[code]
    b = f["bbox"]
    # walk a small grid over the bbox until a point inside the polygon is found
    for i in range(1, 20):
        for j in range(1, 20):
            lon = b[0] + (b[2] - b[0]) * i / 20
            lat = b[1] + (b[3] - b[1]) * j / 20
            if dn.point_in_geometry(lon, lat, f["geometry"]):
                return lat, lon
    raise AssertionError("no interior point found")


@needs_real
def test_real_destination_sampler_and_meta(zw_box):
    dest = dn.NYCDestinationSampler(dn.DEFAULT_BOX, zw_box, np.random.default_rng(0))
    assert len(dest.support) > 300 and set(dest.zone_ids()) <= set(zw_box.zones())
    mass = dest.zone_totals()
    assert "MN6491" not in mass and "MN0661" not in mass                     # park / UN get no mass
    assert sum(mass.values()) == pytest.approx(1.0) and mass["MN0401"] > 0.05 and mass["MN0603"] > 0.05
    draws = [dest.sample() for _ in range(200)]
    assert all(dest.zone_of(d) >= 0 for d in draws)
    assert dest.sample(np.random.default_rng(7)) == dn.NYCDestinationSampler(
        dn.DEFAULT_BOX, zw_box, None).sample(np.random.default_rng(7))        # deterministic
    m = zw_box.meta()
    assert m["zone_weights_source"] == aw.ACS_SOURCE and m["zone_weights_vintage"] == "NTA2020" and m["zone_weights_warning"] is None


@needs_real
def test_weights_table_and_files(zw_city, tmp_path):
    df = aw.weights_table(box=dn.DEFAULT_BOX, zw=zw_city, borough="Manhattan")
    assert list(df.columns) == aw._TABLE_COLUMNS and df["ntacode"].str.startswith("MN").all()
    assert df["in_box"].sum() == 15 and df["share_box"].sum() == pytest.approx(1.0) and df["share_all"].sum() == pytest.approx(1.0)
    assert (df.loc[~df["in_box"], "share_box"] == 0).all()
    assert np.isfinite(df[["w_z", "density_km2", "M_total"]].to_numpy()).all() and (df["w_z"] >= 0).all()
    assert (df.loc[df["ntatype"] == 9, "share_all"] < 0.01).all()          # park zones ~0 (two carry a few residents)
    assert (df.loc[df["pop18"] == 0, "w_z"] == 0).all() and (df.loc[(df["ntatype"] == 0) & (df["pop18"] > 0), "w_z"] > 0).all()
    assert df["w_z"].is_monotonic_decreasing
    res = df[(df["ntatype"] == 0) & (df["pop18"] > 0)].set_index("ntacode")
    assert res.loc["MN0303", "M_total"] > res.loc["MN0802", "M_total"] and res.loc["MN0501", "M_total"] > res.loc["MN0802", "M_total"]
    assert res["M_total"].idxmin() in ("MN0802", "MN0301", "MN0604")           # 60+ heavy zones at the bottom
    csv = tmp_path / "zw.csv"
    md = tmp_path / "zw_README.md"
    out = aw.write_zone_weights(box=dn.DEFAULT_BOX, csv_path=str(csv), readme_path=str(md))
    back = pd.read_csv(csv)
    assert len(back) == len(out) == len(df) and set(back.columns) == set(aw._TABLE_COLUMNS)
    text = md.read_text(encoding="utf-8")
    assert "M_age" in text and "NTA-2020" in text and "## Summary" in text and "Upper East Side" in text and "s18_29" in text
    # the committed deliverables exist and agree with a fresh computation
    assert os.path.exists(aw.ZONE_WEIGHTS_CSV) and os.path.exists(aw.ZONE_WEIGHTS_README)
    saved = pd.read_csv(aw.ZONE_WEIGHTS_CSV).set_index("ntacode")
    assert saved.loc["MN0501", "w_z"] == pytest.approx(df.set_index("ntacode").loc["MN0501", "w_z"], rel=1e-4)


def test_gq_correction_option(synth_raw, synth_geojson):
    """Units review F4: optional group-quarters correction N_z = pop18 x (1 - gq_share)
    (literature note section 5.1); default OFF keeps N_z = pop18 and is recorded."""
    base = aw.compute_zone_weights(synth_raw).set_index("GeoID")
    assert base.loc["ZA", "N_z"] == 1000 and bool(base.loc["ZA", "gq_correction_on"]) is False
    raw2 = synth_raw.copy()
    raw2.loc[raw2.GeoID == "ZA", "HHPopE"] = 1040.0          # 260 of 1300 in group quarters -> gq_share 0.2
    off = aw.compute_zone_weights(raw2).set_index("GeoID")
    on = aw.compute_zone_weights(raw2, gq_correction=True).set_index("GeoID")
    assert on.loc["ZA", "gq_share"] == pytest.approx(0.2) and off.loc["ZA", "N_z"] == 1000
    assert on.loc["ZA", "N_z"] == pytest.approx(800) and on.loc["ZA", "w_z"] == pytest.approx(800 * on.loc["ZA", "M_total"])
    assert on.loc["ZA", "M_total"] == pytest.approx(off.loc["ZA", "M_total"])   # multipliers unchanged
    assert on.loc["ZB", "w_z"] == pytest.approx(off.loc["ZB", "w_z"])            # no group quarters there
    zw = aw.ACSZoneWeights(acs_table=raw2, geojson=synth_geojson, gq_correction=True, fallback="never", warn=False)
    assert zw.meta()["zone_weights_gq_correction"] is True and zw.zone_total("ZA") == pytest.approx(on.loc["ZA", "w_z"])
    zw0 = aw.ACSZoneWeights(acs_table=raw2, geojson=synth_geojson, fallback="never", warn=False)
    assert zw0.meta()["zone_weights_gq_correction"] is False and zw0.info("ZA")["N_z"] == 1000
