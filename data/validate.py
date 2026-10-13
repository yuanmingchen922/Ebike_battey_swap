import sys, json, glob
import pandas as pd, numpy as np, shapefile
raw = sys.argv[1]
print("=== 1. DOHMH")
d = pd.read_csv(f"{raw}/dohmh_restaurants.csv", dtype={'camis':str,'r_zip':str,'r_cb':str,'r_tract':str})
print("rows", len(d), "distinct camis", d.camis.nunique())
inb = d.r_lat.between(40.4,41.0) & d.r_lon.between(-74.3,-73.6)
print("share lat/lon in bbox", round(inb.mean(),4), inb.sum())
print("share with cuisine", round(d.r_cuisine.notna().mean(),4), d.r_cuisine.notna().sum())
print("share with last inspection date", round(d.r_last_insp.notna().mean(),4))
print("usable (bbox & cuisine & inspected)", (inb & d.r_cuisine.notna() & d.r_last_insp.notna()).sum())
print("boro counts\n", d.r_boro.value_counts(dropna=False).to_string())
print("Manhattan", (d.r_boro=='Manhattan').sum(), "Manhattan usable", ((d.r_boro=='Manhattan')&inb&d.r_cuisine.notna()&d.r_last_insp.notna()).sum())
print("top20 cuisine\n", d.r_cuisine.value_counts().head(20).to_string())
print("n_rows sum (should equal source row count)", d.n_rows.sum())

print("=== 2. GeoDa")
shp = glob.glob(f"{raw}/nycnhood_acs/*.shp")[0]
sf = shapefile.Reader(shp)
print("records", len(sf), "shapeType", sf.shapeTypeName)
fields = [f[0] for f in sf.fields[1:]]
print("nfields", len(fields)); print(fields)
recs = [list(r) for r in sf.iterRecords()]
a = pd.DataFrame(recs, columns=fields)
a.to_csv(f"{raw}/nycnhood_acs_attributes.csv", index=False)
cols = ['poptot','medianinco','medianage','male16to19','femal16_19','bachelor','popdty']
print(a[cols].describe().T.to_string())
prj = open(glob.glob(f"{raw}/nycnhood_acs/*.prj")[0]).read()
print("PRJ:", prj[:300])
feats = []
for sr in sf.iterShapeRecords():
    geom = sr.shape.__geo_interface__
    feats.append({"type":"Feature","geometry":geom,"properties":dict(zip(fields, [ (v.isoformat() if hasattr(v,'isoformat') else v) for v in sr.record]))})
gj = {"type":"FeatureCollection","features":feats}
json.dump(gj, open(f"{raw}/nycnhood_acs.geojson","w"))
print("bbox", sf.bbox)
print("geojson features", len(feats), "name sample", a.iloc[0].to_dict() if 'name' not in a else a['name'].head(3).tolist())

print("=== 3. crash grid")
c = pd.read_csv(f"{raw}/cyclist_crash_grid_0005deg.csv")
print("cells", len(c), "total crashes", c.cyc_crashes.sum(), "inj", c.cyc_inj.sum(), "killed", c.cyc_killed.sum())
print(c.sort_values('cyc_crashes', ascending=False).head(10).to_string())
print("lat range", c.lat_cell.min(), c.lat_cell.max(), "lon range", c.lon_cell.min(), c.lon_cell.max())

print("=== 4. counters")
p = pd.read_csv(f"{raw}/bike_counter_hourly_profile.csv", dtype={'id':str})
s = p.groupby(['id','daytype']).share_of_day.sum()
print("shares sum to 1:", np.allclose(s.values, 1.0), s.min(), s.max())
print("counters with data", p.id.nunique(), "rows", len(p))
print("hours per (id,daytype):", p.groupby(['id','daytype']).hour.count().unique())
pk = p.loc[p.groupby(['name','daytype']).share_of_day.idxmax(), ['name','daytype','hour','share_of_day','mean_count_per_interval']]
print(pk.to_string())
ev = p[p.hour.between(15,22)]
pe = ev.loc[ev.groupby(['name','daytype']).share_of_day.idxmax(), ['name','daytype','hour','share_of_day']]
print("evening peak (15-22h)\n", pe.to_string())
tot = p.groupby(['name','daytype']).sum_counts_2024.sum().unstack()
print(tot.to_string())
