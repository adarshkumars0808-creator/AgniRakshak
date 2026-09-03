"""
forecast_engine.py - Predictive Fire Season Planning
Enhanced with: per-fire-type, per-district, alert escalation
"""
import os, json, math
from collections import Counter
import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)
DATA_DIR = os.path.join(PROJECT_DIR, "data", "processed")

FIRMS_FILE = os.path.join(DATA_DIR, "firms_clean_merged.csv")
GRID_FILE = os.path.join(DATA_DIR, "grid_features.csv")
FIRE_TYPE_FILE = os.path.join(DATA_DIR, "fire_type_predictions.csv")
OUTPUT_FILE = os.path.join(DATA_DIR, "fire_forecast.json")

MONTH_NAMES = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
FIRE_SEASON_MONTHS = {"pre_monsoon":[3,4,5],"monsoon":[6,7,8],"post_monsoon":[9,10,11],"winter":[12,1,2]}

# District mapping: lat/lon boundaries for major districts in the study area
DISTRICT_MAP = [
    {"district":"Jharia","state":"Jharkhand","latMin":23.60,"latMax":23.95,"lonMin":86.20,"lonMax":86.65},
    {"district":"Dhanbad","state":"Jharkhand","latMin":23.70,"latMax":24.00,"lonMin":86.30,"lonMax":86.70},
    {"district":"Ranchi","state":"Jharkhand","latMin":23.25,"latMax":23.55,"lonMin":85.20,"lonMax":85.55},
    {"district":"Hazaribagh","state":"Jharkhand","latMin":23.85,"latMax":24.10,"lonMin":85.25,"lonMax":85.70},
    {"district":"Giridih","state":"Jharkhand","latMin":24.05,"latMax":24.45,"lonMin":86.00,"lonMax":86.50},
    {"district":"Ramgarh","state":"Jharkhand","latMin":23.55,"latMax":23.90,"lonMin":85.50,"lonMax":85.85},
    {"district":"Singrauli","state":"Madhya Pradesh","latMin":24.00,"latMax":24.40,"lonMin":82.30,"lonMax":82.80},
    {"district":"Sidhi","state":"Madhya Pradesh","latMin":24.20,"latMax":24.60,"lonMin":81.60,"lonMax":82.20},
    {"district":"Satna","state":"Madhya Pradesh","latMin":24.00,"latMax":24.50,"lonMin":80.70,"lonMax":81.20},
    {"district":"Rewa","state":"Madhya Pradesh","latMin":24.30,"latMax":24.80,"lonMin":81.20,"lonMax":81.60},
    {"district":"Jabalpur","state":"Madhya Pradesh","latMin":23.05,"latMax":23.35,"lonMin":79.80,"lonMax":80.10},
    {"district":"Kanpur","state":"Uttar Pradesh","latMin":26.30,"latMax":26.60,"lonMin":80.15,"lonMax":80.55},
    {"district":"Lucknow","state":"Uttar Pradesh","latMin":26.75,"latMax":27.05,"lonMin":80.80,"lonMax":81.15},
    {"district":"Varanasi","state":"Uttar Pradesh","latMin":25.20,"latMax":25.45,"lonMin":82.90,"lonMax":83.15},
    {"district":"Allahabad","state":"Uttar Pradesh","latMin":25.30,"latMax":25.55,"lonMin":81.75,"lonMax":82.00},
    {"district":"Ghaziabad","state":"Uttar Pradesh","latMin":28.60,"latMax":28.85,"lonMin":77.30,"lonMax":77.60},
    {"district":"Noida","state":"Uttar Pradesh","latMin":28.45,"latMax":28.65,"lonMin":77.30,"lonMax":77.55},
    {"district":"Agra","state":"Uttar Pradesh","latMin":27.05,"latMax":27.30,"lonMin":77.90,"lonMax":78.15},
    {"district":"Meerut","state":"Uttar Pradesh","latMin":28.90,"latMax":29.15,"lonMin":77.60,"lonMax":77.85},
    {"district":"Bulandshahr","state":"Uttar Pradesh","latMin":28.35,"latMax":28.65,"lonMin":77.75,"lonMax":78.10},
    {"district":"Aligarh","state":"Uttar Pradesh","latMin":27.80,"latMax":28.10,"lonMin":78.00,"lonMax":78.30},
    {"district":"Firozabad","state":"Uttar Pradesh","latMin":27.10,"latMax":27.40,"lonMin":78.30,"lonMax":78.60},
    {"district":"Jhansi","state":"Uttar Pradesh","latMin":25.30,"latMax":25.55,"lonMin":78.50,"lonMax":78.90},
    {"district":"Ludhiana","state":"Punjab","latMin":30.80,"latMax":31.05,"lonMin":75.75,"lonMax":76.00},
    {"district":"Amritsar","state":"Punjab","latMin":31.55,"latMax":31.80,"lonMin":74.75,"lonMax":75.00},
    {"district":"Patiala","state":"Punjab","latMin":30.25,"latMax":30.50,"lonMin":76.30,"lonMax":76.55},
    {"district":"Ambala","state":"Haryana","latMin":30.30,"latMax":30.50,"lonMin":76.75,"lonMax":77.00},
    {"district":"Rohtak","state":"Haryana","latMin":28.80,"latMax":29.00,"lonMin":76.50,"lonMax":76.75},
    {"district":"Hisar","state":"Haryana","latMin":29.10,"latMax":29.35,"lonMin":75.65,"lonMax":75.95},
    {"district":"Delhi","state":"Delhi NCR","latMin":28.40,"latMax":28.80,"lonMin":76.85,"lonMax":77.30},
    {"district":"Gurugram","state":"Haryana","latMin":28.35,"latMax":28.55,"lonMin":76.90,"lonMax":77.15},
    {"district":"Faridabad","state":"Haryana","latMin":28.30,"latMax":28.50,"lonMin":77.20,"lonMax":77.40},
    {"district":"Nainital","state":"Uttarakhand","latMin":29.30,"latMax":29.60,"lonMin":79.35,"lonMax":79.75},
    {"district":"Dehradun","state":"Uttarakhand","latMin":30.25,"latMax":30.50,"lonMin":77.90,"lonMax":78.20},
    {"district":"Jaipur","state":"Rajasthan","latMin":26.85,"latMax":27.10,"lonMin":75.70,"lonMax":76.00},
    {"district":"Kota","state":"Rajasthan","latMin":25.10,"latMax":25.30,"lonMin":75.80,"lonMax":76.00},
    {"district":"Udaipur","state":"Rajasthan","latMin":24.50,"latMax":24.70,"lonMin":73.60,"lonMax":73.85},
    {"district":"Chittorgarh","state":"Rajasthan","latMin":24.80,"latMax":25.10,"lonMin":74.50,"lonMax":74.80},
    {"district":"Bilaspur","state":"Chhattisgarh","latMin":22.00,"latMax":22.30,"lonMin":82.00,"lonMax":82.40},
    {"district":"Korba","state":"Chhattisgarh","latMin":22.20,"latMax":22.55,"lonMin":82.50,"lonMax":82.90},
]

ALERT_THRESHOLDS = {
    "readiness_critical": 80, "readiness_high": 60, "readiness_moderate": 40,
    "risk_score_critical": 90, "risk_score_high": 70,
    "detection_spike_pct": 50, "trend_growing_slope": 500,
}


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371
    dlat, dlon = math.radians(lat2-lat1), math.radians(lon2-lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))


def assign_district(lat, lon):
    best, best_dist = None, float('inf')
    for d in DISTRICT_MAP:
        if d["latMin"] <= lat <= d["latMax"] and d["lonMin"] <= lon <= d["lonMax"]:
            cx, cy = (d["latMin"]+d["latMax"])/2, (d["lonMin"]+d["lonMax"])/2
            dist = haversine_km(lat, lon, cx, cy)
            if dist < best_dist:
                best, best_dist = d, dist
    if best:
        return best["district"], best["state"]
    for d in DISTRICT_MAP:
        cx, cy = (d["latMin"]+d["latMax"])/2, (d["lonMin"]+d["lonMax"])/2
        dist = haversine_km(lat, lon, cx, cy)
        if dist < best_dist:
            best, best_dist = d, dist
    if best and best_dist < 200:
        return best["district"], best["state"]
    return "Unknown", "Unknown"


def _merge_fire_type(firms):
    """Merge fire type labels onto FIRMS data."""
    ft = pd.read_csv(FIRE_TYPE_FILE)
    firms = firms.copy()
    firms["grid_id"] = firms["latitude"].round(2).astype(str) + "_" + firms["longitude"].round(2).astype(str)
    firms = firms.merge(ft[["grid_id","fire_type"]], on="grid_id", how="left")
    firms["fire_type"] = firms["fire_type"].fillna("UNCLASSIFIED")
    return firms


def load_data():
    print("[forecast] Loading data...")
    firms = pd.read_csv(FIRMS_FILE, low_memory=False)
    firms["acq_date"] = pd.to_datetime(firms["acq_date"])
    firms["year"] = firms["acq_date"].dt.year
    firms["month"] = firms["acq_date"].dt.month
    grid = pd.read_csv(GRID_FILE)
    fire_type = pd.read_csv(FIRE_TYPE_FILE)
    return firms, grid, fire_type


def compute_monthly_patterns(firms):
    print("[forecast] Monthly patterns...")
    monthly = firms.groupby(["year","month"]).agg(detections=("frp","count"),avg_frp=("frp","mean"),max_frp=("frp","max")).reset_index()
    mavg = monthly.groupby("month").agg(avg_detections=("detections","mean"),std_detections=("detections","std"),avg_frp=("avg_frp","mean"),max_frp=("max_frp","max")).reset_index()
    mx = mavg["avg_detections"].max()
    mavg["intensity_pct"] = (mavg["avg_detections"]/mx*100).round(1) if mx > 0 else 0
    return mavg.to_dict("records")


def compute_monthly_patterns_by_type(firms):
    print("[forecast] Monthly patterns by fire type...")
    fm = _merge_fire_type(firms)
    result = {}
    for ftype in fm["fire_type"].unique():
        fdf = fm[fm["fire_type"]==ftype]
        monthly = fdf.groupby(["year","month"]).agg(detections=("frp","count"),avg_frp=("frp","mean")).reset_index()
        mavg = monthly.groupby("month").agg(avg_detections=("detections","mean"),avg_frp=("avg_frp","mean")).reset_index()
        mx = mavg["avg_detections"].max() if not mavg.empty else 1
        mavg["intensity_pct"] = (mavg["avg_detections"]/mx*100).round(1) if mx > 0 else 0
        result[ftype] = {"monthly_patterns":mavg.to_dict("records"),"total_detections":int(len(fdf)),"unique_grids":int(fdf["grid_id"].nunique())}
    return result


def compute_seasonal_analysis(firms):
    print("[forecast] Seasonal analysis...")
    yearly = firms.groupby(["year","month"]).size().reset_index(name="detections")
    result = {}
    for year in sorted(yearly["year"].unique()):
        yd = yearly[yearly["year"]==year]
        result[int(year)] = {}
        for sn, sm in FIRE_SEASON_MONTHS.items():
            result[int(year)][sn] = int(yd[yd["month"].isin(sm)]["detections"].sum())
    return result


def compute_seasonal_by_type(firms):
    print("[forecast] Seasonal by fire type...")
    fm = _merge_fire_type(firms)
    result = {}
    for ftype in fm["fire_type"].unique():
        fdf = fm[fm["fire_type"]==ftype]
        yearly = fdf.groupby(["year","month"]).size().reset_index(name="detections")
        seasons = {}
        for year in sorted(yearly["year"].unique()):
            yd = yearly[yearly["year"]==year]
            seasons[int(year)] = {}
            for sn, sm in FIRE_SEASON_MONTHS.items():
                seasons[int(year)][sn] = int(yd[yd["month"].isin(sm)]["detections"].sum())
        result[ftype] = seasons
    return result


def compute_yearly_trend(firms):
    print("[forecast] Yearly trends...")
    yearly = firms.groupby("year").agg(total_detections=("frp","count"),avg_frp=("frp","mean")).reset_index().sort_values("year")
    if len(yearly)<3: return {"trend":"insufficient_data","slope":0,"years":[]}
    yd = [{"year":int(r["year"]),"detections":int(r["total_detections"]),"avg_frp":round(float(r["avg_frp"]),2)} for _,r in yearly.iterrows()]
    x=np.array(yearly["year"],dtype=float); y=np.array(yearly["total_detections"],dtype=float)
    slope=float(np.polyfit(x,y,1)[0])
    if slope>500: t="GROWING"
    elif slope<-500: t="DECLINING"
    else: t="STABLE"
    return {"trend":t,"slope":round(slope,1),"years":yd}


def compute_yearly_trend_by_type(firms):
    print("[forecast] Yearly trend by fire type...")
    fm = _merge_fire_type(firms)
    result = {}
    for ftype in fm["fire_type"].unique():
        fdf = fm[fm["fire_type"]==ftype]
        yearly = fdf.groupby("year").agg(total_detections=("frp","count")).reset_index().sort_values("year")
        if len(yearly) < 3:
            result[ftype] = {"trend":"insufficient_data","slope":0,"years":[]}
            continue
        yd = [{"year":int(r["year"]),"detections":int(r["total_detections"])} for _,r in yearly.iterrows()]
        x=np.array(yearly["year"],dtype=float); y=np.array(yearly["total_detections"],dtype=float)
        slope=float(np.polyfit(x,y,1)[0])
        if slope>200: t="GROWING"
        elif slope<-200: t="DECLINING"
        else: t="STABLE"
        result[ftype] = {"trend":t,"slope":round(slope,1),"years":yd}
    return result


def compute_monthly_heatmap(firms):
    print("[forecast] Heatmap...")
    pv = firms.groupby(["year","month"]).size().reset_index(name="detections")
    pt = pv.pivot(index="year",columns="month",values="detections").fillna(0)
    mx = pt.max().max()
    nm = (pt/mx*100).round(1) if mx>0 else pt
    hm = []
    for yr in sorted(nm.index):
        r = {"year":int(yr)}
        for m in range(1,13):
            r[str(m)] = float(nm.loc[yr,m]) if m in nm.columns else 0
            r["raw_"+str(m)] = int(pt.loc[yr,m]) if m in pt.columns else 0
        hm.append(r)
    return hm


def compute_grid_forecast(firms, grid, fire_type):
    print("[forecast] Grid forecasts...")
    firms = firms.copy()
    firms["grid_id"] = firms["latitude"].round(2).astype(str) + "_" + firms["longitude"].round(2).astype(str)
    gm = firms.groupby(["grid_id","month"]).size().reset_index(name="detections")
    risk = pd.read_csv(os.path.join(DATA_DIR, "risk_predictions.csv"))
    gi = grid[["grid_id","latitude","longitude","seasonal_peak","seasonality_strength"]].copy()
    gi = gi.merge(risk[["grid_id","risk_score"]], on="grid_id", how="left")
    gi = gi.merge(fire_type[["grid_id","fire_type","display_site_name"]], on="grid_id", how="left")
    fc = []
    for _,g in gi.iterrows():
        gd = gm[gm["grid_id"]==g["grid_id"]]
        if gd.empty: continue
        mp = {}
        for m in range(1,13):
            md = gd[gd["month"]==m]["detections"]
            mp[str(m)] = round(float(md.mean()),1) if len(md)>0 else 0
        pk = max(mp, key=lambda k: mp[k])
        fc.append({"grid_id":g["grid_id"],"lat":round(float(g["latitude"]),4),"lon":round(float(g["longitude"]),4),
            "fire_type":str(g.get("fire_type","UNKNOWN")),"site_name":str(g.get("display_site_name",g["grid_id"])),
            "seasonality":round(float(g.get("seasonality_strength",0)),2),
            "peak_month":MONTH_NAMES[int(pk)-1],"peak_month_num":int(pk),"monthly":mp,
            "season_totals":{"pre_monsoon":round(sum(mp.get(str(m),0) for m in[3,4,5]),1),
                "monsoon":round(sum(mp.get(str(m),0) for m in[6,7,8]),1),
                "post_monsoon":round(sum(mp.get(str(m),0) for m in[9,10,11]),1),
                "winter":round(sum(mp.get(str(m),0) for m in[12,1,2]),1)},
            "risk_score":round(float(g.get("risk_score",0)),1)})
    fc.sort(key=lambda x: x["risk_score"], reverse=True)
    return fc[:200]


def compute_readiness_index(mp, yt):
    pi = max(p["intensity_pct"] for p in mp) if mp else 50
    f1 = pi*0.4
    sl = yt.get("slope",0)
    if sl>2000: f2=30
    elif sl>1000: f2=22
    elif sl>0: f2=15
    elif sl>-1000: f2=10
    else: f2=5
    hm = sum(1 for p in mp if p["intensity_pct"]>50)
    f3 = min(hm*5,30)
    idx = min(100,round(f1+f2+f3))
    if idx>=80: lv,cl="CRITICAL","#ff382f"
    elif idx>=60: lv,cl="HIGH","#ff6b1a"
    elif idx>=40: lv,cl="MODERATE","#ffae42"
    else: lv,cl="LOW","#20e889"
    return {"score":idx,"level":lv,"color":cl}


def compute_type_readiness(type_data):
    result = {}
    for ftype, data in type_data.items():
        mp = data["monthly_patterns"]
        peak = max((d["intensity_pct"] for d in mp), default=0) if mp else 0
        high_months = sum(1 for d in mp if d["intensity_pct"] > 40)
        score = min(100, round(peak * 0.5 + high_months * 8))
        if score >= 80: lv, cl = "CRITICAL", "#ff382f"
        elif score >= 60: lv, cl = "HIGH", "#ff6b1a"
        elif score >= 40: lv, cl = "MODERATE", "#ffae42"
        else: lv, cl = "LOW", "#20e889"
        result[ftype] = {"score":score,"level":lv,"color":cl,"total_detections":data["total_detections"],"unique_grids":data["unique_grids"]}
    return result


def compute_forecast_summary(mp, yt, hm):
    print("[forecast] Summary...")
    cy,ny=2026,2027
    cd = next((h for h in hm if h["year"]==cy),None)
    sl=yt.get("slope",0)
    tc = sum(cd.get(str(m),0) for m in range(1,13)) if cd else 0
    tp = max(0,tc+sl)
    ma = {str(m+1):p["intensity_pct"] for m,p in enumerate(mp)}
    pk3 = sorted(ma.items(),key=lambda x:x[1],reverse=True)[:3]
    lo3 = sorted(ma.items(),key=lambda x:x[1])[:3]
    return {"current_year":cy,"next_year":ny,"current_total_detections":round(tc),
        "predicted_total_detections":round(tp),"trend":yt.get("trend","UNKNOWN"),
        "trend_pct":round((sl/max(tc,1))*100,1),
        "peak_months":[{"month":MONTH_NAMES[int(m)-1],"intensity":round(v,1)} for m,v in pk3],
        "low_months":[{"month":MONTH_NAMES[int(m)-1],"intensity":round(v,1)} for m,v in lo3],
        "readiness_index":compute_readiness_index(mp,yt)}


def compute_district_forecast(grid_forecasts):
    print("[forecast] District forecasts...")
    districts = {}
    for g in grid_forecasts:
        lat, lon = g["lat"], g["lon"]
        dist, state = assign_district(lat, lon)
        key = dist+"|"+state
        if key not in districts:
            districts[key] = {"district":dist,"state":state,"grids":[],"total_risk":0,"fire_types":{},"peak_months":[],"total_detections":0}
        d = districts[key]
        d["grids"].append(g["grid_id"])
        d["total_risk"] += g["risk_score"]
        d["total_detections"] += sum(g["monthly"].values())
        ft = g["fire_type"]
        d["fire_types"][ft] = d["fire_types"].get(ft, 0) + 1
        d["peak_months"].append(g["peak_month"])

    result = []
    for key, d in districts.items():
        n = len(d["grids"])
        avg_risk = round(d["total_risk"] / n, 1) if n > 0 else 0
        top_fire_type = max(d["fire_types"], key=d["fire_types"].get) if d["fire_types"] else "UNKNOWN"
        peak_month = Counter(d["peak_months"]).most_common(1)[0][0] if d["peak_months"] else "N/A"
        score = min(100, round(avg_risk * 0.6 + n * 2 + (d["total_detections"] / 100)))
        if score >= 80: lv, cl = "CRITICAL", "#ff382f"
        elif score >= 60: lv, cl = "HIGH", "#ff6b1a"
        elif score >= 40: lv, cl = "MODERATE", "#ffae42"
        else: lv, cl = "LOW", "#20e889"
        result.append({"district":d["district"],"state":d["state"],"n_grids":n,"avg_risk":avg_risk,
            "top_fire_type":top_fire_type,"peak_month":peak_month,
            "total_detections":round(d["total_detections"]),
            "readiness":{"score":score,"level":lv,"color":cl},"fire_type_dist":d["fire_types"]})
    result.sort(key=lambda x: x["readiness"]["score"], reverse=True)
    return result


def _get_type_actions(ftype):
    m = {
        "INDUSTRIAL_PERSISTENT":["Inspect all identified industrial facilities for compliance","Issue show-cause notices to non-compliant units","Increase CPCB/SPCB monitoring frequency","Deploy continuous air quality monitors","Review environmental clearance documents"],
        "AGRICULTURAL_BURNING":["Deploy satellite-based stubble burning surveillance","Issue FIRs against identified violators","Promote Happy Seeder and crop residue management","Activate village-level fire watchers","Coordinate with agriculture dept for alternatives"],
        "FOREST_WILDFIRE":["Deploy forest fire monitoring teams","Clear fire breaks in vulnerable areas","Activate community fire watchers (Van Suraksha Samiti)","Deploy aerial water tankers if available","Issue NDMA fire safety advisory to nearby villages"],
        "UNCLASSIFIED":["Conduct ground-truth survey for unclassified fire sources","Deploy drone reconnaissance for remote areas","Cross-reference with industrial and mining databases"],
    }
    return m.get(ftype, ["Investigate and classify fire source"])


def _get_type_agencies(ftype):
    m = {
        "INDUSTRIAL_PERSISTENT":["CPCB","SPCB","NGT","District Admin","Police"],
        "AGRICULTURAL_BURNING":["District Admin","Agriculture Dept","Police","SPCB"],
        "FOREST_WILDFIRE":["Forest Dept","NDRF","SDRF","ITF"],
        "UNCLASSIFIED":["District Admin","Revenue Dept"],
    }
    return m.get(ftype, ["District Admin"])


def compute_alert_escalation(summary, type_readiness, district_forecasts):
    print("[forecast] Alert escalation...")
    alerts = []
    th = ALERT_THRESHOLDS
    ri = summary.get("readiness_index", {})

    # Overall readiness
    if ri.get("score",0) >= th["readiness_critical"]:
        alerts.append({"severity":"CRITICAL","color":"#ff382f","icon":"🔴","title":"Overall Fire Season Readiness: "+str(ri['score'])+"/100",
            "description":"Fire season readiness is CRITICAL ("+str(ri['level'])+"). Immediate preparedness required.","category":"readiness",
            "actions":["Activate emergency response protocols","Deploy additional firefighting resources to high-risk zones","Issue public advisory for fire prevention","Coordinate with NDRF and State Disaster Response Force"],
            "agencies":["NDMA","NDRF","SDRF","Forest Dept"]})
    elif ri.get("score",0) >= th["readiness_high"]:
        alerts.append({"severity":"HIGH","color":"#ff6b1a","icon":"🟠","title":"Overall Fire Season Readiness: "+str(ri['score'])+"/100",
            "description":"Fire season readiness is HIGH. Enhanced monitoring recommended.","category":"readiness",
            "actions":["Increase satellite monitoring frequency","Pre-position firefighting equipment","Issue early warning to at-risk communities"],
            "agencies":["Forest Dept","SPCB","District Admin"]})

    # Per-fire-type
    type_labels = {"INDUSTRIAL_PERSISTENT":"Industrial Persistent Fires","AGRICULTURAL_BURNING":"Agricultural/Stubble Burning","FOREST_WILDFIRE":"Forest Wildfires","UNCLASSIFIED":"Unclassified Fire Sources"}
    for ftype, r in type_readiness.items():
        label = type_labels.get(ftype, ftype)
        if r["score"] >= th["readiness_critical"]:
            alerts.append({"severity":"CRITICAL","color":"#ff382f","icon":"🔴","title":label+": Readiness "+str(r['score'])+"/100",
                "description":str(r['total_detections'])+" detections across "+str(r['unique_grids'])+" grid cells. Peak intensity is critical.",
                "category":"fire_type_"+ftype,"actions":_get_type_actions(ftype),"agencies":_get_type_agencies(ftype)})
        elif r["score"] >= th["readiness_high"]:
            alerts.append({"severity":"HIGH","color":"#ff6b1a","icon":"🟠","title":label+": Readiness "+str(r['score'])+"/100",
                "description":str(r['total_detections'])+" detections. Enhanced monitoring needed.",
                "category":"fire_type_"+ftype,"actions":_get_type_actions(ftype)[:3],"agencies":_get_type_agencies(ftype)[:2]})

    # District-level
    for d in district_forecasts[:10]:
        if d["readiness"]["score"] >= th["readiness_critical"]:
            alerts.append({"severity":"CRITICAL","color":"#ff382f","icon":"🔴",
                "title":d["district"]+", "+d["state"]+": Readiness "+str(d['readiness']['score'])+"/100",
                "description":str(d['n_grids'])+" high-risk grid cells, avg risk "+str(d['avg_risk'])+". Top type: "+d['top_fire_type']+".",
                "category":"district_"+d["district"],
                "actions":["Deploy rapid response teams to "+d["district"],"Issue red alert for "+d["state"]+" fire department","Activate community fire watch volunteers","Coordinate industrial shutdown if applicable"],
                "agencies":["District Admin","Fire Dept","SPCB","NDRF"]})
        elif d["readiness"]["score"] >= th["readiness_high"]:
            alerts.append({"severity":"HIGH","color":"#ff6b1a","icon":"🟠",
                "title":d["district"]+", "+d["state"]+": Readiness "+str(d['readiness']['score'])+"/100",
                "description":str(d['n_grids'])+" grid cells at elevated risk. Avg risk: "+str(d['avg_risk'])+".",
                "category":"district_"+d["district"],
                "actions":["Increase patrols in "+d["district"],"Issue yellow alert for fire services"],
                "agencies":["District Admin","Fire Dept"]})

    # Trend alert
    if summary.get("trend") == "GROWING" and summary.get("trend_pct", 0) > 10:
        alerts.append({"severity":"HIGH","color":"#ff6b1a","icon":"📈",
            "title":"Fire Activity Growing: +"+str(summary['trend_pct'])+"% Year-over-Year",
            "description":"Trend slope indicates consistently increasing fire detections. Predicted "+f"{summary.get('predicted_total_detections',0):,} "+" detections for "+str(summary.get('next_year',2027))+".",
            "category":"trend",
            "actions":["Review and update fire management plans","Increase budget allocation for fire prevention","Deploy additional early warning systems","Coordinate inter-state fire management"],
            "agencies":["NDMA","Forest Dept","Ministry of Environment"]})

    sev_order = {"CRITICAL": 0, "HIGH": 1, "MODERATE": 2, "LOW": 3}
    alerts.sort(key=lambda x: sev_order.get(x["severity"], 99))
    return alerts


def generate_forecast():
    firms, grid, ft = load_data()

    mp = compute_monthly_patterns(firms)
    sa = compute_seasonal_analysis(firms)
    yt = compute_yearly_trend(firms)
    hm = compute_monthly_heatmap(firms)
    gf = compute_grid_forecast(firms, grid, ft)
    sm = compute_forecast_summary(mp, yt, hm)

    mp_type = compute_monthly_patterns_by_type(firms)
    sa_type = compute_seasonal_by_type(firms)
    yt_type = compute_yearly_trend_by_type(firms)
    ri_type = compute_type_readiness(mp_type)

    district_fc = compute_district_forecast(gf)
    alerts = compute_alert_escalation(sm, ri_type, district_fc)

    fd = {
        "monthly_patterns":mp, "seasonal_by_year":sa, "yearly_trend":yt, "monthly_heatmap":hm,
        "grid_forecasts":gf, "summary":sm, "month_names":MONTH_NAMES,
        "by_type":{"monthly_patterns":{k:v["monthly_patterns"] for k,v in mp_type.items()},
            "seasonal_by_year":sa_type, "yearly_trend":yt_type, "readiness":ri_type,
            "type_totals":{k:{"detections":v["total_detections"],"grids":v["unique_grids"]} for k,v in mp_type.items()}},
        "districts":district_fc,
        "escalation_alerts":alerts,
    }

    with open(OUTPUT_FILE,"w") as f:
        json.dump(fd,f)
    print("[forecast] Saved to "+OUTPUT_FILE)
    print("  Overall: "+str(sm['readiness_index']['score'])+"/100 ("+sm['readiness_index']['level']+")")
    print("  Per-type readiness: "+json.dumps({k:v['score'] for k,v in ri_type.items()}))
    print("  Districts: "+str(len(district_fc))+" | Alerts: "+str(len(alerts)))
    return fd


if __name__ == "__main__":
    generate_forecast()
