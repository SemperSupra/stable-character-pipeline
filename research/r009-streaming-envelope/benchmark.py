"""Separate-process equal-output RSS comparison; synthetic input only."""
import argparse
import json
import math
import resource
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from stream_envelope import audit_stream
from paired_envelope import audit,schedule,MARKERS,SCHEMA
WINDOWS=[[50,70]]

def write(path,changed,vertices):
    with open(path,"x") as f:
        def emit(x):f.write(json.dumps(x,separators=(",",":"),allow_nan=False)+"\n")
        emit(dict(schema=SCHEMA,source_class="ORIGINAL_SYNTHETIC",scene_sha256=("b" if changed else "a")*64,
            fps=60,subdiv=32,physical_contact_accepted=False,protected_likeness_used=False))
        for tick in schedule(WINDOWS):
            shift=.03*math.sin(tick/300) if changed else 0
            emit(dict(tick=tick,actors={a:dict(markers={m:[shift if a=="a" else 0,0,1] for m in MARKERS},
                feet={s:{str(i):[i*.0001+(shift if a=="a" and s=="R" else 0),0,0] for i in range(vertices)}
                    for s in ("L","R")}) for a in ("a","b")}))

def worker(mode,a,b,out):
    t=time.perf_counter()
    if mode=="stream":
        with open(a,"rb") as x,open(b,"rb") as y:r=audit_stream(x,y,WINDOWS)
    else:
        def load(path):
            with open(path) as f:
                h=json.loads(next(f));h["rows"]=[json.loads(l) for l in f];return h
        r=audit(load(a),load(b),WINDOWS)
    Path(out).write_text(json.dumps(r,sort_keys=True,allow_nan=False))
    print(json.dumps(dict(mode=mode,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,elapsed_s=time.perf_counter()-t)))

def main():
    if len(sys.argv)>1:worker(*sys.argv[1:]);return
    with tempfile.TemporaryDirectory() as td:
        d=Path(td);a=d/"reference.jsonl";b=d/"candidate.jsonl";vertices=128
        write(a,False,vertices);write(b,True,vertices)
        values=[]
        for mode in ("batch","stream"):
            values.append(json.loads(subprocess.check_output([sys.executable,__file__,mode,str(a),str(b),str(d/(mode+".json"))])))
        assert (d/"batch.json").read_bytes()==(d/"stream.json").read_bytes(),"REPORT_DIFFERENTIAL"
        ratio=values[1]["peak_rss_kib"]/values[0]["peak_rss_kib"]
        assert ratio<.65,(values,ratio)
        print("STREAM_ENVELOPE_BENCHMARK",json.dumps(dict(samples=len(schedule(WINDOWS)),vertices_per_foot=vertices,
            total_vertex_samples=4*vertices*len(schedule(WINDOWS)),input_bytes=a.stat().st_size+b.stat().st_size,
            measurements=values,rss_ratio=ratio,exact_report_equal=True,physical_acceptance=False),sort_keys=True))
if __name__=="__main__":main()
