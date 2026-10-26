# Results folder

Put RIK result files here (CSV or XLSX, any number). They are read in alphabetical order and later files replace earlier ones for the same polling station, so name them with a time stamp, e.g. `2026-10-26_0900_rik.xlsx`.

Recognised automatically (Cyrillic or Latin, any case):
- municipality: Општина / Opština / Municipality
- station number: Број бирачког места / Broj biračkog mesta (or a station label starting with the number, e.g. "12 - OŠ ...")
- registered: Број уписаних бирача / Broj birača u biračkom spisku
- voted: Број бирача који су гласали / Glasalo
- invalid / valid ballots, ballots received / unused / in the box (optional)
- every other numeric column is treated as an electoral list
- long format (one row per list, with columns "Lista" and "Glasova") is also accepted

If a municipality name does not match, add a column `station_id` with the code used in `data/stations.csv` (e.g. `024-015`). Rows that cannot be matched are listed in the app under "Data and sources".

Minimal hand-made file (turnout only):

```
station_id,registered,voted
001-001,703,402
```
