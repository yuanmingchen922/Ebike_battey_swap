"""Literature zone weights on ACS 2020-24 5-year NTA tables (DECISIONS.md R2.4 "Zone weights").

Implements the demand-model weight formula of ``notes/literature_demand_model.md``
section 5.1 (Bennett 2025 participation odds x Buettner 2023 frequency rate ratios)
exactly as fixed in R2.4::

    w_z = N_z x M_age x M_eth x M_sex x M_inc x M_kid x M_alone x M_stu [x M_FI]

    N_z     = population 18+                                        (Dem: Pop_1E - PopU181E)
    M_age   = 3.4 s18_29 + 3.0 s30_44 + 1.9 s45_59 + 1.0 s60p        (shares of pop 18+)
    M_eth   = 1.0 s_white + 1.17 s_black + 1.26 s_hisp + 1.12 s_other (shares of total pop)
    M_sex   = 1 - 0.09 s_female                                      (female share of pop 18+)
    M_inc   = 1 + 0.17 s_adequate                                    (share >= 200 % poverty)
    M_kid   = 1 + 0.22 h_pre + 0.29 h_school                         (household shares)
    M_alone = 1 + 0.10 s_alone                                       (one-person HH / HH)
    M_stu   = 1 + 0.12 s_student                                     (college enrolled / pop 18+)
    M_FI    = 1 + 0.38 s_snap   (OFF by default, R2.4)               (SNAP HH / HH)

and ``pi_z = w_z / sum w``.  Every share is derived from the DCP ACS profile
columns listed in :data:`SHARE_DERIVATIONS` (documented column -> share map; the
MANIFEST section 5 validation guarantees the age bands sum to pop 18+ and the
race / Hispanic groups to the total population).

**NTA vintage.**  The ACS tables are NTA-2020 (262 zones, ``GeoID`` such as
``MN0501``) and the GeoDa fallback polygons are NTA-2010 (195 zones, ``MN17``).
The two code systems do NOT coincide, so no crosswalk is attempted: this module
uses the NTA-2020 polygon file ``data/raw/acs/nta2020.geojson`` (262 features,
``nta2020`` == ``GeoID`` in all four workbooks) for point-in-polygon lookup.
Zone codes seen by the sampler are therefore NTA-2020 codes; the GeoDa 2010
polygons are only touched when the fallback is active.

**Fallback (R2.4).**  If the ACS workbooks or the NTA-2020 GeoJSON are missing or
unusable (missing columns, no ``openpyxl``), :class:`ACSZoneWeights` wraps
:class:`~ebike_swap_sim.data_nyc.GeoDaZoneWeights` (``poptot x (1 + 2.4 x
youth16_19_share)``), sets ``source = 'geoda_fallback'`` and issues a loud
warning that the instance builder writes into ``meta['zone_weights_warning']``.
The formula code path (:func:`acs_shares`, :func:`literature_multipliers`,
:func:`compute_zone_weights`) is pure pandas and is unit-tested on a synthetic
table so it runs unchanged on any table with the same column names.

Weights exposed through the :class:`~ebike_swap_sim.data_nyc.ZoneWeights`
interface are *densities* ``w_z / area_z`` in km^-2 (same convention as the
GeoDa fallback, so :class:`~ebike_swap_sim.data_nyc.NYCDestinationSampler`
reproduces ``pi_z`` restricted to the part of each zone inside the study box).
Pure-python geometry (ray casting from ``data_nyc``); no shapely, no gurobipy.
The E2 mathematics (arcs / ilp / evaluate) is untouched.
"""
from __future__ import annotations

import functools
import json
import os
import warnings
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd

from .data_nyc import (
    DATA_RAW,
    DEFAULT_BOX,
    DEFAULT_PATHS,
    GEODA_FALLBACK_WARNING,
    NOTES_DATA,
    GeoDaZoneWeights,
    StudyBox,
    _geometry_bbox,
    point_in_geometry,
    polygon_area_km2,
)

__all__ = [
    "ACS_DIR", "ACS_PATHS", "ACS_SOURCE", "ACS_FALLBACK_WARNING", "NTA_VINTAGE_NOTE",
    "RR_AGE", "RR_ETH", "RR_BIN", "RR_KID", "RR_FI", "ACS_COLUMNS", "SHARE_DERIVATIONS",
    "SHARE_COLUMNS", "MULTIPLIER_COLUMNS",
    "acs_tables_available", "load_acs_tables", "load_nta2020", "acs_shares",
    "literature_multipliers", "compute_zone_weights", "ACSZoneWeights",
    "weights_table", "write_zone_weights", "ZONE_WEIGHTS_CSV", "ZONE_WEIGHTS_README",
]

# ---------------------------------------------------------------------------
# paths and constants
# ---------------------------------------------------------------------------
ACS_DIR = os.path.join(DATA_RAW, "acs")

#: ACS 2020-24 5-year DCP profiles by NTA-2020 and the NTA-2020 polygons (MANIFEST section 5).
ACS_PATHS: Dict[str, str] = {
    "dem": os.path.join(ACS_DIR, "Dem_2024ACS5YR_NTA.xlsx"),
    "soc": os.path.join(ACS_DIR, "Soc_2024ACS5YR_NTA.xlsx"),
    "econ": os.path.join(ACS_DIR, "Econ_2024ACS5YR_NTA.xlsx"),
    "nta2020": os.path.join(ACS_DIR, "nta2020.geojson"),
}
_SHEETS = {"dem": "DemData", "soc": "SocData", "econ": "EconData"}
_ID_COLUMNS = ("GeoType", "NTAType", "GeogName", "GeoID", "Borough")

#: ``meta['zone_weights_source']`` when the literature formula on ACS 2020-24 is used.
ACS_SOURCE = "acs_2020_24_literature"

#: Loud warning when the ACS path is unusable and the GeoDa fallback is active (R2.4).
ACS_FALLBACK_WARNING = (
    "ZONE WEIGHTS FALLBACK (R2.4): the ACS 2020-24 NTA tables / NTA-2020 polygons under "
    "data/raw/acs/ are missing or unusable, so the literature formula "
    "(N_z x M_age x M_eth x M_sex x M_inc x M_kid x M_alone x M_stu) was NOT applied. "
)

#: Written into ``meta`` together with the source: which polygon vintage the codes refer to.
NTA_VINTAGE_NOTE = (
    "Zone codes are NTA-2020 (DCP ACS 2020-24 GeoID == nta2020.geojson); the GeoDa "
    "NTA-2010 codes (MN17 etc.) are a different system and are not mapped."
)

#: Rate ratios of the literature formula (literature_demand_model.md section 5.1, R2.4).
RR_AGE: Dict[str, float] = {"s18_29": 3.4, "s30_44": 3.0, "s45_59": 1.9, "s60p": 1.0}
RR_ETH: Dict[str, float] = {"s_white": 1.0, "s_black": 1.17, "s_hisp": 1.26, "s_other": 1.12}
RR_BIN: Dict[str, float] = {"s_female": 0.91, "s_adequate": 1.17, "s_alone": 1.10, "s_student": 1.12}
RR_KID: Dict[str, float] = {"h_pre": 1.22, "h_school": 1.29}
RR_FI: Dict[str, float] = {"s_snap": 1.38}

#: Raw estimate columns read from each workbook (all ``*E`` = ACS estimates).
ACS_COLUMNS: Dict[str, Tuple[str, ...]] = {
    "dem": ("Pop_1E", "FemE", "PopU5E", "Pop5t9E", "Pop10t14E", "Pop15t19E", "Pop20t24E",
            "Pop25t29E", "Pop30t34E", "Pop35t39E", "Pop40t44E", "Pop45t49E", "Pop50t54E",
            "Pop55t59E", "Pop60t64E", "Pop65pl1E", "PopU181E", "PopU18FE",
            "Hsp1E", "WtNHE", "BlNHE"),
    "soc": ("HH1E", "FamChU18E", "NFamAE", "HHPopE", "SE_ClgGScE"),
    "econ": ("OChU6E", "OCh6t17E", "HH2E", "Inc_SNAPE", "PopPvU2E",
             "Pv200t299E", "Pv300t399E", "Pv400t499E", "Pv500plE"),
}

#: Documented column -> share derivations (MANIFEST section 5 "Derivations").
SHARE_DERIVATIONS: Dict[str, str] = {
    "pop_total": "Pop_1E (DP05 total population)",
    "pop18": "N_z = Pop_1E - PopU181E (population 18+)",
    "a18_19": "Pop15t19E - (PopU181E - PopU5E - Pop5t9E - Pop10t14E), clipped at 0 (15-17 removed from 15-19)",
    "s18_29": "(a18_19 + Pop20t24E + Pop25t29E) / pop18",
    "s30_44": "(Pop30t34E + Pop35t39E + Pop40t44E) / pop18",
    "s45_59": "(Pop45t49E + Pop50t54E + Pop55t59E) / pop18",
    "s60p": "(Pop60t64E + Pop65pl1E) / pop18   (the four age shares sum to 1 exactly)",
    "s_female": "(FemE - PopU18FE) / pop18   (female 18+ share of pop 18+)",
    "s_white": "WtNHE / Pop_1E   (non-Hispanic white alone)",
    "s_black": "BlNHE / Pop_1E   (non-Hispanic Black alone)",
    "s_hisp": "Hsp1E / Pop_1E   (Hispanic / Latino of any race)",
    "s_other": "(Pop_1E - WtNHE - BlNHE - Hsp1E) / Pop_1E   (NH Asian, AIAN, NHPI, other, 2+ races)",
    "s_adequate": "(Pv200t299E + Pv300t399E + Pv400t499E + Pv500plE) / PopPvU2E   (B17024, >= 200 % of poverty)",
    "h_kid": "FamChU18E / HH1E   (B11003 households with own children < 18 / DP02 households)",
    "h_pre": "h_kid x OChU6E / (OChU6E + OCh6t17E)   (split by DP03 own-children counts; B11003 age split not published at NTA level)",
    "h_school": "h_kid x OCh6t17E / (OChU6E + OCh6t17E)",
    "s_alone": "NFamAE / HH1E   (B11001 householder living alone)",
    "s_student": "SE_ClgGScE / pop18   (DP02 enrolled in college or graduate school / pop 18+)",
    "s_snap": "Inc_SNAPE / HH2E   (DP03 households with SNAP, optional M_FI only)",
    "gq_share": "(Pop_1E - HHPopE) / Pop_1E   (group-quarters share, reported only)",
}
SHARE_COLUMNS: Tuple[str, ...] = (
    "s18_29", "s30_44", "s45_59", "s60p", "s_female", "s_white", "s_black", "s_hisp", "s_other",
    "s_adequate", "h_kid", "h_pre", "h_school", "s_alone", "s_student", "s_snap", "gq_share",
)
MULTIPLIER_COLUMNS: Tuple[str, ...] = ("M_age", "M_eth", "M_sex", "M_inc", "M_kid", "M_alone", "M_stu", "M_fi", "M_total")

ZONE_WEIGHTS_CSV = os.path.join(NOTES_DATA, "zone_weights_manhattan.csv")
ZONE_WEIGHTS_README = os.path.join(NOTES_DATA, "zone_weights_README.md")


# ---------------------------------------------------------------------------
# 1. loading
# ---------------------------------------------------------------------------
def acs_tables_available(paths: Optional[Dict[str, str]] = None) -> bool:
    """True iff the three ACS workbooks and the NTA-2020 GeoJSON of :data:`ACS_PATHS`
    (or ``paths``) exist on disk (R2.4: decides formula vs GeoDa fallback)."""
    p = dict(ACS_PATHS, **(paths or {}))
    return all(os.path.exists(p[k]) for k in ("dem", "soc", "econ", "nta2020"))


def _safe_div(num: pd.Series, den: pd.Series) -> pd.Series:
    out = num.astype(float) / den.astype(float).where(den.astype(float) > 0, np.nan)
    return out.fillna(0.0)


@functools.lru_cache(maxsize=4)
def _load_acs_tables_cached(dem: str, soc: str, econ: str) -> pd.DataFrame:
    frames = []
    for key, path in (("dem", dem), ("soc", soc), ("econ", econ)):
        df = pd.read_excel(path, sheet_name=_SHEETS[key])
        cols = list(_ID_COLUMNS) + list(ACS_COLUMNS[key])
        missing = [c for c in cols if c not in df.columns]
        if missing:
            raise KeyError(f"ACS workbook {os.path.basename(path)} lacks columns {missing}")
        sub = df[cols].copy() if key == "dem" else df[["GeoID"] + list(ACS_COLUMNS[key])].copy()
        frames.append(sub)
    out = frames[0].merge(frames[1], on="GeoID", how="inner").merge(frames[2], on="GeoID", how="inner")
    if len(out) != len(frames[0]):
        raise ValueError("ACS workbooks do not share the same GeoID set")
    for c in [c for cols in ACS_COLUMNS.values() for c in cols]:
        out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0.0).astype(float)
    out["NTAType"] = pd.to_numeric(out["NTAType"], errors="coerce").fillna(-1).astype(int)
    return out.sort_values("GeoID").reset_index(drop=True)


def load_acs_tables(paths: Optional[Dict[str, str]] = None) -> pd.DataFrame:
    """Merged ACS 2020-24 NTA-2020 table (one row per ``GeoID``) with the id columns
    and exactly the estimate columns of :data:`ACS_COLUMNS` (R2.4; MANIFEST section 5).
    Cached per path triple; raises ``FileNotFoundError`` / ``KeyError`` if unusable."""
    p = dict(ACS_PATHS, **(paths or {}))
    for k in ("dem", "soc", "econ"):
        if not os.path.exists(p[k]):
            raise FileNotFoundError(p[k])
    return _load_acs_tables_cached(p["dem"], p["soc"], p["econ"]).copy()


def load_nta2020(path: Optional[str] = None) -> Dict[str, Any]:
    """NTA-2020 GeoJSON (262 features, properties ``nta2020``, ``ntaname``, ``boroname``,
    ``ntatype``; MANIFEST section 5).  Codes equal the ACS ``GeoID`` (R2.4 vintage choice)."""
    path = path or ACS_PATHS["nta2020"]
    with open(path, "r", encoding="utf-8") as fh:
        gj = json.load(fh)
    if "features" not in gj:
        raise ValueError(f"{path} is not a FeatureCollection")
    return gj


# ---------------------------------------------------------------------------
# 2. the formula (pure pandas; runs on any table with the ACS column names)
# ---------------------------------------------------------------------------
def acs_shares(raw: pd.DataFrame) -> pd.DataFrame:
    """Derive ``pop_total``, ``pop18`` (= ``N_z``) and every share of
    :data:`SHARE_DERIVATIONS` from the raw ACS estimate columns (R2.4 formula
    inputs; literature_demand_model.md section 5.1 / appendix A).

    Input: one row per zone with the columns of :data:`ACS_COLUMNS` (``GeoID`` and
    the id columns are carried through when present).  Zero denominators give share
    0 (zones without population get ``w_z = 0`` anyway).  The four age shares sum to
    1 and the four ethnicity shares sum to 1 wherever the denominator is positive.
    """
    df = raw.copy()
    g = lambda c: df[c].astype(float)  # noqa: E731
    out = pd.DataFrame(index=df.index)
    for c in _ID_COLUMNS:
        if c in df.columns:
            out[c] = df[c]
    out["pop_total"] = g("Pop_1E")
    out["pop18"] = (g("Pop_1E") - g("PopU181E")).clip(lower=0.0)
    a15_17 = (g("PopU181E") - g("PopU5E") - g("Pop5t9E") - g("Pop10t14E")).clip(lower=0.0)
    out["a18_19"] = (g("Pop15t19E") - a15_17).clip(lower=0.0)
    a18_29 = out["a18_19"] + g("Pop20t24E") + g("Pop25t29E")
    a30_44 = g("Pop30t34E") + g("Pop35t39E") + g("Pop40t44E")
    a45_59 = g("Pop45t49E") + g("Pop50t54E") + g("Pop55t59E")
    a60p = g("Pop60t64E") + g("Pop65pl1E")
    out["s18_29"] = _safe_div(a18_29, out["pop18"])
    out["s30_44"] = _safe_div(a30_44, out["pop18"])
    out["s45_59"] = _safe_div(a45_59, out["pop18"])
    out["s60p"] = _safe_div(a60p, out["pop18"])
    out["s_female"] = _safe_div((g("FemE") - g("PopU18FE")).clip(lower=0.0), out["pop18"])
    out["s_white"] = _safe_div(g("WtNHE"), out["pop_total"])
    out["s_black"] = _safe_div(g("BlNHE"), out["pop_total"])
    out["s_hisp"] = _safe_div(g("Hsp1E"), out["pop_total"])
    out["s_other"] = _safe_div((g("Pop_1E") - g("WtNHE") - g("BlNHE") - g("Hsp1E")).clip(lower=0.0), out["pop_total"])
    adequate = g("Pv200t299E") + g("Pv300t399E") + g("Pv400t499E") + g("Pv500plE")
    out["s_adequate"] = _safe_div(adequate, g("PopPvU2E"))
    out["h_kid"] = _safe_div(g("FamChU18E"), g("HH1E"))
    kids = g("OChU6E") + g("OCh6t17E")
    out["h_pre"] = out["h_kid"] * _safe_div(g("OChU6E"), kids)
    out["h_school"] = out["h_kid"] * _safe_div(g("OCh6t17E"), kids)
    out["s_alone"] = _safe_div(g("NFamAE"), g("HH1E"))
    out["s_student"] = _safe_div(g("SE_ClgGScE"), out["pop18"])
    out["s_snap"] = _safe_div(g("Inc_SNAPE"), g("HH2E"))
    out["gq_share"] = _safe_div((g("Pop_1E") - g("HHPopE")).clip(lower=0.0), out["pop_total"])
    return out


def literature_multipliers(shares: pd.DataFrame, food_insecurity: bool = False,
                           student_cap: Optional[float] = None, gq_correction: bool = False,
                           rr_age: Dict[str, float] = RR_AGE, rr_eth: Dict[str, float] = RR_ETH,
                           rr_bin: Dict[str, float] = RR_BIN, rr_kid: Dict[str, float] = RR_KID,
                           rr_fi: Dict[str, float] = RR_FI) -> pd.DataFrame:
    """Per-adult multipliers ``M_age .. M_stu`` (``M_fi`` optional), ``M_total`` and
    ``w_z = pop18 x M_total`` from a shares table (:func:`acs_shares`) -- the R2.4
    formula with the literature rate ratios (literature_demand_model.md section 5.1).

    ``food_insecurity=True`` switches ``M_FI = 1 + 0.38 s_snap`` ON (R2.4 default
    OFF, sensitivity only); ``student_cap`` (e.g. 1.10) caps ``M_stu`` for dormitory
    zones (literature note on group quarters; default no cap).  Zones with
    ``pop18 == 0`` get neutral multipliers (1.0) and ``w_z = 0``.

    Group-quarters correction (literature_demand_model.md section 5.1, "group-quarters correction";
    units review F4): with ``gq_correction=True`` the population base is the
    non-group-quarters adult population ``N_z = pop18 x (1 - gq_share)`` (``gq_share =
    (Pop_1E - HHPopE) / Pop_1E``, the ACS household-population complement that stands
    in for B26001 at NTA level); the default ``False`` keeps ``N_z = pop18`` so that
    dormitory / institutional residents count as potential customers.  The column
    ``N_z`` records the base actually used.  The cap alternative of the note is moot
    on the Manhattan tables (max ``M_stu`` = 1.08 < 1.10 across all NTAs).
    """
    df = shares.copy()
    pos = df["pop18"] > 0
    df["M_age"] = sum(rr_age[k] * df[k] for k in rr_age)
    df["M_eth"] = sum(rr_eth[k] * df[k] for k in rr_eth)
    df["M_sex"] = 1.0 + (rr_bin["s_female"] - 1.0) * df["s_female"]
    df["M_inc"] = 1.0 + (rr_bin["s_adequate"] - 1.0) * df["s_adequate"]
    df["M_kid"] = 1.0 + (rr_kid["h_pre"] - 1.0) * df["h_pre"] + (rr_kid["h_school"] - 1.0) * df["h_school"]
    df["M_alone"] = 1.0 + (rr_bin["s_alone"] - 1.0) * df["s_alone"]
    df["M_stu"] = 1.0 + (rr_bin["s_student"] - 1.0) * df["s_student"]
    if student_cap is not None:
        df["M_stu"] = df["M_stu"].clip(upper=float(student_cap))
    df["M_fi"] = (1.0 + (rr_fi["s_snap"] - 1.0) * df["s_snap"]) if food_insecurity else 1.0
    for c in MULTIPLIER_COLUMNS[:-1]:
        df.loc[~pos, c] = 1.0
    df["M_total"] = df["M_age"] * df["M_eth"] * df["M_sex"] * df["M_inc"] * df["M_kid"] * df["M_alone"] * df["M_stu"] * df["M_fi"]
    if gq_correction:
        df["N_z"] = (df["pop18"] * (1.0 - df["gq_share"].clip(lower=0.0, upper=1.0))).where(pos, 0.0)
    else:
        df["N_z"] = df["pop18"].where(pos, 0.0)
    df["w_z"] = (df["N_z"] * df["M_total"]).where(pos, 0.0)
    df["food_insecurity_on"] = bool(food_insecurity)
    df["gq_correction_on"] = bool(gq_correction)
    return df


def compute_zone_weights(raw: pd.DataFrame, food_insecurity: bool = False,
                         student_cap: Optional[float] = None, gq_correction: bool = False) -> pd.DataFrame:
    """:func:`acs_shares` followed by :func:`literature_multipliers`: raw ACS estimate
    columns -> shares, multipliers, ``w_z`` and ``pi_z = w_z / sum w_z`` over the rows
    given (R2.4 weight formula end to end)."""
    df = literature_multipliers(acs_shares(raw), food_insecurity=food_insecurity, student_cap=student_cap,
                                gq_correction=gq_correction)
    total = float(df["w_z"].sum())
    df["pi_z"] = df["w_z"] / total if total > 0 else 0.0
    return df


# ---------------------------------------------------------------------------
# 3. ZoneWeights implementation
# ---------------------------------------------------------------------------
class ACSZoneWeights:
    """R2.4 zone weights: literature formula on ACS 2020-24 NTA-2020 tables, with the
    GeoDa fallback of ``data_nyc`` when the tables are unusable.

    Implements the :class:`~ebike_swap_sim.data_nyc.ZoneWeights` protocol
    (``weight_at(lat, lon)`` density in km^-2, ``zones()``) plus ``zone_at``,
    ``zone_total(code)`` (= ``w_z``), ``info(code)``, ``table()``.  Attributes read
    by ``make_nyc_instance`` for the instance meta: ``source``
    (:data:`ACS_SOURCE` or ``'geoda_fallback'``), ``warning`` (``None`` when the
    formula is used, else the loud fallback text), ``vintage`` (``'NTA2020'`` /
    ``'NTA2010'``), ``fallback`` (the wrapped :class:`GeoDaZoneWeights` or ``None``).

    ``box`` restricts the polygons to NTAs whose bounding box intersects it (speed
    and ``zones()``); ``food_insecurity`` / ``student_cap`` / ``gq_correction`` are
    forwarded to :func:`literature_multipliers` (all OFF by default: ``N_z = pop18``
    including group-quarters residents, no student cap -- the note's group-quarters
    correction is an available option, not the default).  ``acs_table`` / ``geojson`` inject in-memory
    inputs (tests); ``fallback='auto'`` falls back on any load error, ``'never'``
    re-raises it, ``'force'`` uses the GeoDa fallback regardless.
    """

    def __init__(self, paths: Optional[Dict[str, str]] = None, box: Optional[StudyBox] = None,
                 food_insecurity: bool = False, student_cap: Optional[float] = None,
                 gq_correction: bool = False,
                 acs_table: Optional[pd.DataFrame] = None,
                 geojson: Union[None, str, Dict[str, Any]] = None,
                 fallback: str = "auto", warn: bool = True) -> None:
        if fallback not in ("auto", "never", "force"):
            raise ValueError("fallback must be 'auto', 'never' or 'force'")
        self.paths = dict(ACS_PATHS, **(paths or {}))
        self.box = box
        self.food_insecurity = bool(food_insecurity)
        self.student_cap = student_cap
        self.gq_correction = bool(gq_correction)
        self.fallback: Optional[GeoDaZoneWeights] = None
        self.warning: Optional[str] = None
        self.source = ACS_SOURCE
        self.vintage = "NTA2020"
        self.vintage_note = NTA_VINTAGE_NOTE
        self._features: List[Dict[str, Any]] = []
        self._by_code: Dict[str, Dict[str, Any]] = {}
        self._table: Optional[pd.DataFrame] = None
        error: Optional[str] = None
        if fallback == "force":
            error = "fallback forced by caller"
        else:
            try:
                self._build(acs_table, geojson)
            except Exception as exc:  # noqa: BLE001 - any load / column problem triggers the R2.4 fallback
                if fallback == "never":
                    raise
                error = f"{type(exc).__name__}: {exc}"
        if error is not None:
            self._activate_fallback(error, warn)

    # -- construction -------------------------------------------------------
    def _build(self, acs_table: Optional[pd.DataFrame], geojson: Union[None, str, Dict[str, Any]]) -> None:
        raw = acs_table if acs_table is not None else load_acs_tables(self.paths)
        if isinstance(geojson, dict):
            gj = geojson
        else:
            gj = load_nta2020(geojson or self.paths["nta2020"])
        if "GeoID" not in raw.columns:
            raise KeyError("ACS table needs a GeoID column")
        wt = compute_zone_weights(raw, food_insecurity=self.food_insecurity, student_cap=self.student_cap,
                                  gq_correction=self.gq_correction)
        wt = wt.set_index("GeoID", drop=False)
        box = self.box
        feats: List[Dict[str, Any]] = []
        for feat in gj["features"]:
            geom = feat.get("geometry")
            props = feat.get("properties", {})
            code = props.get("nta2020") or props.get("GeoID") or props.get("ntacode")
            if geom is None or code is None:
                continue
            code = str(code)
            bbox = _geometry_bbox(geom)
            if box is not None and (bbox[2] < box.lon_min or bbox[0] > box.lon_max
                                    or bbox[3] < box.lat_min or bbox[1] > box.lat_max):
                continue
            area = polygon_area_km2(geom)
            if code in wt.index:
                row = wt.loc[code]
                w_total = float(row["w_z"])
                attrs = {k: (float(row[k]) if k not in _ID_COLUMNS else row[k])
                         for k in wt.columns if k in ("pop_total", "pop18", "N_z") or k in SHARE_COLUMNS
                         or k in MULTIPLIER_COLUMNS or k == "NTAType"}
                matched = True
            else:  # polygon without an ACS row: weight 0, reported
                w_total, attrs, matched = 0.0, {}, False
            feats.append({
                "code": code, "name": str(props.get("ntaname", "")), "boro": str(props.get("boroname", "")),
                "ntatype": int(props.get("ntatype", attrs.get("NTAType", -1)) or 0),
                "geometry": geom, "bbox": bbox, "area_km2": area, "w_total": w_total,
                "density": (w_total / area) if area > 0 else 0.0, "acs_matched": matched, **attrs,
            })
        if not feats:
            raise ValueError("no NTA-2020 polygon intersects the study box")
        unmatched = [f["code"] for f in feats if not f["acs_matched"]]
        if len(unmatched) > 0.2 * len(feats):
            raise ValueError(f"{len(unmatched)} of {len(feats)} polygons have no ACS row (vintage mismatch?)")
        feats.sort(key=lambda f: f["code"])
        self._features = feats
        self._by_code = {f["code"]: f for f in feats}
        self._table = wt.reset_index(drop=True)

    def _activate_fallback(self, error: str, warn: bool) -> None:
        self.fallback = GeoDaZoneWeights(self.paths.get("nta_geojson", DEFAULT_PATHS["nta_geojson"]),
                                         box=self.box, warn=False)
        self.source = self.fallback.source  # 'geoda_fallback'
        self.vintage = "NTA2010"
        self.warning = ACS_FALLBACK_WARNING + f"Reason: {error}. " + GEODA_FALLBACK_WARNING
        if warn:
            warnings.warn(self.warning, UserWarning, stacklevel=3)

    # -- ZoneWeights interface ---------------------------------------------
    @property
    def is_fallback(self) -> bool:
        return self.fallback is not None

    def _find(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        for f in self._features:
            b = f["bbox"]
            if b[0] <= lon <= b[2] and b[1] <= lat <= b[3] and point_in_geometry(lon, lat, f["geometry"]):
                return f
        return None

    def zone_at(self, lat: float, lon: float) -> Optional[str]:
        """NTA code containing the point (NTA-2020, or NTA-2010 in fallback); ``None`` outside."""
        if self.fallback is not None:
            return self.fallback.zone_at(lat, lon)
        f = self._find(lat, lon)
        return f["code"] if f else None

    def weight_at(self, lat: float, lon: float) -> float:
        """Weight density ``w_z / area_z`` (km^-2) of the zone containing the point; 0 outside
        every zone and in zero-population (park / airport) zones (R2.4 interface)."""
        if self.fallback is not None:
            return self.fallback.weight_at(lat, lon)
        f = self._find(lat, lon)
        return float(f["density"]) if f else 0.0

    def zones(self) -> List[str]:
        """Sorted zone codes known to this object (intersecting ``box`` when given)."""
        if self.fallback is not None:
            return self.fallback.zones()
        return [f["code"] for f in self._features]

    def zone_total(self, code: str) -> float:
        """Whole-zone weight ``w_z = N_z x M_total`` (not per area)."""
        if self.fallback is not None:
            return self.fallback.zone_total(code)
        return float(self._by_code[code]["w_total"])

    def info(self, code: str) -> Dict[str, Any]:
        """Population, shares, multipliers, ``w_z``, area and density of one zone."""
        if self.fallback is not None:
            return self.fallback.info(code)
        f = self._by_code[code]
        return {k: v for k, v in f.items() if k not in ("geometry", "bbox")}

    def table(self) -> pd.DataFrame:
        """One row per known zone (``zones()``) with every field of :meth:`info`."""
        if self.fallback is not None:
            return self.fallback.table()
        return pd.DataFrame([self.info(c) for c in self.zones()])

    def meta(self) -> Dict[str, Any]:
        """Entries for the instance ``meta`` (source, warning, vintage, formula switches)."""
        return {"zone_weights_source": self.source, "zone_weights_warning": self.warning,
                "zone_weights_vintage": self.vintage, "zone_weights_vintage_note": self.vintage_note,
                "zone_weights_food_insecurity": self.food_insecurity,
                "zone_weights_student_cap": self.student_cap,
                "zone_weights_gq_correction": self.gq_correction,
                "zone_weights_n_zones": len(self.zones())}


# ---------------------------------------------------------------------------
# 4. reporting: table + files under notes/data
# ---------------------------------------------------------------------------
_TABLE_COLUMNS = ["ntacode", "name", "boro", "ntatype", "in_box", "area_km2", "pop_total", "pop18"] + \
    list(SHARE_COLUMNS) + list(MULTIPLIER_COLUMNS) + ["w_z", "density_km2", "share_box", "share_all"]


def weights_table(box: Optional[StudyBox] = DEFAULT_BOX, zw: Optional[ACSZoneWeights] = None,
                  borough: Optional[str] = "Manhattan", **kwargs: Any) -> pd.DataFrame:
    """Per-NTA report of the R2.4 literature weights: ``ntacode, name, boro, ntatype,
    in_box, area_km2, pop_total, pop18``, every share, every multiplier (``M_age ..
    M_total``), ``w_z``, ``density_km2``, ``share_box`` (``pi_z`` among the zones
    intersecting ``box``; 0 for the others) and ``share_all`` (``pi_z`` over all rows).

    Rows: all NTA-2020 zones of ``borough`` (``None`` = whole city) sorted by ``w_z``
    descending; ``in_box`` marks the zones whose polygon bounding box intersects
    ``box``.  ``zw`` may be a prebuilt city-wide :class:`ACSZoneWeights` (``box=None``);
    ``kwargs`` go to its constructor.  Raises ``RuntimeError`` in fallback mode
    (the report is only meaningful for the formula)."""
    zw = zw if zw is not None else ACSZoneWeights(box=None, **kwargs)
    if zw.is_fallback:
        raise RuntimeError("weights_table needs the ACS formula path; fallback active: " + str(zw.warning))
    rows = []
    box_codes = set(ACSZoneWeights(box=box, paths=zw.paths, food_insecurity=zw.food_insecurity,
                                   student_cap=zw.student_cap, warn=False).zones()) if box is not None else set()
    for code in zw.zones():
        f = zw.info(code)
        if borough is not None and f["boro"] != borough:
            continue
        rows.append({"ntacode": code, "name": f["name"], "boro": f["boro"], "ntatype": f["ntatype"],
                     "in_box": code in box_codes, "area_km2": f["area_km2"],
                     "pop_total": f.get("pop_total", 0.0), "pop18": f.get("pop18", 0.0),
                     **{k: f.get(k, 0.0) for k in SHARE_COLUMNS},
                     **{k: f.get(k, 1.0) for k in MULTIPLIER_COLUMNS},
                     "w_z": f["w_total"], "density_km2": f["density"]})
    df = pd.DataFrame(rows)
    tot_all = float(df["w_z"].sum())
    tot_box = float(df.loc[df["in_box"], "w_z"].sum())
    df["share_all"] = df["w_z"] / tot_all if tot_all > 0 else 0.0
    df["share_box"] = np.where(df["in_box"], df["w_z"] / tot_box if tot_box > 0 else 0.0, 0.0)
    df = df.sort_values(["w_z", "ntacode"], ascending=[False, True]).reset_index(drop=True)
    return df[_TABLE_COLUMNS]


def _fmt_rows(df: pd.DataFrame) -> str:
    lines = ["| NTA | name | pop18 | s18_29 | s60p | M_age | M_total | w_z | share_box |", "|---|---|---|---|---|---|---|---|---|"]
    for _, r in df.iterrows():
        lines.append(f"| {r['ntacode']} | {r['name']} | {int(r['pop18'])} | {r['s18_29']:.3f} | {r['s60p']:.3f} | "
                     f"{r['M_age']:.3f} | {r['M_total']:.3f} | {r['w_z']:.0f} | {r['share_box']:.4f} |")
    return "\n".join(lines)


def write_zone_weights(box: StudyBox = DEFAULT_BOX, csv_path: str = ZONE_WEIGHTS_CSV,
                       readme_path: str = ZONE_WEIGHTS_README, **kwargs: Any) -> pd.DataFrame:
    """Write ``notes/data/zone_weights_manhattan.csv`` (all Manhattan NTA-2020 zones,
    :func:`weights_table` with ``in_box`` for the default study box) and the bilingual
    ``zone_weights_README.md`` explaining the numbers (R2.4 deliverable).  Returns the table."""
    df = weights_table(box=box, borough="Manhattan", **kwargs)
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    df.to_csv(csv_path, index=False, float_format="%.6g")
    res = df[(df["ntatype"] == 0) & (df["pop18"] > 0)].copy()
    by_m = res.sort_values("M_total", ascending=False)
    top5, bot5 = by_m.head(5), by_m.tail(5).iloc[::-1]
    inbox = df[df["in_box"]].sort_values("share_box", ascending=False)
    rr_lines = "\n".join(f"- `{k}`: {v}" for k, v in SHARE_DERIVATIONS.items())
    text = f"""# Zone weights for the semi-real NYC instance

Generated by `python -m ebike_swap_sim.acs_weights` (module `ebike_swap_sim/acs_weights.py`).
Source data: DCP ACS 2020-2024 5-year profiles by NTA-2020 (`data/raw/acs/{{Dem,Soc,Econ}}_2024ACS5YR_NTA.xlsx`)
and the NTA-2020 polygons `data/raw/acs/nta2020.geojson` (MANIFEST section 5). Rule: DECISIONS.md R2.4 "Zone weights",
formula from `notes/literature_demand_model.md` section 5.1.

## Summary

**What the numbers are.** `zone_weights_manhattan.csv` has one row per Manhattan NTA-2020 zone (including zones without
population such as parks, weight 0). `w_z = N_z x M_age x M_eth x M_sex x M_inc x M_kid x M_alone x M_stu` is the zone's
**relative expected order volume**: `N_z = pop18` is the population aged 18+ (ACS estimate), and each `M_*` is a literature
multiplier for the "relative propensity per adult to order delivery" (Bennett 2025 participation odds ratios and
Buettner 2023 frequency rate ratios, literature_demand_model.md section 5). `M_total` is the product of the multipliers
(per-adult factor), `density_km2 = w_z / area` is the density the sampler actually uses (`NYCDestinationSampler` assigns
every 150 m grid node the density of the zone containing it, so points are uniform inside a zone and the between-zone
proportions are pi_z). `share_box` is pi_z inside the default study box (lat 40.735-40.770, lon -74.005 to -73.965; the
{int(df['in_box'].sum())} zones with `in_box = True`), `share_all` is pi_z over all of Manhattan.

**Age is the main factor.** Rate ratios 3.4/3.0/1.9/1.0 (18-29/30-44/45-59/60+) mean that a zone with 40 % young adults
has a per-adult factor of about 2.7, whereas a zone where 60+ residents are one third has about 2.1; the other factors are
each within +/-10-30 %. `M_FI` (SNAP, 1.38) is OFF by default (R2.4).

**Version note.** The ACS tables are NTA-2020 (262 zones, codes like `MN0501`), the GeoDa fallback polygons are NTA-2010
(195 zones, `MN17`); the two code systems do not correspond, so this module uses the NTA-2020 polygons directly for the
point-in-polygon tests and performs no code crosswalk; only when the ACS files are missing / unusable does it fall back to
the GeoDa fallback formula (`meta['zone_weights_source'] = 'geoda_fallback'` with a warning). This run used the
**ACS formula** (`source = {ACS_SOURCE}`).

**Column-to-share derivations.** See the list below (each share states which DCP columns it uses). Note on the children
term: the B11003 age breakdown (<6 / 6-17) is not published at NTA level, only the count of "family households with
children under 18" `FamChU18E`; the DP03 child counts `OChU6E : OCh6t17E` are therefore used to split that household share
into pre-school / school-age parts (declared approximation).

## Details

**What the numbers are.** One row per Manhattan NTA-2020 zone (park / special zones have population 0 and weight 0).
`w_z = N_z x M_age x M_eth x M_sex x M_inc x M_kid x M_alone x M_stu` is the zone's *relative expected order volume*:
`N_z = pop18` (ACS estimate of residents 18+) times the literature per-adult multipliers (Bennett 2025 participation
odds ratios and Buettner 2023 frequency rate ratios, literature_demand_model.md section 5). `M_total` is the product of
the multipliers (orders per adult relative to a 60+ / NH-white / male / low-income / childless / co-living / non-student
reference adult), `density_km2 = w_z / area` is what the sampler uses (uniform inside a zone, pi_z between zones),
`share_box` is pi_z inside the default study box ({int(df['in_box'].sum())} zones with `in_box = True`) and `share_all` is pi_z over all of Manhattan.
`M_FI` (SNAP, 1.38) is OFF by default (R2.4). Zone codes are NTA-2020; the GeoDa NTA-2010 codes (`MN17`) are a
different system and are not mapped (the fallback is used only when the ACS files are unusable).

**Column -> share derivations** (all `*E` columns are ACS estimates; MANIFEST section 5 validation: age bands sum to
pop 18+, race / Hispanic groups sum to total population, poverty bands sum to `PopPvU2E`):
{rr_lines}

Rate ratios: age {RR_AGE}; ethnicity {RR_ETH}; binary {RR_BIN}; children {RR_KID}; optional SNAP {RR_FI}.

## Sanity check: per-adult multiplier `M_total`, residential Manhattan NTAs

Top 5 (young / single / adequate-income zones should rank high):

{_fmt_rows(top5)}

Bottom 5 (60+ heavy zones, e.g. Upper East Side, should rank low):

{_fmt_rows(bot5)}

Zones in the default study box by `share_box`:

{_fmt_rows(inbox)}

Caveat (R2.4 geometry): these weights are placed on the synthetic 150 m GridNetwork; no real road network is used.
"""
    with open(readme_path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return df


if __name__ == "__main__":  # pragma: no cover
    table = write_zone_weights()
    print(f"wrote {ZONE_WEIGHTS_CSV} ({len(table)} rows) and {ZONE_WEIGHTS_README}")
    res = table[(table["ntatype"] == 0) & (table["pop18"] > 0)].sort_values("M_total", ascending=False)
    print(res[["ntacode", "name", "pop18", "s18_29", "s60p", "M_age", "M_total", "w_z", "in_box"]].head(5).to_string())
    print(res[["ntacode", "name", "pop18", "s18_29", "s60p", "M_age", "M_total", "w_z", "in_box"]].tail(5).to_string())
