"""Use RIK's final numbers (23 Oct 2026) as registered_2026; keep the Ministry's 9 Oct numbers as registered_annex1."""
import sys, pandas as pd
sys.path.insert(0, "."); import core
st = pd.read_csv("data/stations.csv", dtype={"mun_code": str})
if "registered_annex1" not in st:
    st["registered_annex1"] = st["registered_2026"]
s = core.load_stations()
d = pd.read_csv("data/raw/rik_final_rows_units.csv")
d["ukey"] = core.align_units(d.op.map(core.unit_key), s)
m = s[["station_id", "ukey", "ps_no", "kind"]].merge(d[["ukey", "ps_no", "registered"]], on=["ukey", "ps_no"], how="left")
m.loc[m.kind == "prison", "registered"] = st.set_index("station_id").loc[m.loc[m.kind == "prison", "station_id"], "registered_annex1"].values
assert m.registered.notna().all() and len(m) == len(st)
st["registered_2026"] = st.station_id.map(m.set_index("station_id").registered).astype(int)
assert st.registered_2026.sum() == 6451292, st.registered_2026.sum()
st.to_csv("data/stations.csv", index=False)
print("total", st.registered_2026.sum(), "changed", (st.registered_2026 != st.registered_annex1).sum())
