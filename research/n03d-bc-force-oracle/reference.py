"""BC OpenSim true independently captured GRF/kinematics reference.

Computes force-defined contact state on the model's OWN walking trial.
Never equates 100STYLE or MPFB scene floor with this separate trial.
"""
import bisect,hashlib,json,math,statistics,xml.etree.ElementTree as ET
from pathlib import Path
from urllib.request import Request,urlopen

UPSTREAM="opensim-org/opensim-core"
COMMIT="f67ee67fa4b9de89ff8bb9466f131e52acd8b0b6"
FILES={
 "force":("OpenSim/Examples/Moco/example3DWalking/grf_walk.mot","cd7379619d840e25dfdf6777aedb88816154420f"),
 "coordinates":("OpenSim/Examples/Moco/example3DWalking/coordinates.sto","79fc9932e51d65660b27ea2983c92de6266a7d7d"),
 "model":("OpenSim/Examples/Moco/example3DWalking/subject_walk_scaled.osim","99857a5df135592f9d3078d9665111d1a63131d7")
}
def need(ok,msg):
    if not ok:raise ValueError(msg)
def hashblob(data):
    return hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()
def acquire(to):
    to=Path(to);to.mkdir(exist_ok=True,parents=True);out={}
    for key,(path,expected) in FILES.items():
        url=f"https://raw.githubusercontent.com/{UPSTREAM}/{COMMIT}/{path}"
        data=urlopen(Request(url,headers={"User-Agent":"SCP-BC-science-audit"}),timeout=90).read()
        need(hashblob(data)==expected,"OPENSIM_BLOB_PIN_"+key)
        (to/(key+Path(path).suffix)).write_bytes(data)
        out[key]={"original_git_blob":expected,"sha256":hashlib.sha256(data).hexdigest(),"bytes":len(data)}
    return out
def parse_storage(text):
    lines=[s.strip() for s in text.splitlines() if s.strip()]
    try: n=next(i for i,s in enumerate(lines) if s.lower()=="endheader")
    except StopIteration:raise ValueError("MISSING_ENDHEADER")
    info={}
    for row in lines[:n]:
        if "=" in row:
            k,v=row.split("=",1);info[k.lower()]=v
    columns=lines[n+1].split()
    need(columns[0]=="time" and len(set(columns))==len(columns),"STORAGE_COLUMNS")
    rows=[]
    for line in lines[n+2:]:
        value=[float(v) for v in line.split()]
        need(len(value)==len(columns) and
             all(math.isfinite(v) and abs(v)<1e8 for v in value),"STORAGE_NONFINITE_OR_WIDTH")
        rows.append(value)
    need(len(rows)>50 and int(info.get("nrows",0))==len(rows),"HEADER_ROWS")
    declared=int(info.get("ncolumns",0))
    need(declared>0,"HEADER_NCOLUMNS_MISSING")
    info["observedcolumns"]=str(len(columns))
    info["headercolumnsmatch"]=str(declared==len(columns))
    need(all(rows[i+1][0]>rows[i][0] for i in range(len(rows)-1)),"STORAGE_TIME_NOT_STRICT")
    return {"columns":columns,"rows":rows,"metadata":info}
def interpolate(t,col,storage):
    times=[row[0] for row in storage["rows"]]
    need(times[0]<=t<=times[-1],"OUT_OF_SOURCE_WINDOW")
    i=bisect.bisect_right(times,t)-1
    if i==len(times)-1:return storage["rows"][i][col]
    lo,hi=storage["rows"][i],storage["rows"][i+1]
    alpha=(t-lo[0])/(hi[0]-lo[0])
    return lo[col]*(1-alpha)+hi[col]*alpha
def read_model(text):
    root=ET.fromstring(text)
    need(root.tag=="OpenSimDocument","OPEN_SIM_MODEL_ROOT")
    model=root.find("Model")
    need(model is not None and model.get("name")=="subject_walk_scaled","MODEL_NAME")
    count={}
    for e in root.iter():
        key=e.tag.rsplit("}",1)[-1]
        if key in ("Body","Coordinate","Millard2012EquilibriumMuscle",
                   "Thelen2003Muscle","DeGrooteFregly2016Muscle",
                   "HuntCrossleyForce","SmoothSphereHalfSpaceForce",
                   "ContactSphere","ContactHalfSpace","WeldJoint","PinJoint","CustomJoint"):
            count[key]=count.get(key,0)+1
    need(count.get("Body",0)>=10 and count.get("Coordinate",0)>=15,"MODEL_BIOMECHANICS_STRUCTURE")
    return {"model_name":model.attrib.get("name"),"model_components":count,
            "model_ground_reference":True,"true_anatomical_R_O_M_certified":False}
def ratio(x):
    return round(sum(bool(a) for a in x)/len(x),6) if x else None
def events(states):
    return sum(states[i] and not states[i-1] for i in range(1,len(states)))
def evaluate(grf,coord,model,receipts):
    need(set(grf["columns"])>=set(["time","ground_force_r_vy","ground_force_l_vy"]),
         "GRF_Y_FORCE_CHANNEL_MISSING")
    name=["/jointset/walker_knee_r/knee_angle_r/value",
          "/jointset/walker_knee_l/knee_angle_l/value",
          "/jointset/ankle_r/ankle_angle_r/value",
          "/jointset/ankle_l/ankle_angle_l/value"]
    need(all(v in coord["columns"] for v in name),"COORDINATE_ANATOMY_MISSING")
    low=max(grf["rows"][0][0],coord["rows"][0][0])
    high=min(grf["rows"][-1][0],coord["rows"][-1][0])
    need(high-low>=.50,"NO_TIME_OVERLAP")
    # Fixed physiological reference grid, only overlap; no fabricated source 100STYLE phases.
    count=int(math.floor((high-low)*60))+1
    time=[low+i/60 for i in range(count)]
    need(len(time)>=30 and time[-1]<=high+1e-7,"NONCONTINUOUS_REFERENCE")
    idx={side:grf["columns"].index("ground_force_"+side+"_vy") for side in ("r","l")}
    force={side:[interpolate(t,idx[side],grf) for t in time] for side in ("r","l")}
    angle={v:[interpolate(t,coord["columns"].index(v),coord) for t in time] for v in name}
    limits={}
    for threshold in (20,50,100):
        left=[v>threshold for v in force["l"]]
        right=[v>threshold for v in force["r"]]
        both=[a and b for a,b in zip(left,right)]
        flight=[not a and not b for a,b in zip(left,right)]
        limits[str(threshold)]={"right_stance_fraction":ratio(right),"left_stance_fraction":ratio(left),
                "double_support_fraction":ratio(both),"no_support_fraction":ratio(flight),
                "right_force_onsets":events(right),"left_force_onsets":events(left),
                "samples":len(time)}
    stats={}
    for v,series in angle.items():
        stats[v.split("/")[-2]+"_"+v.split("/")[-1]]={
            "min_rad":round(min(series),6),"max_rad":round(max(series),6),
            "p50_rad":round(statistics.median(series),6)}
    header_consistent=(coord["metadata"]["headercolumnsmatch"]=="True" and
                       grf["metadata"]["headercolumnsmatch"]=="True")
    return {"schema":"scp.n03d-bc.opensim-60hz-force-scientific-reference.v1",
            "source_repo":UPSTREAM,"exact_commit":COMMIT,
            "source_asset_receipts":receipts,"source_class":"PUBLIC_OPENSIM_REFERENCE_RESEARCH_NOT_RELICENSED",
            "coordinates_metadata":{k:v for k,v in coord["metadata"].items() if k in ("nrows","ncolumns","observedcolumns","headercolumnsmatch","indegrees")},
            "grf_metadata":{k:v for k,v in grf["metadata"].items() if k in ("nrows","ncolumns","observedcolumns","headercolumnsmatch","indegrees")},
            "model":model,"sample_rate_hz":60,"actual_overlap_start_s":round(low,6),
            "actual_overlap_end_s":round(time[-1],6),"overlap_native_sample_count":len(time),
            "vertical_grf_threshold_N_sensitivity":limits,
            "kinematic_joint_ranges":stats,
            "independent_grf_contact_definition":"SOURCE_EXPLICIT_FORCE_Y_THRESHOLD_ONLY",
            "source_contact_known_only_for_this_walk":True,
    "upstream_metadata_all_columns_consistent":header_consistent,
    "source_has_independent_malformed_header_observation":not header_consistent,
            "100style_or_MPF_source_contact_corroborated":False,
            "ground_force_for_protected_actors":False,
            "native_blender_skin_tested":False,
            "physical_MPF_accepted":False,"mvp_accepted":False,
            "status":"PASS_NARROW_GRFS_DATA_RESEARCH_HOLD_CROSS_SOURCE" if header_consistent
        else "HOLD_SOURCE_COORDINATE_HEADER_MISMATCH"}
def independent(r):
    need(r.get("schema")=="scp.n03d-bc.opensim-60hz-force-scientific-reference.v1" and
         r.get("exact_commit")==COMMIT and r.get("source_contact_known_only_for_this_walk") is True and
         r.get("100style_or_MPF_source_contact_corroborated") is False and
         r.get("ground_force_for_protected_actors") is False and
         r.get("native_blender_skin_tested") is False and r.get("physical_MPF_accepted") is False and
         r.get("mvp_accepted") is False,"FALSE_SOURCE_CONTACT_TRANSFER")
    need(r.get("source_has_independent_malformed_header_observation") is not
         r.get("upstream_metadata_all_columns_consistent"),"INCONSISTENT_SOURCE_HEADER_FLAG")
    if not r["upstream_metadata_all_columns_consistent"]:
        need(r.get("status")=="HOLD_SOURCE_COORDINATE_HEADER_MISMATCH",
             "SOURCE_HEADER_FALSE_PASS")
    need(r["sample_rate_hz"]==60 and r["overlap_native_sample_count"]>=30 and
         set(r["vertical_grf_threshold_N_sensitivity"])=={"20","50","100"},
         "MISSING_FORCE_SENSITIVITY")
    for v in r["vertical_grf_threshold_N_sensitivity"].values():
        for n in ("right_stance_fraction","left_stance_fraction","double_support_fraction","no_support_fraction"):
            need(0<=v[n]<=1,"SOURCE_CONTACT_FRACTION")
        need(abs(v["right_stance_fraction"]+v["left_stance_fraction"]-v["double_support_fraction"]+v["no_support_fraction"]-1)<1e-4,
             "INVALID_BINARY_CONTACT_IDENTITY")
    return "HOLD"
def cli():
    import argparse
    a=argparse.ArgumentParser();a.add_argument("--work",required=True);a.add_argument("--output",required=True);args=a.parse_args()
    data=acquire(args.work)
    root=Path(args.work)
    grf=parse_storage((root/"force.mot").read_text())
    coord=parse_storage((root/"coordinates.sto").read_text())
    model=read_model((root/"model.osim").read_text())
    v=evaluate(grf,coord,model,data)
    need(independent(v)=="HOLD","FORCE_CRITIC_INVALID")
    Path(args.output).write_text(json.dumps(v,sort_keys=True,indent=2,allow_nan=False)+"\n")
    print("N03D_BC_OPEN_SIM_REAL_FORCE_REFERENCE",json.dumps({k:z for k,z in v.items() if k!="kinematic_joint_ranges"},sort_keys=True),flush=True)
if __name__=="__main__":cli()
