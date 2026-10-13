import json, sys, time, re
import requests, pandas as pd
raw = sys.argv[1]
sites = json.load(open(f"{raw}/bike_counter_sites_raw.json"))
KEYS = ['Ave','St','Greenway','Columbus','Amsterdam','Broadway','Prospect','Kent']
def keep(n):
    if 'Bridge' in n or 'Peds' in n: return False
    return any(k in n for k in KEYS)
sel = [s for s in sites if keep(s.get('name',''))]
rows = []
for s in sel:
    rows.append(dict(id=s['id'], name=s['name'], lat=float(s['latitude']), lon=float(s['longitude']),
                     counter=s.get('counter'), interval_min=int(s.get('interval',15)), domain=s.get('domain'), timezone=s.get('timezone')))
pd.DataFrame(rows).to_csv(f"{raw}/bike_counter_sites.csv", index=False)
print("selected", len(sel), [s['name'] for s in sel])

URL = 'https://data.cityofnewyork.us/resource/uczf-rk3c.json'
out = []
for s in sel:
    params = {'$select': 'date_extract_dow(date) as dow,date_extract_hh(date) as hh,sum(counts) as c,count(*) as n',
              '$where': f"id='{s['id']}' AND date between '2024-01-01T00:00:00' and '2024-12-31T23:59:59'",
              '$group': 'dow,hh', '$order': 'dow,hh', '$limit': 500}
    for attempt in range(3):
        r = requests.get(URL, params=params, timeout=120)
        if r.ok: break
        time.sleep(3)
    r.raise_for_status()
    d = r.json()
    print(s['id'], s['name'], 'groups', len(d), 'bytes', len(r.content))
    for x in d:
        out.append(dict(id=s['id'], name=s['name'], lat=float(s['latitude']), lon=float(s['longitude']),
                        interval_min=int(s.get('interval',15)), dow=int(x['dow']), hour=int(x['hh']), c=float(x['c']), n=int(x['n'])))
df = pd.DataFrame(out)
df.to_csv(f"{raw}/bike_counter_dow_hour_raw.csv", index=False)
# SoQL date_extract_dow: 0 = Sunday ... 6 = Saturday
df['daytype'] = df['dow'].map(lambda d: 'weekend' if d in (0,6) else 'weekday')
g = df.groupby(['id','name','lat','lon','interval_min','daytype','hour'], as_index=False)[['c','n']].sum()
g['mean_count_per_interval'] = g['c']/g['n']
g['share_of_day'] = g['c']/g.groupby(['id','daytype'])['c'].transform('sum')
g = g.rename(columns={'c':'sum_counts_2024','n':'n_intervals_2024'})
g = g.sort_values(['id','daytype','hour'])
g.to_csv(f"{raw}/bike_counter_hourly_profile.csv", index=False)
print(g.head())
