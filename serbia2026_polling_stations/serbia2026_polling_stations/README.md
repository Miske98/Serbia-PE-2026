# Serbia 2026 Polling Stations

Streamlit app for exploring turnout and results by polling station for the parliamentary election of 25 October 2026. The map is always visible next to the analysis panel (forensics, register, Kosovo and Metohija, abroad, station search); hovering a chart bar, heat-map cell, point or table row highlights those stations or municipalities on the map. The interface is a single HTML component (`ui.html`, deck.gl + Plotly.js); `app.py` prepares the data. Use the sidebar to set the view height for your screen.

## Run locally

```
pip install -r requirements.txt
streamlit run app.py
```

## Host it on GitHub + Streamlit Community Cloud (free)

1. On github.com create a new repository (private is fine), e.g. `serbia2026-polling-stations`.
2. Upload the contents of this folder (not the folder itself): on the empty repository page choose "uploading an existing file", drag all files and folders in, then "Commit changes". `app.py` must be at the top level of the repository.
3. Go to share.streamlit.io, sign in with GitHub, choose "Create app" → "Deploy a public app from GitHub", pick the repository, branch `main`, main file `app.py`, then "Deploy". The first start takes 2–4 minutes.
4. Private repositories can be deployed too; under the app's Settings → Sharing you choose who can view it.

## Updating results

RIK files go into `data/results/`. Upload the new file on GitHub (open `data/results` → Add file → Upload files) with a name that sorts after the previous one, e.g. `2026-10-27_0900_rik.xlsx`. Files are read in alphabetical order and later files replace earlier ones station by station, so you can keep the old ones or delete them. The app reloads automatically within a minute or two after the commit.

Stations RIK has not processed yet come with zeros; they are treated as "not processed" and left out of all analyses. The bar at the top of the map shows how many stations are processed. List names come from `data/results/list_names.csv` (column `lista_N` → name); edit it if RIK changes the column layout.

## Folders

| Path | Content |
|---|---|
| `data/stations.csv` | 8,392 polling stations: voters from RIK's final number (23 Oct), names and addresses from the Ministry's Annex 1 (9 Oct), coordinates and type (domestic / kosovo / abroad / prison) |
| `data/results/` | RIK result files and `list_names.csv` |
| `data/baseline/` | 2023 results by polling station (podatak.rs CSV, CC BY 4.0), included |
| `data/context/` | Register gap by municipality and the Kosovo register series (from the two earlier reports) |
| `data/geo/` | Municipal boundaries and Kosovo outline (geoBoundaries) |
| `core.py` | Import and analysis functions |
| `ui.html` | The interface (map + panel) |
| `METHODS.md` | Methods and references (link at the bottom of the panel) |
| `build/` | Scripts that produced `stations.csv` from the PDF |

## Rebuilding stations.csv

```
pdftotext -layout Number_of_voters_per_polling_station_2026.pdf t.txt
python build/01_parse_pdf.py t.txt data/raw/ps_parsed.csv data/raw/mun_official.csv
python build/02_build_stations.py     # needs data/raw/bm2026_geo.tsv (majstors/datasets-parlamentarni-izbori2026)
```

The parser checks every unit's station count and voter total against the headers in the PDF. They all match, and the total is 6,450,523.
