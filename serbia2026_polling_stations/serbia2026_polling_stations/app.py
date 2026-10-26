"""Serbia 2026 parliamentary election: interactive polling-station explorer.

Run locally:  streamlit run app.py
Data: put RIK result files (CSV or XLSX) into data/results/ and reload the page.
The whole interface (map + analysis panel with linked hover) is one HTML component, ui.html.
"""
import json
import os
import re

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import core

st.set_page_config(page_title="Serbia 2026 Polling Stations", page_icon="🗳️", layout="wide",
                   initial_sidebar_state="collapsed")
st.markdown("""<style>
.block-container{padding:2.9rem 0.8rem 0 0.8rem;max-width:100%}
header[data-testid="stHeader"]{height:0;background:transparent}
iframe{border:0}
</style>""", unsafe_allow_html=True)


def stamp(sub):
    p = os.path.join(core.DATA, sub)
    return max([os.path.getmtime(os.path.join(p, f)) for f in os.listdir(p)] + [os.path.getmtime(os.path.join(core.DATA, "stations.csv"))])


def r(x, n=4):
    try:
        if x is None or pd.isna(x) or not np.isfinite(float(x)):
            return None
    except (TypeError, ValueError):
        return None
    return round(float(x), n) if n else int(round(float(x)))


@st.cache_data(show_spinner="Preparing data…")
def build_payload(_stamp: float) -> str:
    stns = core.load_stations()
    res, info, unmatched = core.load_results(os.path.join(core.DATA, "results"))
    T, LISTS = core.build_table(stns, res)
    base = core.load_baseline()
    if not base.empty:
        T = T.merge(core.match_baseline(stns, base), on="station_id", how="left")
        base["ukey"] = core.align_units(base["ukey"], stns)
    for c in ["registered_2023", "turnout_2023", "minutes_2023", "name_2023"]:
        if c not in T:
            T[c] = np.nan
    has_res = bool(T.reported.any())
    sp = core.spatial_analysis(T, "turnout") if has_res else pd.DataFrame()
    if not sp.empty:
        T = T.merge(sp[["station_id", "neighbour_z", "neighbour_median", "neighbour_km"]], on="station_id", how="left")
    else:
        T["neighbour_z"] = np.nan; T["neighbour_median"] = np.nan; T["neighbour_km"] = np.nan

    S = {
        "id": T.station_id.tolist(), "unit": T.unit.tolist(), "lsg": T.lsg.fillna("").tolist(), "kind": T.kind.tolist(),
        "no": T.ps_no.astype(int).tolist(), "name": T.name_lat.fillna("").tolist(), "addr": T.address_lat.fillna("").tolist(),
        "lat": [r(x, 5) for x in T.lat], "lon": [r(x, 5) for x in T.lon], "prec": T.geo_precision.tolist(),
        "host": T.host_town.fillna("").tolist(), "city": T.city.fillna("").tolist(), "country": T.country.fillna("").tolist(),
        "reg": T.registered_2026.astype(int).tolist(), "reg_a1": T.registered_annex1.astype(int).tolist(),
        "reg23": [r(x, 0) for x in T.registered_2023], "t23": [r(x) for x in T.turnout_2023],
        "min23": T.minutes_2023.fillna("").tolist(), "min26": (T["minutes"] if "minutes" in T else pd.Series([""] * len(T))).fillna("").tolist(), "name23": T.name_2023.fillna("").tolist(),
        "voted": [r(x, 0) for x in T.voted], "valid": [r(x, 0) for x in T.valid], "invalid": [r(x, 0) for x in T.invalid],
        "nz": [r(x, 2) for x in T.neighbour_z], "nmed": [r(x) for x in T.neighbour_median], "nkm": [r(x, 1) for x in T.neighbour_km],
        "votes": [[r(x, 0) for x in T[c]] for c in LISTS],
    }
    out = {"stations": S, "lists": [c[3:] for c in LISTS], "has_results": has_res, "demo": False, "sources": core.SOURCES,
           "files": [{"file": i["file"], "rows": i["rows"], "matched": i.get("matched", 0)} for i in info],
           "unmatched": int(len(unmatched))}
    if has_res:
        ip = core.integer_percent_test(T)
        out["integer"] = {str(k): v for k, v in ip.items()}
        out["moran"] = core.morans_I(T)
        out["consistency"] = core.consistency(T, LISTS)[["station_id", "check"]].values.tolist()
    if not base.empty:
        bu = base.groupby("ukey").agg(st23=("ps_no", "size"), reg23=("registered", "sum"), v23=("voted", "sum"))
        now = stns.groupby("ukey").agg(unit=("unit", "first"), kind=("kind", "first"), lsg=("lsg", "first"),
                                       st26=("station_id", "size"), reg26=("registered_2026", "sum"))
        out["units23"] = json.loads(now.join(bu, how="left").reset_index(drop=True).to_json(orient="records"))
    gap = pd.read_csv(os.path.join(core.DATA, "context", "register_gap_lsg.csv"))
    out["gap"] = json.loads(gap[["lsg", "uvr_2026_10_05", "projected_eligible", "unexplained_gap", "unexplained_gap_rel"]].to_json(orient="records"))
    out["kim_series"] = json.loads(pd.read_csv(os.path.join(core.DATA, "context", "kosovo_register_series.csv")).to_json(orient="records"))
    for k, f in [("lsg_geo", "serbia_lsg.geojson"), ("kos_geo", "kosovo_municipalities.geojson"), ("kos_outline", "kosovo.geojson")]:
        with open(os.path.join(core.DATA, "geo", f)) as fh:
            out[k] = json.load(fh)
    return json.dumps(out, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def methods_html() -> str:
    md = open(os.path.join(core.HERE, "METHODS.md"), encoding="utf-8").read()
    out = []
    for para in md.strip().split("\n\n"):
        p = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", para)
        p = re.sub(r"\*(.+?)\*", r"<i>\1</i>", p)
        p = re.sub(r"`(.+?)`", r"<code>\1</code>", p)
        out.append(f"<h3>{p[3:]}</h3>" if p.startswith("## ") else f"<p>{p}</p>")
    src = "".join(f"<li>{v}</li>" for v in core.SOURCES.values())
    return "".join(out) + f"<h3>Sources</h3><ul>{src}</ul>"


with st.sidebar:
    height = st.slider("Height of the view (px)", 600, 1400, 860, 20,
                       help="About 760 on a 16-inch laptop, 1100 or more on a 27-inch monitor.")

payload = build_payload(stamp("results"))
html = open(os.path.join(core.HERE, "ui.html"), encoding="utf-8").read()
html = html.replace("__DATA__", payload).replace("__METHODS__", json.dumps(methods_html()).replace("</", "<\\/"))
if hasattr(st, "iframe"):
    st.iframe(html, height=height)
else:
    components.html(html, height=height, scrolling=False)
