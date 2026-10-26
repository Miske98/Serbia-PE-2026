"""Data loading, results import and analysis functions for the Serbia 2026 polling-station explorer.

Everything here is plain pandas/numpy so it can be reused by the report script.
"""
from __future__ import annotations

import glob
import os
import re
import unicodedata

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

# ---------------------------------------------------------------- sources
SOURCES = {
    "register": ("Republic Electoral Commission, Decision on the final number of voters, 02 no. 013-863/26, 23 Oct 2026, "
                 "annex by polling station (6,451,292 voters); station names and addresses from the Ministry of Public Administration and "
                 "Local Self-Government decision closing the Unified Voter Register, 9 Oct 2026, Annex 1"),
    "geocode": ("Polling-station coordinates: izbori26.com geocodes, compiled in github.com/majstors/datasets-parlamentarni-izbori2026 "
                "(downloaded 23 Oct 2026; unofficial, automatic geocoding). Matched to the official list by address; "
                "unmatched stations placed at settlement or municipality centre"),
    "abroad_geo": "Stations abroad: city-centre coordinates entered manually from the addresses in Annex 1",
    "boundaries": "Municipal boundaries: geoBoundaries ADM2 Serbia and ADM0 Kosovo (CC BY 4.0)",
    "results": "Republic Electoral Commission (RIK), results by polling station (preliminary, processed stations only; files in data/results/); list names from RIK's collective electoral list as reported by Mašina, 2026",
    "baseline": "RIK results by polling station, 17 Dec 2023 parliamentary election, as processed by podatak.rs (CC BY 4.0, 'Izvor: RIK, obrada podatak.rs')",
    "gap": ("Misic, 'Serbia Voter Register Gap 2026': RZS Census 2022 cohort minus deaths to 5 Oct 2026 plus citizens abroad, "
            "compared with the UVR of 5 Oct 2026"),
    "kim_series": "Closed register for Kosovo and Metohija at past elections: OSCE/ODIHR and RIK via RFE, N1, Novosti, KoSSev (Misic, 'Kosovo Register and Population')",
}


def src(*keys: str) -> str:
    return "Source: " + "; ".join(SOURCES[k] for k in keys) + "."


# ---------------------------------------------------------------- text normalisation
_CYR = dict(zip("АБВГДЂЕЖЗИЈКЛЉМНЊОПРСТЋУФХЦЧЏШ",
                ["A", "B", "V", "G", "D", "DJ", "E", "Z", "Z", "I", "J", "K", "L", "LJ", "M", "N", "NJ", "O", "P", "R", "S",
                 "T", "C", "U", "F", "H", "C", "C", "DZ", "S"]))


def ascii_key(s) -> str:
    """Upper-case ASCII key: Cyrillic and Latin spellings of the same name give the same key."""
    s = str(s).upper()
    s = "".join(_CYR.get(c, c) for c in s)
    s = s.replace("Đ", "DJ").replace("DŽ", "DZ")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z0-9]+", " ", s).strip()


def unit_key(s) -> str:
    k = ascii_key(s)
    k = re.sub(r"\bGRAD\b$", "", k).strip()
    k = re.sub(r"^GRAD\b", "", k).strip()
    k = re.sub(r"\bGRADSKA OPSTINA\b|\bOPSTINA\b", "", k).strip()
    if "INOSTRAN" in k or k == "ABROAD":
        return "ABROAD"
    if "ZAVOD" in k or "PRISON" in k or "ZATVOR" in k:
        return "PRISONS"
    return re.sub(r"\s+", " ", k)


# ---------------------------------------------------------------- stations
def load_stations() -> pd.DataFrame:
    st = pd.read_csv(os.path.join(DATA, "stations.csv"), dtype={"mun_code": str, "station_id": str})
    st["ukey"] = st["unit"].map(unit_key)
    st["precise"] = st["geo_precision"].isin(["building", "street", "settlement", "approx"])
    return st


# ---------------------------------------------------------------- results import
FIELDS = {
    "station_id": ["station id"],
    "unit": ["opstina", "jedinica lokalne samouprave", "municipality", "opstina grad", "grad opstina", "jls", "unit", "lsg"],
    "ps_no": ["broj birackog mesta", "birackog mesta broj", "biracko mesto broj", "bm broj", "broj bm", "polling station number",
              "ps no", "station number", "redni broj birackog mesta"],
    "ps_label": ["biracko mesto", "naziv birackog mesta", "polling station", "naziv"],
    "registered": ["broj upisanih biraca", "upisanih biraca", "ukupan broj biraca", "broj biraca u birackom spisku",
                   "biraca u birackom spisku", "registered voters", "registered", "upisani", "upisano"],
    "voted": ["broj biraca koji su glasali", "biraca koji su glasali", "glasali biraci", "glasalo", "izaslo", "izaslih", "voted", "turnout count",
              "ukupno glasalo"],
    "ballots_received": ["primljenih glasackih listica", "broj primljenih", "ballots received"],
    "ballots_unused": ["neupotrebljenih", "neupotrebljeni", "unused ballots"],
    "ballots_in_box": ["glasackih listica u glasackoj kutiji", "listica u kutiji", "listici u kutiji", "ballots in box"],
    "minutes": ["zapisnik link", "zapisnik"],
    "invalid": ["nevazecih", "nevazeci", "invalid"],
    "valid": ["vazecih", "vazeci", "valid"],
}
# order matters: 'nevazeci' must be tested before 'vazeci'
FIELD_ORDER = ["minutes", "station_id", "ps_no", "unit", "registered", "voted", "ballots_received", "ballots_unused", "ballots_in_box",
               "invalid", "valid", "ps_label"]


def _match_field(col: str) -> str | None:
    k = ascii_key(col).lower()
    for f in FIELD_ORDER:
        for syn in FIELDS[f]:
            if syn in k:
                if f == "valid" and "nevaz" in k:
                    continue
                return f
    return None


def _read_any(path: str) -> list[pd.DataFrame]:
    if path.lower().endswith((".xlsx", ".xls")):
        sheets = pd.read_excel(path, sheet_name=None, header=None)
        return [_promote_header(d) for d in sheets.values()]
    for sep in [",", ";", "\t"]:
        try:
            d = pd.read_csv(path, sep=sep, header=None, dtype=str, encoding="utf-8-sig")
            if d.shape[1] > 3:
                return [_promote_header(d)]
        except Exception:
            continue
    return []


def _promote_header(raw: pd.DataFrame) -> pd.DataFrame:
    """Find the header row (first row with >=3 recognised field names) and use it."""
    raw = raw.dropna(how="all").reset_index(drop=True)
    for i in range(min(15, len(raw))):
        row = [str(x) for x in raw.iloc[i].tolist()]
        if sum(_match_field(x) is not None for x in row if x and x != "nan") >= 3:
            d = raw.iloc[i + 1:].copy()
            d.columns = [str(c).strip() for c in row]
            return d.reset_index(drop=True)
    d = raw.iloc[1:].copy()
    d.columns = [str(c).strip() for c in raw.iloc[0]]
    return d


def _num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype(str).str.replace(r"[\s\xa0.]", "", regex=True).str.replace(",", ".", regex=False)
                         .replace({"": None, "nan": None, "-": None}), errors="coerce")


def _standardise(d: pd.DataFrame, fname: str) -> tuple[pd.DataFrame, dict]:
    mapping, lists = {}, []
    for c in d.columns:
        f = _match_field(c)
        if f and f not in mapping.values():
            mapping[c] = f
    # long format: one row per list
    k = {c: ascii_key(c).lower() for c in d.columns}
    list_name_col = next((c for c in d.columns if k[c] in ("lista", "izborna lista", "naziv liste", "list", "electoral list")), None)
    votes_col = next((c for c in d.columns if k[c] in ("glasova", "broj glasova", "votes", "glasovi", "osvojeno glasova")), None)
    out = d.rename(columns=mapping)
    if list_name_col is not None and votes_col is not None:
        idx = [f for f in ["station_id", "unit", "ps_no", "registered", "voted", "invalid", "valid",
                           "ballots_received", "ballots_unused", "ballots_in_box"] if f in out.columns]
        out[votes_col] = _num(out[votes_col])
        wide = out.pivot_table(index=idx, columns=list_name_col, values=votes_col, aggfunc="sum").reset_index()
        lists = [c for c in wide.columns if c not in idx]
        wide.columns = [("L: " + str(c)) if c in lists else c for c in wide.columns]
        out = wide
        lists = ["L: " + str(c) for c in lists]
    else:
        for c in d.columns:
            if c in mapping:
                continue
            v = _num(d[c])
            if v.notna().mean() > 0.8 and not re.fullmatch(r"(?i)(r\.?\s*br\.?|redni broj|rb|id|sifra.*|code|izlaznost|turnout|maticni.*|region|bm uid|uid|sifra.*|vreme.*|korekcija.*)", ascii_key(c).lower()):
                newc = "L: " + re.sub(r"\s+", " ", str(c)).strip()
                out = out.rename(columns={c: newc})
                lists.append(newc)
    for f in ["ps_no", "registered", "voted", "invalid", "valid", "ballots_received", "ballots_unused", "ballots_in_box"] + lists:
        if f in out.columns:
            out[f] = _num(out[f])
    names_f = os.path.join(os.path.dirname(fname), "list_names.csv")
    if os.path.exists(names_f):
        nm = pd.read_csv(names_f)
        ren = {}
        for c in lists:
            hit = nm[nm["column"].str.lower() == c[3:].strip().lower()]
            if len(hit):
                ren[c] = "L: " + str(hit.iloc[0]["short_name"])
        out = out.rename(columns=ren); lists = [ren.get(c, c) for c in lists]
    lists = [c for c in lists if out[c].fillna(0).sum() > 0]
    out = out.drop(columns=[c for c in out.columns if str(c).startswith("L: ") and c not in lists])
    if "voted" in out.columns:  # stations not yet processed are delivered as zeros
        lv = out[lists].fillna(0).sum(axis=1) if lists else 0
        pending = (out["voted"].fillna(0) == 0) & (lv == 0)
        out.loc[pending, "voted"] = np.nan
    if "minutes" in out.columns:
        out["minutes"] = out["minutes"].astype(str).str.extract(r"(https?://\S+)")[0]
    out["source_file"] = os.path.basename(fname)
    info = {"file": os.path.basename(fname), "mapped": {v: k for k, v in mapping.items()}, "lists": lists, "rows": len(out)}
    return out, info


def _attach(res: pd.DataFrame, st: pd.DataFrame) -> pd.DataFrame:
    if "station_id" in res.columns and res["station_id"].notna().any():
        res["station_id"] = res["station_id"].astype(str)
        return res
    if "ps_no" not in res.columns and "ps_label" in res.columns:  # e.g. "12 - OŠ ..."
        res["ps_no"] = pd.to_numeric(res["ps_label"].astype(str).str.extract(r"^\s*(\d+)")[0], errors="coerce")
    res["ukey"] = align_units(res["unit"].map(unit_key), st) if "unit" in res.columns else None
    lut = st.set_index(["ukey", "ps_no"])["station_id"]
    alias = {}
    for u in st["ukey"].unique():  # 'BEOGRAD ZEMUN' also reachable as 'ZEMUN'
        parts = u.split(" ", 1)
        if parts[0] in ("BEOGRAD", "NIS", "VRANJE", "UZICE", "POZAREVAC") and len(parts) == 2:
            alias.setdefault(parts[1], u)
    sub_units = {}
    for k2 in st["ukey"].unique():
        if " " in k2:
            sub_units.setdefault(k2.split(" ")[0], []).append(k2)
    ids = []
    for u, n in zip(res["ukey"], res["ps_no"]):
        sid = lut.get((u, n)) if pd.notna(n) else None
        if sid is None and u in alias:
            sid = lut.get((alias[u], n))
        if sid is None and pd.notna(n):  # e.g. Vranjska Banja numbered 93-113 within Vranje
            for k2 in sub_units.get(u, []):
                sid = lut.get((k2, n))
                if sid is not None:
                    break
        ids.append(sid)
    res["station_id"] = ids
    return res


def load_results(folder: str | None = None) -> tuple[pd.DataFrame, list[dict], pd.DataFrame]:
    """Read every CSV/XLSX in the folder. Later files (by name) override earlier ones for the same station."""
    folder = folder or os.path.join(DATA, "results")
    st = load_stations()
    frames, infos = [], []
    for f in sorted(glob.glob(os.path.join(folder, "*"))):
        if not f.lower().endswith((".csv", ".xlsx", ".xls")) or os.path.basename(f) == "list_names.csv":
            continue
        for d in _read_any(f):
            if d.empty:
                continue
            s, info = _standardise(d, f)
            if not ({"registered", "voted"} <= set(s.columns)):
                info["skipped"] = "no 'registered' and 'voted' columns recognised"
                infos.append(info)
                continue
            s = _attach(s, st)
            info["matched"] = int(s["station_id"].notna().sum())
            frames.append(s)
            infos.append(info)
    if not frames:
        return pd.DataFrame(), infos, pd.DataFrame()
    allr = pd.concat(frames, ignore_index=True)
    unmatched = allr[allr["station_id"].isna()]
    allr = allr[allr["station_id"].notna()].drop_duplicates("station_id", keep="last")
    return allr, infos, unmatched


# ---------------------------------------------------------------- merged analysis table
def build_table(st: pd.DataFrame, res: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    lists = [c for c in res.columns if str(c).startswith("L: ")] if not res.empty else []
    keep = ["station_id", "minutes", "registered", "voted", "invalid", "valid", "ballots_received", "ballots_unused", "ballots_in_box"] + lists
    r = res[[c for c in keep if c in res.columns]].rename(columns={"registered": "registered_result"}) if not res.empty else pd.DataFrame(columns=["station_id"])
    t = st.merge(r, on="station_id", how="left")
    for c in ["voted", "invalid", "valid"]:
        if c not in t:
            t[c] = np.nan
    t["reported"] = t["voted"].notna()
    t["reg"] = t["registered_result"].fillna(t["registered_2026"]) if "registered_result" in t else t["registered_2026"]
    t["turnout"] = t["voted"] / t["reg"]
    if "invalid" in t:
        t["invalid_share"] = t["invalid"] / t["voted"]
    for c in lists:
        t[c] = t[c].fillna(0) if t["reported"].any() else t[c]
        base = t["valid"] if "valid" in t and t["valid"].notna().any() else t[lists].sum(axis=1)
        t["share " + c[3:]] = t[c] / base.replace(0, np.nan)
    return t, lists


def aggregate(t: pd.DataFrame, by: str, lists: list[str]) -> pd.DataFrame:
    cols = {"n_stations": ("station_id", "size"), "n_reported": ("reported", "sum"), "registered_2026": ("registered_2026", "sum")}
    g = t.groupby(by).agg(**cols)
    rep = t[t.reported]
    if len(rep):
        s = rep.groupby(by)[["reg", "voted"] + [c for c in ["invalid", "valid"] + lists if c in rep]].sum()
        g = g.join(s)
        g["turnout"] = g["voted"] / g["reg"]
        if "invalid" in g:
            g["invalid_share"] = g["invalid"] / g["voted"]
        for c in lists:
            g["share " + c[3:]] = g[c] / (g["valid"] if "valid" in g else g[lists].sum(axis=1))
    return g.reset_index()


# ---------------------------------------------------------------- consistency checks
def consistency(t: pd.DataFrame, lists: list[str]) -> pd.DataFrame:
    r = t[t.reported].copy()
    checks = []
    def add(mask, label):
        for sid in r.loc[mask.fillna(False), "station_id"]:
            checks.append((sid, label))
    add(r["voted"] > r["reg"], "More voters recorded as voting than registered")
    if "registered_result" in r:
        add((r["registered_result"] - r["registered_2026"]).abs() > 0, "Registered voters in results differ from RIK final number (23 Oct)")
    if {"valid", "invalid"} <= set(r.columns):
        add((r["valid"] + r["invalid"] - r.get("ballots_in_box", r["voted"])).abs() > 0, "Valid + invalid differs from ballots in box (or voters who voted)")
    if lists and "valid" in r:
        add((r[lists].sum(axis=1) - r["valid"]).abs() > 0, "Sum of list votes differs from valid ballots")
    if {"ballots_received", "ballots_unused"} <= set(r.columns):
        add((r["ballots_received"] - r["ballots_unused"] - r["voted"]).abs() > 0, "Ballots received minus unused differs from voters who voted")
    add(r["turnout"] >= 0.95, "Turnout of 95% or more")
    add((r["voted"] == 0) & (r["reg"] > 0), "Zero voters recorded")
    out = pd.DataFrame(checks, columns=["station_id", "check"])
    return out.merge(t[["station_id", "unit", "ps_no", "name_lat", "address_lat", "reg", "voted", "turnout"]], on="station_id")


# ---------------------------------------------------------------- integer-percentage test (Kobak, Shpilkin & Pshenichnikov 2016)
def integer_percent_test(t: pd.DataFrame, col_num="voted", col_den="reg", sims=2000, min_den=100, seed=1) -> dict:
    r = t[t.reported & (t[col_den] >= min_den) & t[col_num].notna()]
    n, v = r[col_den].astype(int).to_numpy(), r[col_num].astype(int).to_numpy()
    def hits(vv, step):
        pct = 100 * vv / n
        return int(np.sum(np.isclose(pct, np.round(pct / step) * step, atol=1e-9)))
    rng = np.random.default_rng(seed)
    p = np.clip(v / n, 1e-6, 1 - 1e-6)
    out = {"n": len(r)}
    for step in (1, 5):
        obs = hits(v, step)
        sim = np.array([hits(rng.binomial(n, p), step) for _ in range(sims)])
        out[step] = {"observed": obs, "expected": float(sim.mean()), "lo": float(np.percentile(sim, 2.5)),
                     "hi": float(np.percentile(sim, 97.5)), "p_upper": float((sim >= obs).mean())}
    return out


# ---------------------------------------------------------------- last digit test (Beber & Scacco 2012)
def last_digit_test(t: pd.DataFrame, cols: list[str], min_count=100) -> dict:
    from scipy.stats import chisquare
    vals = pd.concat([t.loc[t.reported, c] for c in cols]).dropna()
    vals = vals[vals >= min_count].astype(int)
    if len(vals) < 200:
        return {"n": int(len(vals))}
    obs = np.bincount(vals % 10, minlength=10)
    chi = chisquare(obs)
    return {"n": int(len(vals)), "obs": obs, "chi2": float(chi.statistic), "p": float(chi.pvalue)}


# ---------------------------------------------------------------- spatial neighbours
def _xy(t: pd.DataFrame) -> np.ndarray:
    lat0 = np.deg2rad(44.0)
    return np.c_[np.deg2rad(t["lon"]) * np.cos(lat0) * 6371, np.deg2rad(t["lat"]) * 6371]


def spatial_analysis(t: pd.DataFrame, value="turnout", k=8, perms=999, seed=7) -> pd.DataFrame:
    """Local Moran's I with k-nearest-neighbour weights and conditional permutation p-values (Anselin 1995),
    plus a neighbour-deviation z-score. Only domestic stations with settlement-or-better coordinates."""
    from scipy.spatial import cKDTree
    r = t[t.reported & (t.kind == "domestic") & t.precise & t[value].notna()].reset_index(drop=True)
    if len(r) < 50:
        return pd.DataFrame()
    xy = _xy(r)
    dist, idx = cKDTree(xy).query(xy, k=k + 1)
    idx, dist = idx[:, 1:], dist[:, 1:]
    y = r[value].to_numpy()
    z = (y - y.mean()) / y.std()
    lag = z[idx].mean(axis=1)
    I = z * lag
    rng = np.random.default_rng(seed)
    nobs = len(z)
    larger = np.zeros(nobs)
    for _ in range(perms):
        rnd = rng.integers(0, nobs - 1, size=(nobs, k))
        rnd = rnd + (rnd >= np.arange(nobs)[:, None])  # never draw the station itself
        larger += (z * z[rnd].mean(axis=1)) * np.sign(I) >= np.abs(I)
    p = (larger + 1) / (perms + 1)
    neigh_med = np.median(y[idx], axis=1)
    resid = y - neigh_med
    mad = np.median(np.abs(resid - np.median(resid))) * 1.4826
    q = np.where(z > 0, np.where(lag > 0, "High-High", "High-Low"), np.where(lag > 0, "Low-High", "Low-Low"))
    out = r[["station_id"]].copy()
    out["local_I"], out["p_sim"], out["quadrant"] = I, p, q
    out["neighbour_median"], out["neighbour_dev"], out["neighbour_z"] = neigh_med, resid, resid / mad
    out["neighbour_km"] = dist.mean(axis=1)
    out["cluster"] = np.where(p < 0.01, out["quadrant"], "Not significant")
    return out


def morans_I(t: pd.DataFrame, value="turnout", k=8) -> float | None:
    from scipy.spatial import cKDTree
    r = t[t.reported & (t.kind == "domestic") & t.precise & t[value].notna()]
    if len(r) < 50:
        return None
    xy = _xy(r)
    _, idx = cKDTree(xy).query(xy, k=k + 1)
    z = r[value].to_numpy(); z = z - z.mean()
    return float((z * z[idx[:, 1:]].mean(axis=1)).sum() / (z ** 2).sum())


# ---------------------------------------------------------------- baseline (2023)
def align_units(keys: pd.Series, stns: pd.DataFrame) -> pd.Series:
    """2023 files name Belgrade/Niš city municipalities without the city ('BARAJEVO'); map them to 2026 keys."""
    alias = {}
    for u in stns.ukey.unique():
        parts = u.split(" ", 1)
        if parts[0] in ("BEOGRAD", "NIS", "VRANJE", "UZICE", "POZAREVAC") and len(parts) == 2:
            alias[parts[1]] = u
    alias.update({"PALILULA": "BEOGRAD PALILULA", "PALILULA BEOGRAD": "BEOGRAD PALILULA", "PALILULA NIS": "NIS PALILULA"})
    return keys.map(lambda k: alias.get(k, k))


def match_baseline(stns: pd.DataFrame, base: pd.DataFrame) -> pd.DataFrame:
    """Match 2026 stations to 2023 stations within the same unit: same number and similar name,
    otherwise the same name at another number (if unique). Returns one row per matched 2026 station."""
    from difflib import SequenceMatcher
    if base.empty:
        return pd.DataFrame()
    b = base.copy()
    b["nk"] = b.get("ps_label", pd.Series("", index=b.index)).map(ascii_key)
    s = stns[["station_id", "ukey", "ps_no", "name"]].copy()
    s["nk"] = s["name"].map(ascii_key)
    b["ukey"] = align_units(b["ukey"], stns)
    rows = []
    for u, g26 in s.groupby("ukey"):
        g23 = b[b.ukey == u]
        if g23.empty:
            continue
        by_no = g23.set_index("ps_no", drop=False)
        used = set()
        for r in g26.itertuples():
            how = None
            if r.ps_no in by_no.index and u != "ABROAD":
                c = by_no.loc[[r.ps_no]].iloc[0]
                sim = SequenceMatcher(None, r.nk, c.nk).ratio()
                if sim >= 0.6:
                    how = ("number+name", c, sim)
            if how is None:
                same = g23[(g23.nk == r.nk) & ~g23.ps_no.isin(used)]
                if len(same) == 1:
                    how = ("name only", same.iloc[0], 1.0)
            if how:
                used.add(how[1].ps_no)
                rows.append({"station_id": r.station_id, "ps_no_2023": how[1].ps_no, "name_2023": how[1].get("ps_label"),
                             "registered_2023": how[1].registered, "voted_2023": how[1].voted,
                             "invalid_2023": how[1].get("invalid"), "match": how[0], "name_similarity": how[2],
                             "minutes_2023": how[1].get("zapisnik_url")})
    m = pd.DataFrame(rows)
    if m.empty:
        return m
    m["turnout_2023"] = m.voted_2023 / m.registered_2023
    return m


def load_baseline() -> pd.DataFrame:
    files = sorted(glob.glob(os.path.join(DATA, "baseline", "*.csv")) + glob.glob(os.path.join(DATA, "baseline", "*.xlsx")))
    if not files:
        return pd.DataFrame()
    frames = []
    for f in files:
        for d in _read_any(f):
            s, _ = _standardise(d, f)
            if {"registered", "voted", "unit"} <= set(s.columns):
                s["ukey"] = s["unit"].map(unit_key)
                frames.append(s)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


# ---------------------------------------------------------------- colours
def ramp(values, vmin, vmax, palette="seq"):
    """Return RGB lists. seq: light->dark blue; div: orange-grey-blue."""
    stops = {"seq": [(239, 243, 255), (158, 202, 225), (66, 146, 198), (8, 81, 156), (8, 48, 107)],
             "div": [(179, 88, 6), (241, 163, 64), (235, 235, 235), (153, 142, 195), (84, 39, 136)]}[palette]
    v = np.clip((np.asarray(values, dtype=float) - vmin) / max(vmax - vmin, 1e-9), 0, 1)
    v = np.nan_to_num(v, nan=-1)
    out = []
    for x in v:
        if x < 0:
            out.append([190, 190, 190]); continue
        pos = x * (len(stops) - 1); i = min(int(pos), len(stops) - 2); f = pos - i
        out.append([int(stops[i][j] + (stops[i + 1][j] - stops[i][j]) * f) for j in range(3)])
    return out
