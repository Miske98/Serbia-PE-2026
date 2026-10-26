"""Poster: share of Studentska lista and of Vučić – Ujedinjena Srbija by municipality, side by side (Serbian Latin)."""
import json, sys, math
import numpy as np, pandas as pd
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch
from matplotlib.path import Path
from matplotlib.colors import LinearSegmentedColormap
from shapely.geometry import shape
sys.path.insert(0, "/home/claude/proj/app"); import core

st = core.load_stations(); res, _, _ = core.load_results(); T, LISTS = core.build_table(st, res)
R = T[T.reported].copy()
STUD, SNS = "L: Studentska lista", "L: Vučić – Ujedinjena Srbija"
n_done, n_all = int(T.reported.sum()), len(T)
def shares(g): return pd.Series({"stud": g[STUD].sum() / g["valid"].sum(), "sns": g[SNS].sum() / g["valid"].sum(), "n": len(g)})
srb = R[R.kind == "domestic"].groupby("lsg").apply(shares)
kos = R[R.kind == "kosovo"].groupby("unit").apply(shares)
G = json.load(open("/home/claude/proj/app/data/geo/serbia_lsg.geojson"))
K = json.load(open("/home/claude/proj/app/data/geo/kosovo_municipalities.geojson"))
assert set(srb.index) <= {f["properties"]["name"] for f in G["features"]}
C = math.cos(math.radians(43.8))

def patch(geom, **kw):
    g = shape(geom); polys = [g] if g.geom_type == "Polygon" else list(g.geoms)
    verts, codes = [], []
    for p in polys:
        for ring in [p.exterior, *p.interiors]:
            xy = [(x * C, y) for x, y in ring.coords]
            verts += xy; codes += [Path.MOVETO] + [Path.LINETO] * (len(xy) - 2) + [Path.CLOSEPOLY]
    return PathPatch(Path(verts, codes), **kw)

mpl.rcParams.update({"font.family": "Inter", "hatch.linewidth": 0.35, "hatch.color": "#b9b4aa"})
BG, INK, MUTED = "#f6f3ee", "#1d1d1f", "#6b6760"
RED = LinearSegmentedColormap.from_list("r", ["#fbe8e4", "#f2a08f", "#d9442f", "#9e1b16", "#5a0b0b"])
BLUE = LinearSegmentedColormap.from_list("b", ["#e7eef8", "#9cbde3", "#3f7fc4", "#1b4f91", "#0b2650"])

fig = plt.figure(figsize=(16, 11.2), facecolor=BG)
fig.text(0.045, 0.955, "Dve mape iste zemlje", fontsize=34, fontweight="bold", color=INK, va="top")
fig.text(0.045, 0.9, "Udeo glasova po opštinama, parlamentarni izbori 25. oktobra 2026.", fontsize=15.5, color=MUTED, va="top")

panels = [("stud", "Studentska lista", "Studenti pobeđuju", RED, 0.035),
          ("sns", "Aleksandar Vučić", "Ujedinjena Srbija", BLUE, 0.515)]
for key, t1, t2, cmap, x0 in panels:
    ax = fig.add_axes([x0, 0.20, 0.45, 0.585]); ax.set_facecolor(BG); ax.axis("off")
    vals = pd.concat([srb[key], kos[key]])
    lo, hi = math.floor(vals.quantile(0.03) * 20) / 20, math.ceil(vals.quantile(0.97) * 20) / 20
    norm = mpl.colors.Normalize(lo, hi)
    for f in G["features"]:
        v = srb[key].get(f["properties"]["name"], np.nan)
        ax.add_patch(patch(f["geometry"], facecolor=cmap(norm(v)) if pd.notna(v) else "#dddddd", edgecolor=BG, linewidth=0.35))
    for f in K["features"]:
        v = kos[key].get(f["properties"]["name"], np.nan)
        if pd.notna(v):
            ax.add_patch(patch(f["geometry"], facecolor=cmap(norm(v)), edgecolor=BG, linewidth=0.35))
        else:
            ax.add_patch(patch(f["geometry"], facecolor=BG, edgecolor="#c9c4ba", linewidth=0.35, hatch="//////"))
    ax.set_xlim(18.75 * C, 23.15 * C); ax.set_ylim(41.8, 46.25); ax.set_aspect("equal")
    fig.text(x0 + 0.045, 0.815, t1, fontsize=21, fontweight="bold", color=cmap(0.8), va="bottom")
    fig.text(x0 + 0.045, 0.79, t2, fontsize=14, color=MUTED, va="bottom")
    cax = fig.add_axes([x0 + 0.105, 0.16, 0.24, 0.011])
    cb = mpl.colorbar.ColorbarBase(cax, cmap=cmap, norm=norm, orientation="horizontal", extend="both", extendfrac=0.04)
    ticks = np.linspace(lo, hi, 5); cb.set_ticks(ticks)
    cb.set_ticklabels([("≤ " if i == 0 else "≥ " if i == len(ticks) - 1 else "") + f"{t*100:.0f}%" for i, t in enumerate(ticks)])
    cb.outline.set_visible(False); cax.tick_params(length=0, labelsize=10, colors=MUTED, pad=4)
    cax.set_title("udeo važećih glasova", fontsize=10, color=MUTED, loc="left", pad=5)

note = (f"Preliminarni rezultati RIK-a: obrađeno {n_done:,} od {n_all:,} biračkih mesta (stanje 26. oktobra 2026. u 12:27). ".replace(",", ".") +
        "U opštinama u kojima nisu obrađena sva biračka mesta\nudeo je izračunat iz obrađenih mesta. "
        "Udeo = glasovi liste / važeći glasovi. Svaka mapa ima sopstvenu skalu boja; vrednosti ispod 3. i iznad 97. percentila\n"
        "opština obojene su krajnjom bojom. Opštine na Kosovu i Metohiji obojene su prema rezultatima biračkih mesta na kojima su njihovi birači glasali\n"
        "(Kuršumlija, Raška, Tutin, Vranje); šrafirane opštine nemaju birače u biračkom spisku. "
        "Izvor: Republička izborna komisija. Granice opština: geoBoundaries (CC BY 4.0).")
fig.text(0.045, 0.098, note, fontsize=9.2, color=MUTED, va="top", linespacing=1.55)
fig.text(0.955, 0.052, "ArtiFact - vizualne priče", fontsize=13, fontweight="bold", color=INK, ha="right", va="bottom")
fig.text(0.955, 0.03, "@dat.artifact", fontsize=11.5, color=MUTED, ha="right", va="bottom")
out = "/home/claude/proj/poster/udeo_studentska_vucic_opstine_2026"
fig.savefig(out + ".png", dpi=600, facecolor=BG); fig.savefig(out + ".pdf", facecolor=BG); fig.savefig(out + ".svg", facecolor=BG)
print(srb.describe(), kos.round(3).to_string())
