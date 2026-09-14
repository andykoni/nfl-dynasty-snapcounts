import json, re, unicodedata
from pathlib import Path
from urllib.parse import urlparse
import requests
import nflreadpy as nfl

ROOT = Path(__file__).resolve().parents[1]
CFG = json.loads((ROOT/"config.json").read_text())
YEAR = CFG["season"]

def as_list(x):
    if x is None: return []
    return x if isinstance(x,list) else [x]

def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii","ignore").decode().lower()
    return re.sub(r"[^a-z0-9]","",s)

def mfl_export_url(league_url):
    p=urlparse(league_url)
    return f"{p.scheme}://{p.netloc}/{YEAR}/export"

def mfl_roster(league):
    params={"TYPE":"rosters","L":league["league_id"],"FRANCHISE":league["franchise_id"],"JSON":1}
    r=requests.get(mfl_export_url(league["url"]),params=params,timeout=30,headers={"User-Agent":"NFL Dynasty Snap Dashboard"})
    r.raise_for_status()
    j=r.json()
    franchises=as_list(j.get("rosters",{}).get("franchise"))
    if not franchises: raise RuntimeError(f"No roster returned for {league['name']}: {j}")
    f=franchises[0]
    players=as_list(f.get("player"))
    out=[]
    for p in players:
        if isinstance(p,str): out.append({"id":p,"status":"ROSTER"})
        else: out.append({"id":str(p.get("id")),"status":p.get("status","ROSTER")})
    return out

# Current MFL player IDs are the stable ownership key.
roster_records=[]
for league in CFG["leagues"]:
    for p in mfl_roster(league):
        roster_records.append({**p,"league":league["name"]})

ids = nfl.load_ff_playerids().to_pandas()
snaps = nfl.load_snap_counts(seasons=[YEAR]).to_pandas()

# Normalise crosswalk column names.
ids.columns=[str(c) for c in ids.columns]
snaps.columns=[str(c) for c in snaps.columns]
mfl_col = next(c for c in ids.columns if c.lower()=="mfl_id")
pfr_col = next(c for c in ids.columns if c.lower() in ("pfr_id","pfr_player_id"))
name_col = next(c for c in ids.columns if c.lower()=="name")
pos_col = next((c for c in ids.columns if c.lower()=="position"), None)

ids[mfl_col]=ids[mfl_col].astype(str)
ids[pfr_col]=ids[pfr_col].fillna("").astype(str)
snaps["pfr_player_id"]=snaps["pfr_player_id"].fillna("").astype(str)

cross = ids[[mfl_col,pfr_col,name_col] + ([pos_col] if pos_col else [])].copy()
cross["mfl_key"]=cross[mfl_col].str.replace(r"\.0$","",regex=True)
cross=cross[cross["mfl_key"].ne("nan")]

# Join current rosters to nflverse snap data through MFL -> PFR IDs.
roster_df = __import__("pandas").DataFrame(roster_records)
roster_df["mfl_key"]=roster_df["id"].astype(str)
roster_df=roster_df.merge(cross,left_on="mfl_key",right_on="mfl_key",how="left")
roster_df["player"]=roster_df[name_col].fillna("Unknown")
roster_df["position"]=roster_df[pos_col].fillna("") if pos_col else ""
roster_df["unit"]=roster_df["position"].map(lambda x: "IDP" if x in {"DT","DE","LB","CB","S","DB","DL"} else "Offense")

# Current NFL snap rows for the latest completed week available in nflverse.
snaps["week_num"]=__import__("pandas").to_numeric(snaps["week"],errors="coerce")
latest=int(snaps["week_num"].max())
latest_snaps=snaps[snaps["week_num"].eq(latest)].copy()
latest_snaps["pfr_player_id"]=latest_snaps["pfr_player_id"].astype(str)

# Historical rows, keyed by PFR player id and week.
history={}
for _,r in snaps.iterrows():
    pid=str(r.get("pfr_player_id",""))
    if not pid: continue
    history.setdefault(pid,[]).append({
        "week":int(r["week_num"]),
        "team":str(r.get("team","")),
        "offense_snaps":int(r.get("offense_snaps",0) or 0),
        "offense_pct":float(r.get("offense_pct",0) or 0)*100,
        "defense_snaps":int(r.get("defense_snaps",0) or 0),
        "defense_pct":float(r.get("defense_pct",0) or 0)*100,
        "st_snaps":int(r.get("st_snaps",0) or 0),
        "st_pct":float(r.get("st_pct",0) or 0)*100
    })

# Consolidate duplicate ownership across leagues.
current={}
for _,r in roster_df.iterrows():
    key=str(r.get("mfl_key"))
    current.setdefault(key,{"player_id":key,"player":r["player"],"position":r["position"],"team":"",
                           "unit":r["unit"],"leagues":[],"status":[]})
    if r["league"] not in current[key]["leagues"]: current[key]["leagues"].append(r["league"])
    current[key]["status"].append({"league":r["league"],"status":r["status"]})

# Add latest snap usage.
for key,x in current.items():
    rr=roster_df[roster_df["mfl_key"].eq(key)].iloc[0]
    pfr=str(rr.get(pfr_col,""))
    rows=latest_snaps[latest_snaps["pfr_player_id"].eq(pfr)]
    if len(rows):
        s=rows.iloc[0]
        x["team"]=str(s.get("team",""))
        if x["unit"]=="IDP":
            x["snaps"]=int(s.get("defense_snaps",0) or 0); x["pct"]=float(s.get("defense_pct",0) or 0)*100
        else:
            x["snaps"]=int(s.get("offense_snaps",0) or 0); x["pct"]=float(s.get("offense_pct",0) or 0)*100
        h=history.get(pfr,[])
        h=sorted(h,key=lambda z:z["week"])
        vals=[(z["defense_pct"] if x["unit"]=="IDP" else z["offense_pct"]) for z in h][-3:]
        x["trend"]=0 if len(vals)<2 else (1 if vals[-1]>vals[-2]+5 else (-1 if vals[-1]<vals[-2]-5 else 0))
    else:
        x["snaps"]=None; x["pct"]=None; x["trend"]=0

payload={
 "season":YEAR,"week":latest,
 "updated_at":__import__("datetime").datetime.utcnow().replace(microsecond=0).isoformat()+"Z",
 "status":"Live data",
 "leagues":[x["name"] for x in CFG["leagues"]],
 "current":list(current.values()),
 "history":history
}
(ROOT/"data.json").write_text(json.dumps(payload,indent=2,default=str),encoding="utf-8")
print(f"Updated {len(current)} current players across {len(CFG['leagues'])} leagues; latest week={latest}")
