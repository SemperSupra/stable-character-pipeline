#!/usr/bin/env python3
"""Independent source-only status and negative-control reviewer for exact pinned C1/C5 receipts."""
import hashlib,json,pathlib,subprocess,sys
root=pathlib.Path(sys.argv[1]).resolve()
c1=json.loads((root/"c1.json").read_text())
c5=json.loads((root/"c5"/"time-map.json").read_text())
c8=json.loads((root/"c8.json").read_text())
if not (c1["source_sha256"]=="7294644f1fc26490f8a0aed415afc01b8278294e4373169e1407986c56cb0961" and c1["independent_review"]=="PENDING_SECOND_READER" and c1["music_score_status"]=="NO_NOTATED_SCORE_BYTES_ADMITTED" and c1["physical_motion"]=="UNKNOWN_NOT_MEASURED" and len(c1["phrases"])==7 and c5["source_audio_project_sha256"]=="0e7e1752427569a97e293cb974258db4071e52f3274adfde75fff9cfe706465c" and c5["score_minus_audio_end_samples"]=="128000" and c5["original_source_audio_end_samples"]=="768000" and c5["proposed_score_end_samples"]=="896000" and len(c5["events"])==4 and c8["admission"]=="NOT_ADMITTED" and c8["qualification"]=="PASS_METADATA_NONPROMOTING_ONLY" and c8["score_events"]==4 and "no_cross_source_figure_to_score_alignment" in c8["holds"]):raise AssertionError("real source status or nonpromotion incorrect")
if c8["figure_receipt_sha256"]!=hashlib.sha256((root/"c1.json").read_bytes()).hexdigest() or c8["score_receipt_sha256"]!=hashlib.sha256((root/"c5"/"time-map.json").read_bytes()).hexdigest():raise AssertionError("source receipt digest mismatch")
cli=pathlib.Path("qualification/motion_source_bridge").resolve()
cases=[
 ("false_figure",{"physical_motion":"OBSERVED"},{}),
 ("false_project",{},{"source_audio_project_sha256":"f"*64}),
 ("false_clock",{},{"score_minus_audio_end_samples":"0"}),
]
for name,fig,score in cases:
    f=dict(c1);s=dict(c5);f.update(fig);s.update(score)
    fp=root/(name+"-figure.json");sp=root/(name+"-score.json")
    fp.write_text(json.dumps(f));sp.write_text(json.dumps(s))
    p=subprocess.run(["go","run",".","-figure",str(fp),"-score",str(sp)],cwd=cli,capture_output=True)
    fp.unlink();sp.unlink()
    if p.returncode==0:raise AssertionError("falsified source accepted "+name)
(root/"independent.json").write_text(json.dumps({"schema":"scp.c8.actual-pinned-public-review.v0","figure_cues":7,"synthetic_event_count":4,"negative_controls":["false_figure","false_project","false_clock"],"status":"PASS_METADATA_NONPROMOTING_ONLY","historical_score":"UNKNOWN_NOT_ADMITTED","physical_motion":"NOT_RUN","R009":"HELD_NOT_ACCEPTED"},sort_keys=True,indent=2)+"\n")
print("PASS original C1/C5 source-bound nonpromotion and three adversarial CLI denials")
