"""Join parsed stations with coordinates; classify domestic / Kosovo / abroad / prison; write data/stations.csv."""
import re, sys, pandas as pd, numpy as np
sys.path.insert(0, "build"); from abroad_cities import station as abroad_station
CYR = dict(zip("АБВГДЂЕЖЗИЈКЛЉМНЊОПРСТЋУФХЦЧЏШабвгдђежзијклљмнњопрстћуфхцчџш",
 ["A","B","V","G","D","Đ","E","Ž","Z","I","J","K","L","Lj","M","N","Nj","O","P","R","S","T","Ć","U","F","H","C","Č","Dž","Š",
  "a","b","v","g","d","đ","e","ž","z","i","j","k","l","lj","m","n","nj","o","p","r","s","t","ć","u","f","h","c","č","dž","š"]))
def lat(s): return "".join(CYR.get(c, c) for c in str(s)) if isinstance(s, str) else s
def title(s):
    t = " ".join(w[:1] + w[1:].lower() if w.isupper() else w for w in str(s).split(" "))
    t = re.sub(r'([„"“(«\-])(\w)', lambda m: m.group(1) + m.group(2).upper(), t)
    for w in (" На ", " И ", " У ", " Са ", " Од ", " За "): t = t.replace(w, w.lower())
    return t
def norm(x):
    x = str(x).upper().replace("–", "-"); x = re.sub(r"\s*-\s*ГРАД$", "", x); x = re.sub(r"\s*-\s*", "-", x); return x.strip()
def akey(s): return re.sub(r"[^0-9A-ZА-ЯЂЈЉЊЋЏ]", "", re.sub(r"\b(БРОЈ|БР\.|BR\.|ББ)", "", str(s).upper()))

KIM = {"ГЊИЛАНЕ","ГОРА","ИСТОК","КЛИНА","КОСОВО ПОЉЕ","КОСОВСКА КАМЕНИЦА","КОСОВСКА МИТРОВИЦА","ЛЕПОСАВИЋ","ЛИПЉАН","НОВО БРДО","ОБИЛИЋ",
       "ОРАХОВАЦ","ПЕЋ","ПРИШТИНА","ПРИЗРЕН","СРБИЦА","УРОШЕВАЦ","ВИТИНА","ВУЧИТРН","ЗУБИН ПОТОК","ЗВЕЧАН","ШТРПЦЕ"}
ps = pd.read_csv("data/raw/ps_parsed.csv", dtype={"mun_code": str})
g = pd.read_csv("data/raw/bm2026_geo.tsv", sep="\t", encoding="utf-8-sig")
ps["k"] = ps.mun_name.map(norm)
g["k"] = g.opstina.map(norm).replace({"БЕЛА CRKVA": "БЕЛА ЦРКВА", "КОСТОЛАЦ": "ПОЖАРЕВАЦ-КОСТОЛАЦ"})
g = g[g.lat.notna()]
g["pool"] = [k.split("-")[0] if k.startswith(("ВРАЊЕ", "УЖИЦЕ")) else k for k in g.k]          # geo file merges Vranjska Banja into Vranje, Sevojno into Užice
g["ak"] = g.adresa.map(akey); g["uk"] = g.ulica.map(akey); g["nas"] = g.naselje.astype(str).str.upper().str.strip()
good = g[g.geo_tacnost.isin(["objekat", "ulica", "naselje"])]
settle = good.groupby(["pool", "nas"])[["lat", "lng"]].median()
muni_c = good.groupby("pool")[["lat", "lng"]].median()

def host_pool(r):
    if r.k in KIM:  # Kosovo registration units vote at relocated stations; the address names the host town
        return norm(r.address.split(",")[0]) if isinstance(r.address, str) else None
    if r.k == "ZAVODI": return norm(str(r.address).split(",")[0])
    return r.k.split("-")[0] if r.k.startswith(("ВРАЊЕ", "УЖИЦЕ")) else r.k

MANUAL = {"БЕОГРАД-СТАРИ ГРАД": (44.8186, 20.4590), "БЕОГРАД": (44.8125, 20.4612)}
out = []
for r in ps.itertuples():
    rec = dict(lat=np.nan, lon=np.nan, geo_precision="none", geo_note="")
    if r.mun_code == "198":
        city, country, la, lo = abroad_station(r.ps_no)
        rec.update(lat=la, lon=lo, geo_precision="city", geo_note="City centre (manual)", city=city, country=country)
    else:
        pool = host_pool(r); a = akey(r.address)
        cand = g[g.pool == pool] if pool else g.iloc[0:0]
        if r.k in KIM or r.k == "ZAVODI":
            cand = g[(g.pool.str.split("-").str[0] == pool) | (g.nas == pool)]
        # 1) same number and same address  2) same address anywhere in host unit  3) settlement  4) unit centre
        hit = cand[(cand.k == r.k) & (cand.redni_broj == r.ps_no) & (cand.ak == a)]
        if hit.empty: hit = cand[(cand.ak == a) | ((cand.uk == a) & (cand.uk != "NAN"))]
        if hit.empty and "," in str(r.address): hit = cand[cand.uk == akey(str(r.address).split(",", 1)[1])]
        if not hit.empty:
            h = hit.iloc[0]; rec.update(lat=h.lat, lon=h.lng, geo_precision={"objekat":"building","ulica":"street","naselje":"settlement"}.get(h.geo_tacnost, "approx"),
                                        geo_note="Address match, izbori26.com geocode via majstors/datasets-parlamentarni-izbori2026")
        else:
            sett = str(r.address).split(",")[0].strip().upper() if isinstance(r.address, str) else ""
            sk = [i for i in settle.index if i[1] == sett and (i[0] == pool or i[0].split("-")[0] == pool or r.k in KIM or r.k == "ZAVODI")]
            if r.k in KIM or r.k == "ZAVODI": sk = [i for i in sk if i[1] == sett and (i[0].split("-")[0] == pool or i[1] == pool)] or [i for i in settle.index if i[1] == pool]
            if sk:
                la, lo = settle.loc[sk[0]]; rec.update(lat=la, lon=lo, geo_precision="settlement", geo_note="Median of geocoded stations in the same settlement")
            elif pool in MANUAL:
                la, lo = MANUAL[pool]; rec.update(lat=la, lon=lo, geo_precision="municipality", geo_note="Municipality centre (manual; source geocodes unavailable)")
            elif pool in muni_c.index:
                la, lo = muni_c.loc[pool]; rec.update(lat=la, lon=lo, geo_precision="municipality", geo_note="Median of geocoded stations in the municipality")
    out.append(rec)
geo = pd.DataFrame(out, index=ps.index)
df = pd.concat([ps, geo], axis=1)
df["kind"] = np.select([df.mun_code == "198", df.mun_code == "199", df.k.isin(KIM)], ["abroad", "prison", "kosovo"], "domestic")
df["unit"] = df.mun_name.map(lambda s: lat(title(s)).replace("-", " - ").replace("  ", " ").replace(" - Град", "").replace(" - Grad", "").replace("Inostranstvo", "Abroad").replace("Zavodi", "Prisons"))
def lsg(u, kind):
    u = u.replace(" - ", "-")
    if kind in ("abroad", "prison", "kosovo"): return None
    base = re.split(r"-", u)[0].strip()
    return base
df["lsg"] = [lsg(u, k) for u, k in zip(df.unit, df.kind)]
df["host_town"] = [lat(title(str(a).split(",")[0])) if k in ("kosovo", "prison") else None for a, k in zip(df.address, df.kind)]
df["station_id"] = df.mun_code + "-" + df.ps_no.astype(str).str.zfill(3)
df["name_lat"] = df.name.map(lambda s: lat(title(s))); df["address_lat"] = df.address.map(lambda s: lat(title(s)) if isinstance(s, str) else "")
cols = ["station_id","mun_code","unit","lsg","kind","ps_no","name_lat","address_lat","registered","lat","lon","geo_precision","geo_note","city","country","host_town","name","address"]
df[cols].rename(columns={"registered": "registered_2026"}).to_csv("data/stations.csv", index=False)
print(df.kind.value_counts()); print(df.geo_precision.value_counts()); print(df.groupby("kind").registered.sum())
import json; names={f["properties"]["name"] for f in json.load(open("data/geo/serbia_lsg.geojson"))["features"]}
print("missing lsg in map:", sorted(set(df.lsg.dropna()) - names)); print(df[df.geo_precision=="none"][["unit","ps_no","address"]].head(20).to_string())

# ---- post-check: every domestic station must fall inside (or within ~1 km of) its municipality polygon
import json
from shapely.geometry import shape, Point
G = json.load(open("data/geo/serbia_lsg.geojson"))
poly = {f["properties"]["name"]: shape(f["geometry"]) for f in G["features"]}
s = pd.read_csv("data/stations.csv", dtype={"mun_code": str})
dom = s.kind == "domestic"
inside = pd.Series([poly[l].buffer(0.01).contains(Point(x, y)) if k == "domestic" else True
                    for l, x, y, k in zip(s.lsg, s.lon, s.lat, s.kind)])
s["settlement"] = s.address.astype(str).str.split(",").str[0].str.strip().str.upper()
ok = s[dom & inside & s.geo_precision.isin(["building", "street", "settlement"])]
med = ok.groupby(["unit", "settlement"])[["lat", "lon"]].median()
UNIT_CENTRE = {"Beograd - Sopot": (44.5194, 20.5753)}
print(s[dom & ~inside].unit.value_counts().head(10))
for i in s.index[dom & ~inside]:
    key = (s.at[i, "unit"], s.at[i, "settlement"])
    if key in med.index:
        s.loc[i, ["lat", "lon"]] = med.loc[key].values
        s.loc[i, ["geo_precision", "geo_note"]] = ["settlement", "Source geocode outside municipality; moved to median of valid stations in the same settlement"]
    elif s.at[i, "unit"] in UNIT_CENTRE:
        s.loc[i, ["lat", "lon"]] = UNIT_CENTRE[s.at[i, "unit"]]
        s.loc[i, ["geo_precision", "geo_note"]] = ["municipality", "Source geocode outside municipality; moved to municipality centre (manual)"]
    else:
        p = poly[s.at[i, "lsg"]].representative_point()
        s.loc[i, ["lat", "lon"]] = [p.y, p.x]
        s.loc[i, ["geo_precision", "geo_note"]] = ["municipality", "Source geocode outside municipality; moved to a point inside the municipality polygon"]
print("moved", int((dom & ~inside).sum()))
s.drop(columns="settlement").to_csv("data/stations.csv", index=False)
