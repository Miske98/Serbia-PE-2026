import pandas as pd, re
d=pd.read_csv('data/raw/rik_final_rows.csv'); s=pd.read_csv('data/raw/rik_final_summary.csv'); s=s[s.opstina!='УКУПНО:'].copy()
s.loc[s.opstina.str.contains('ЗАВОД'),'opstina']='ЗАВОДИ'
s.loc[s.opstina=='Иностранство','opstina']='ИНОСТРАНСТВО'
munis=set(s.opstina)
okr=['ГРАД БЕОГРАД','ЈАБЛАНИЧКИ','ЈУЖНОБАНАТСКИ','ЈУЖНОБАЧКИ','БОРСКИ','БРАНИЧЕВСКИ','ЗАЈЕЧАРСКИ','ЗАПАДНОБАЧКИ','ЗЛАТИБОРСКИ','КОЛУБАРСКИ','КОСОВСКИ','КОСОВСКО-МИТРОВАЧКИ','КОСОВСКО-ПОМОРАВСКИ','МАЧВАНСКИ','МОРАВИЧКИ','НИШАВСКИ','ПЕЋКИ','ПИРОТСКИ','ПОДУНАВСКИ','ПОМОРАВСКИ','ПРИЗРЕНСКИ','ПЧИЊСКИ','РАСИНСКИ','РАШКИ','СЕВЕРНОБАНАТСКИ','СЕВЕРНОБАЧКИ','СРЕДЊОБАНАТСКИ','СРЕМСКИ','ТОПЛИЧКИ','ШУМАДИЈСКИ']
def op(t):
    t=re.sub(r'\s+',' ',str(t)).replace('ОКРУГ ОПШТИНА','').strip()
    if 'ЗАВОД' in t: return 'ЗАВОДИ'
    if t.startswith('ИНОСТРАНСТВО'): return 'ИНОСТРАНСТВО'
    for m in sorted(munis,key=len,reverse=True):   # longest municipality name contained in the row text, after the okrug
        for o in okr:
            if t.startswith(o) and m in t[len(o):]: return m
    for m in sorted(munis,key=len,reverse=True):
        if m in t and m not in okr: return m
    return None
d['op']=d.left.map(op)
# rows with no municipality text: same as previous row on the page
d['op']=d.groupby('page').op.ffill()
d['op']=d.op.ffill()
g=d.groupby('op').agg(n=('ps_no','size'),r=('registered','sum'),mx=('ps_no','max'))
c=s.set_index('opstina').join(g,how='outer')
bad=c[(c.n!=c.n_ps)|(c.r!=c.registered)]
print(len(d), d.registered.sum()); print(bad)
print(d[d.op.isna()].head())
d.to_csv('data/raw/rik_final_rows_units.csv',index=False)

# Two rows sit on the pages where the prisons table is drawn; their unit is read from context.
d.loc[(d.op == 'ЗАВОДИ') & (d.ps_no == 113) & (d.registered == 1520), 'op'] = 'ЧУКАРИЦА'
d.loc[(d.op == 'ЗАВОДИ') & (d.ps_no == 1) & (d.registered == 184), 'op'] = 'БОЉЕВАЦ'
# Prisons table overlaps other text and cannot be read by position; its counts read top-to-bottom equal Annex 1 (old decision),
# and the summary page gives the same 29 stations / 8,295 voters, so Annex 1 values are kept for prisons.
d = d[d.op != 'ЗАВОДИ']
g = d.groupby('op').agg(n=('ps_no', 'size'), r=('registered', 'sum'))
c = s.set_index('opstina').join(g, how='left')
bad = c[((c.n != c.n_ps) | (c.r != c.registered)) & (c.index != 'ЗАВОДИ')]
print('after fix, mismatching units:', len(bad)); print(bad)
print('stations', len(d), 'voters', d.registered.sum(), '+ prisons 8295 =', d.registered.sum() + 8295)
d.to_csv('data/raw/rik_final_rows_units.csv', index=False)
