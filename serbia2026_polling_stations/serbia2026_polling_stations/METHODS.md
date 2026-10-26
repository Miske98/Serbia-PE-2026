## Methods

**Purpose and limits.** The tool describes patterns in polling-station numbers published by the Republic Electoral Commission (RIK). Every check below can flag stations for a closer look at the records (*zapisnici*) and observer reports. None of them establishes that anything improper happened; ordinary causes include small or special stations, local turnout drives, data-entry errors and differences in how registers are kept.

**Register and stations.** Voters per station come from RIK's decision on the final number of voters (02 no. 013-863/26, 23 October 2026): 8,392 stations and 6,451,292 voters. The table was read from the PDF by word position. For all 192 units, its station counts and voter totals agree with the decision's summary pages. The prisons table in that PDF is printed over other text and cannot be read reliably by position. Its 29 stations and 8,295 voters equal the Ministry's Annex 1 of 9 October, so the Annex 1 figures are used for prisons. Station names and addresses come from that Annex 1, which lists 6,450,523 voters. Between the two documents, 1,001 stations changed, for a net change of +769 voters. The Annex 1 figure for each station is kept as `registered_annex1`.

**Coordinates.** Taken from the izbori26.com geocodes published by majstors/datasets-parlamentarni-izbori2026 (unofficial). Matched to the official list by address within the same municipality, because some station numbers changed after that list was published. If no address matched, the station is placed at the median position of other stations in the same settlement, or of the municipality. Stations abroad are at the city centre. The *geo_precision* column says which applies. Spatial checks use only stations with settlement-level coordinates or better.

**Kosovo and Metohija.** Voters registered in Kosovo and Metohija municipalities vote at relocated stations. The station addresses in Annex 1 place all of them in Vranje, Raška, Tutin and Kuršumlija. Their results are reported under the registration municipality and are kept separate from the spatial checks.

**1. Arithmetic consistency.** Compares the figures recorded for each station: voters who voted against registered voters, valid plus invalid against ballots in the box, list votes against valid ballots, and ballots received minus unused against voters who voted. A station appears only where the loaded file has the columns needed.

**2. Round percentages.** Kobak, D., Shpilkin, S. & Pshenichnikov, M. S. (2016). *Integer percentages as electoral falsification fingerprints.* Annals of Applied Statistics 10(1). The number of stations whose turnout is an exact whole percentage (or a multiple of 5%) is compared with 2,000 simulations in which each station's count varies binomially around its own turnout. Only stations with at least 100 registered voters are included.

**3. Election fingerprint.** Klimek, P., Yegorov, Y., Hanel, R. & Thurner, S. (2012). *Statistical detection of systematic election irregularities.* PNAS 109(41). This is a two-dimensional histogram of turnout against a list's vote share, weighted by votes. In most elections it shows one compact cluster. A smear towards high turnout and high share, or a separate cluster there, is the pattern the authors describe. Regional differences can produce a similar shape.

**4. Spatial comparison.** Anselin, L. (1995). *Local indicators of spatial association: LISA.* Geographical Analysis 27(2). Turnout at each domestic station is compared with its 8 nearest stations, using Local Moran's I with 999 conditional permutations. The tool also gives a neighbour-deviation score: turnout minus the neighbours' median, divided by a robust standard deviation (1.4826 × MAD). Stations with a score of ±3 or more are listed.

**5. Station size and change since 2023.** Turnout is plotted against station size. It is also compared with turnout at the same station in 2023, for stations matched by number and name. Both are descriptive and have no formal test.

**Language.** Results are described as *within* or *outside* the range expected under random variation. Flags are invitations to check, not findings.
