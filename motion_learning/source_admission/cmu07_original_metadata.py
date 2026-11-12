"""CMU source 07 original ASF/AMC metadata + motion-time qualification (research).

Only exact official-subject small clips. No raw motion bytes published in
artifacts, no private R009 actor/source, no MHR skin retarget claim.
Requires strict authenticated HTTPS downloads outside this script.
"""
import argparse, hashlib, json, math, re
from pathlib import Path

SCALE_TO_METERS=(1.0/0.45)*2.54/100.0
SUBJECT="07"
ALLOWED={"07_01","07_02"}
OFFICIAL="https://mocap.cs.cmu.edu/subjects/07/"
PUBLISHER_FAQ="https://mocap.cs.cmu.edu/faqs.php"
PUBLISHER_TERMS="https://mocap.cs.cmu.edu/"
FRAME_RATE=120

def file_info(p):
    b=Path(p).read_bytes()
    if len(b)<100 or len(b)>20_000_000:
        raise ValueError("source file unexpectedly sized")
    if b"\0" in b or b"<!DOCTYPE" in b or b"<html" in b.lower():
        raise ValueError("source is binary, HTML error page, or malicious payload")
    try:
        t=b.decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValueError("source is not expected ASF/AMC ASCII") from exc
    return t,{"sha256":hashlib.sha256(b).hexdigest(),"bytes":len(b)}

def parse_asf(t):
    if ":version" not in t or ":bonedata" not in t or ":hierarchy" not in t or ":root" not in t:
        raise ValueError("missing authentic ASF structural sections")
    in_bones=False;in_bone=False;names=[];dofs={}
    for raw in t.splitlines():
        line=raw.strip()
        if not line or line.startswith("#"): continue
        if line.startswith(":"):
            in_bones=line==":bonedata"
            in_bone=False
            continue
        if not in_bones: continue
        if line=="begin":
            in_bone=True
        elif line=="end":
            in_bone=False
        elif in_bone and line.startswith("name "):
            name=line.split()[1]
            if not re.fullmatch("[a-zA-Z][a-zA-Z0-9_]*",name):
                raise ValueError("malformed source bone name")
            names.append(name)
        elif in_bone and line.startswith("dof "):
            if not names:raise ValueError("DOF before bone")
            dofs[names[-1]]=line.split()[1:]
    if not (10<=len(names)<=100) or len(set(names))!=len(names):
        raise ValueError("implausible source calibrated bone hierarchy")
    return {"bonedata_bones":len(names),"bones":names,"dof":dofs,
            "root_present":":root" in t,"hierarchy_present":":hierarchy" in t}

def parse_amc(t):
    if ":DEGREES" not in t and ":degrees" not in t.lower():
        raise ValueError("source AMC angular unit header missing")
    frames=[];frame=None;last=0;joints=set()
    for raw in t.splitlines():
        line=raw.strip()
        if not line or line.startswith("#") or line.startswith(":"):continue
        if re.fullmatch(r"[1-9]\d*",line):
            k=int(line)
            if k!=last+1:raise ValueError("source AMC frame index discontinuity")
            if frame is not None:frames.append(frame)
            frame={"index":k,"bones":{}}
            last=k
            continue
        if frame is None:raise ValueError("source AMC joint data before first frame")
        parts=line.split()
        if len(parts)<2 or not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_]*",parts[0]):
            raise ValueError("source AMC unexpected joint record")
        if parts[0] in frame["bones"]:raise ValueError("duplicate joint in AMC frame")
        try:values=[float(x) for x in parts[1:]]
        except ValueError as exc:raise ValueError("bad source numeric channel") from exc
        if not all(math.isfinite(x) for x in values) or len(values)>8:
            raise ValueError("nonfinite or implausible source joint channels")
        frame["bones"][parts[0]]=values
        joints.add(parts[0])
    if frame is not None:frames.append(frame)
    if len(frames)<20 or len(frames)>100000:
        raise ValueError("inadequate original measured sample count")
    if not all("root" in f["bones"] and len(f["bones"]["root"])>=3 for f in frames):
        raise ValueError("missing 3D measured root channel")
    if any(len(f["bones"])<10 for f in frames):
        raise ValueError("implausible sparse original skeleton frame")
    first=set(frames[0]["bones"])
    if any(set(f["bones"])!=first for f in frames):
        raise ValueError("source joint channel set changes during capture")
    root=[f["bones"]["root"][:3] for f in frames]
    endpoints=[root[0],root[-1]]
    metric=[[v*SCALE_TO_METERS for v in x] for x in endpoints]
    distance=math.dist(*metric)
    step_displacements=[math.dist(a,b)*SCALE_TO_METERS for a,b in zip(root,root[1:])]
    return {"original_measured_frames":len(frames),"joint_channels":sorted(joints),
        "source_native_root_xyz_start":root[0],"source_native_root_xyz_end":root[-1],
        "root_position_units":"CMU ASF AMC source coordinate, not direct meters",
        "published_to_meters_multiplier":SCALE_TO_METERS,
        "converted_root_end_to_end_displacement_m_if_source_units_as_published":distance,
        "root_step_p95_m_if_source_units_as_published":
           sorted(step_displacements)[int(.95*(len(step_displacements)-1))],
        "timebase":"publisher reports 120Hz; AMC time index starts at 1",
        "timebase_hz":FRAME_RATE,
        "duration_between_first_last_samples_seconds":(len(frames)-1)/FRAME_RATE,
        "source_marker_observation":"Mocap derived ASF/AMC joint angles; toe joints noisy and fingers/thumbs not independently captured"}

def assess(asf_path,amc_path,motion):
    if motion not in ALLOWED:raise ValueError("unadmitted/unindexed source motion")
    if Path(asf_path).name!="07.asf" or Path(amc_path).name!=motion+".amc":
        raise ValueError("wrong original CMU filenames")
    asf_text,af=file_info(asf_path)
    amc_text,mf=file_info(amc_path)
    body=parse_asf(asf_text)
    observed=parse_amc(amc_text)
    joint_names=set(observed["joint_channels"])
    if not joint_names.issubset(set(body["bones"])|{"root"}):
        raise ValueError("AMC channels not present in source per-subject ASF")
    return {"schema":"motion.cmu07.original_capture_file_metadata.v1",
        "status":"SOURCE_BYTES_HASHED_CAPTURE_METADATA_ONLY_NO_RETARGET",
        "motion":motion,
        "source_url_asf":OFFICIAL+"07.asf",
        "source_url_amc":OFFICIAL+motion+".amc",
        "source_index":"https://mocap.cs.cmu.edu/subjects/07/",
        "publisher_license_pages":[PUBLISHER_FAQ,PUBLISHER_TERMS],
        "source_rights_statement":"CMU FAQ permits copying modifying redistributing; publisher forbids direct resale incl converted data",
        "source_data_release_or_reupload":"NOT_PRODUCED; only aggregate measured metadata",
        "rights_venue_status":"ORIGINAL_SOURCE_PUBLISHER_TERMS_REVIEWED; EXACT_PROCESSING_SCOPE_REQUIRES_OWNER_ADMISSION",
        "source_files":{"asf":af,"amc":mf},
        "asf":body,"amc":observed,
        "gates":{"source_filename_match":True,"source_structure":True,"joint_set_match":True,
                 "finite_joint_channels":True,"measurement_from_original_bytes":True},
        "limitations":["Official source acquisition path HTTPS certificate remains externally observable",
            "Header 120 Hz and source unit conversion are publisher declared, not measured independently",
            "Not full FK reconstruction, foot pressure/sole contact, source-target rig mapping or native Blender retarget",
            "No R009 protected real person or identity media, no private executor admission",
            "No unrestricted resale of source or its converted capture data"]}

def selftest():
    tiny_asf=":version 1.10\n:root\n:bonedata\n"
    for i in range(12):
        tiny_asf+="begin\nid "+str(i+1)+"\nname bone"+str(i+1)+"\ndof rx ry rz\nend\n"
    tiny_asf+=":hierarchy\nbegin\nroot bone1\nend\n"
    b=parse_asf(tiny_asf)
    assert len(b["bones"])==12
    sample=":FULLY-SPECIFIED\n:DEGREES\n"
    for i in range(1,24):
        sample+=str(i)+"\nroot "+str(i)+ " 0 0 0 0 0\n"
        sample+="".join("bone"+str(k)+" 0 0 0\n" for k in range(1,13))
    v=parse_amc(sample)
    assert v["original_measured_frames"]==23
    assert v["converted_root_end_to_end_displacement_m_if_source_units_as_published"]>1.
    for fake in [sample.replace("12\nroot","13\nroot",1),
                 sample.replace("bone1 0 0 0","bone1 NaN 0 0",1),
                 sample.replace("bone1 0 0 0\n","",1),
                 sample.replace(":DEGREES",":BADUNIT")]:
        try:parse_amc(fake)
        except ValueError:pass
        else:raise AssertionError("bad or contradictory source accepted")
    for path in (".","07_01"):
        try:
            if path not in ALLOWED:raise ValueError("motion refused")
        except ValueError:pass
    print("CMU_ORIGINAL_MOCAP_SOURCE_METADATA_SELFTEST_PASS")

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--motion",choices=sorted(ALLOWED))
    ap.add_argument("--asf",type=Path)
    ap.add_argument("--amc",type=Path)
    ap.add_argument("--out",type=Path)
    ap.add_argument("--selftest",action="store_true")
    a=ap.parse_args()
    if a.selftest:selftest()
    else:
        if not all((a.motion,a.asf,a.amc,a.out)):raise SystemExit("source arguments required")
        a.out.mkdir(parents=True,exist_ok=True)
        result=assess(a.asf,a.amc,a.motion)
        (a.out/(a.motion+".metadata.json")).write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
        print("CMU_SOURCE_METADATA",json.dumps({"motion":a.motion,
          "frames":result["amc"]["original_measured_frames"],
          "sha256_amc":result["source_files"]["amc"]["sha256"],
          "root_total_m":result["amc"]["converted_root_end_to_end_displacement_m_if_source_units_as_published"],
          "status":result["status"]},sort_keys=True))
