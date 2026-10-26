"""Parse RIK Decision 02 no. 013-863/26 of 23 Oct 2026 (final number of voters per polling station).
Station rows are read from word positions; municipality totals from the summary pages are used to validate."""
import re, sys, collections, pdfplumber, pandas as pd
pdf = pdfplumber.open(sys.argv[1])
rows, summ = [], []
okr_names = set()
def isnum(t): return re.fullmatch(r"\d+", t) is not None
for pi, page in enumerate(pdf.pages):
    words = page.extract_words(keep_blank_chars=False, use_text_flow=False)
    if not words: continue
    text = page.extract_text() or ""
    if "БРОЈ БИРАЧКИХ" in text or pi >= 229:          # summary pages: OKRUG header lines, then "OPSTINA n_ps n_voters"
        for line in text.splitlines():
            m = re.match(r"^(.*?\S)\s+(\d+)\s+(\d+)$", line.strip())
            if m: summ.append((m.group(1), int(m.group(2)), int(m.group(3))))
            elif line.strip() and not re.search(r"\d", line) and "БРОЈ" not in line and "ОКРУГ" not in line and "МЕСТА" not in line:
                okr_names.add(line.strip())
        continue
    W = page.width
    nums = [w for w in words if isnum(w["text"])]
    hi_x1 = collections.Counter(round(w["x1"]) for w in nums if w["x1"] > 0.6 * W)
    if not hi_x1: continue
    cx = lambda w: (w["x0"] + w["x1"]) / 2
    cs = [round(cx(w)) for w in nums if w["x1"] > 0.8 * W]
    if not cs: continue
    edge = max(set(cs), key=lambda x: (sum(abs(y - x) <= 3 for y in cs), x))   # counts are centre-aligned in the last column
    cnt = [w for w in nums if abs(cx(w) - edge) <= 4]
    rest = [w for w in nums if w not in cnt and w["x0"] > 0.2 * W and w["x1"] < edge - 40]
    if not cnt or not rest: continue
    xs = collections.Counter(round(w["x0"] / 4) for w in rest)
    bm_x = min(k for k, v in xs.items() if v >= 2 or len(xs) == 1) * 4
    bms = sorted([w for w in rest if abs(w["x0"] - bm_x) <= 10], key=lambda w: w["top"])
    for i, b in enumerate(bms):
        yc = (b["top"] + b["bottom"]) / 2
        lo = (yc + (bms[i-1]["top"] + bms[i-1]["bottom"]) / 2) / 2 if i else yc - 30
        hi = (yc + (bms[i+1]["top"] + bms[i+1]["bottom"]) / 2) / 2 if i + 1 < len(bms) else yc + 30
        c = min(cnt, key=lambda w: abs((w["top"] + w["bottom"]) / 2 - yc))
        left = sorted([w for w in words if w["x1"] <= b["x0"] - 1 and lo <= (w["top"] + w["bottom"]) / 2 < hi], key=lambda w: (round(w["top"]), w["x0"]))
        # split okrug (leftmost column) from opstina: okrug words start at the page's leftmost x
        xmin = min(w["x0"] for w in words)
        okr = [w for w in left if w["x0"] < xmin + 60 and not any(abs(w["x0"] - o["x0"]) > 60 for o in [])]
        mid = sorted([w for w in words if b["x1"] < w["x0"] and w["x1"] < c["x0"] - 1 and lo <= (w["top"] + w["bottom"]) / 2 < hi], key=lambda w: (round(w["top"]), w["x0"]))
        rows.append(dict(page=pi + 1, left=" ".join(w["text"] for w in left), ps_no=int(b["text"]), registered=int(c["text"]),
                         count_dy=abs((c["top"] + c["bottom"]) / 2 - yc), mid=" ".join(w["text"] for w in mid)))
d = pd.DataFrame(rows)
s = pd.DataFrame(summ, columns=["opstina", "n_ps", "registered"])
okr = sorted(okr_names | {"ГРАД БЕОГРАД", "ЗАВОДСКИХ САНКЦИЈА"}, key=len, reverse=True)
def split_left(t):
    t = re.sub(r"\s+", " ", t).strip()
    # okrug words appear first on the row line, opština words may wrap; remove every okrug token sequence
    for o in okr + ["ГРАД БЕОГРАД", "БЕОГРАД"]:
        pass
    return t
d.to_csv(sys.argv[2], index=False); s.to_csv(sys.argv[3], index=False)
print(len(d), d.registered.sum(), len(s), s.registered.sum(), s.n_ps.sum()); print(sorted(okr_names))

