"""Parse the Ministry's decision (Annex 1) into one row per polling station."""
import re, sys, pandas as pd
txt = open(sys.argv[1], encoding="utf-8").read()
mun_re = re.compile(r"^(\d{3})(?: (\S.*?))?\s{2,}(\d+)\s+([\d.]+)\s*$")
st_re = re.compile(r"^([\d.]+)\s+(\d+)\s{2,}(\S.*?)(?:\s{2,}([\d.]+))?\s*$")
rows, muns, cur, last = [], {}, None, None
for line in txt.splitlines():
    m = mun_re.match(line)
    if m:
        code, name = m.group(1), (m.group(2) or {"198":"INOSTRANSTVO","199":"ZAVODI"}.get(m.group(1),"?")).strip()
        muns[code] = (name, int(m.group(3)), int(m.group(4).replace(".", "")))
        cur = code; continue
    s = st_re.match(line)
    if s and cur:
        if not s.group(4):  # count may follow on a continuation line (rare)
            print("NOCOUNT", cur, line[:120], file=sys.stderr)
        rows.append(dict(mun_code=cur, mun_name=muns[cur][0], seq=int(s.group(1).replace(".","")), ps_no=int(s.group(2)),
                         title=s.group(3).strip(), registered=int(s.group(4).replace(".", "")) if s.group(4) else None))
        last = rows[-1]; continue
    # continuation of a wrapped title: indented ~24 cols, uppercase, before street list
    if last is not None and re.match(r"^ {16,30}\S", line) and not line.strip().startswith("Улица") and line.strip().upper() == line.strip() and "бројеви" not in line:
        if not last.get("_done"):
            last["title"] += " " + line.strip()
    if last is not None and ("Улица" in line or "бројеви" in line or "Насеље" in line):
        last["_done"] = True
df = pd.DataFrame(rows).drop(columns=["_done"], errors="ignore")
df = df.drop_duplicates(["mun_code", "ps_no"])
m = pd.DataFrame([(k, *v) for k, v in muns.items()], columns=["mun_code", "mun_name", "n_ps_official", "registered_official"])
chk = df.groupby("mun_code").agg(n=("ps_no", "size"), reg=("registered", "sum")).reset_index().merge(m, on="mun_code")
bad = chk[(chk.n != chk.n_ps_official) | (chk.reg != chk.registered_official)]
print("stations", len(df), "sum", df.registered.sum(), "official", m.registered_official.sum(), "munis", len(m))
print("mismatches:\n", bad.to_string())
df[["name", "address"]] = df.title.str.split(";", n=1, expand=True).reindex(columns=[0, 1])
df["name"] = df["name"].str.strip(); df["address"] = df["address"].str.strip()
df.to_csv(sys.argv[2], index=False); m.to_csv(sys.argv[3], index=False)
