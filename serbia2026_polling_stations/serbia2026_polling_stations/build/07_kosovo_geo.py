"""Kosovo municipalities in Serbia's system (29 + Mališevo), from the SVG paths of the 'Kosovo Register and Population'
project (geoBoundaries ADM2, grouped), converted back to lon/lat by matching the bounding box of the geoBoundaries outline."""
import json, re, sys
from shapely.geometry import shape
src = json.load(open(sys.argv[1]))
out = json.load(open("data/geo/kosovo.geojson"))
x0, y0, x1, y1 = shape(out["features"][0]["geometry"]).bounds
W, H = src["W"], src["H"]
def ll(x, y): return [round(x0 + x / W * (x1 - x0), 5), round(y1 - y / H * (y1 - y0), 5)]
feats = []
for f in src["f"]:
    rings = []
    for sub in re.split(r"(?=M)", f["d"]):
        pts = [ll(float(a), float(b)) for a, b in re.findall(r"(-?[\d.]+),(-?[\d.]+)", sub)]
        if len(pts) > 2:
            rings.append([pts + [pts[0]]])
    feats.append({"type": "Feature", "properties": {"name": f["n"].rstrip("*"), "not_in_serbian_system": f["n"].endswith("*")},
                  "geometry": {"type": "MultiPolygon", "coordinates": rings}})
json.dump({"type": "FeatureCollection", "features": feats}, open("data/geo/kosovo_municipalities.geojson", "w"))
print(len(feats))
