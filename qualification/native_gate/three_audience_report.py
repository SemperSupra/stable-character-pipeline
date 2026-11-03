#!/usr/bin/env python3
"""Tiny human/automation/agent tri-view of an already verified actual JSON receipt.
Does not generate facts, does not accept private assets, and never promotes R009.
"""
import argparse,json,pathlib,hashlib,sys
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--receipt",required=True)
    p.add_argument("--human",required=True)
    p.add_argument("--automation",required=True)
    p.add_argument("--agent",required=True)
    a=p.parse_args()
    raw=pathlib.Path(a.receipt).read_bytes()
    j=json.loads(raw)
    if j.get("schema")!="scp.r009.synthetic-integrated-evidence.v1" or \
       j.get("private_R009")!="HELD_NOT_ACCEPTED" or \
       j.get("CPE")!="NOT_PROMOTED" or \
       j.get("status")!="PASS_REPRODUCIBLE_ORIGINAL_SYNTHETIC_EVIDENCE_PROJECTION_ONLY":
        raise SystemExit("THREE_AUDIENCE_PUBLIC_SYNTHETIC_RECEIPT_REJECTED")
    if j.get("science",{}).get("human_identity")!="NOT_ADMITTED" or \
       j.get("source_clock",{}).get("temporal_human_retarget")!="NOT_IMPLEMENTED":
        raise SystemExit("UNSUPPORTED_SCIENCE_OR_TEMPORAL_CLAIM")
    videos=j["media_sha256"]
    if set(videos)!={"front","oblique","debug_front"} or len(set(videos.values()))!=3:
        raise SystemExit("NOT_THREE_DISTINCT_VERIFIED_MEDIA")
    if any(pathlib.Path(x).exists() for x in (a.human,a.automation,a.agent)):
        raise SystemExit("REFUSE_OVERWRITE")
    sourcehash=hashlib.sha256(raw).hexdigest()
    human=[
      "# R009 — Original-synthetic native integration evidence",
      "",
      "**Engineering:** verified real source-authored Blender, two clean 72-frame camera streams and one independent debug stream. Only original synthetic actors were used.",
      "",
      "**Input provenance:** source-bound self-authored BVH→VMD native *spatial calibration only*; 60→30 Hz drops the intermediate source frame. A separate invented 72-frame hip/knee fixture controls the parented, dual-weighted overlay. This is not human rotation retargeting.",
      "",
      "**Visual QA:** all 72 frames / two clean views observed; actual re-encoded hostile video rejected; debug-marker visibility is authored contact labeling, not measured force.",
      "",
      "**Scientific and product limits:** independent human JCS/ROM/contact UNKNOWN; original identity NOT_ADMITTED. Original Naomi/Alison, performer/source rights, protected trusted runner, original park video and blind CPE remain HELD/NOT_RUN. No merge, release or deployment.",
      "",
      "## Exact media digests",
      ""
    ]+[f"- {key}: SHA-256 \`{videos[key]}\`" for key in ("front","oblique","debug_front")]
    human+=["",f"Typed receipt SHA-256: \`{sourcehash}\`",""]
    pathlib.Path(a.human).write_text("\n".join(human),encoding="utf8")
    automation={
       "schema":"scp.r009.automation-evidence-view.v1",
       "source_receipt_sha256":sourcehash,
       "status":j["status"],
       "media_sha256":videos,
       "immutable_donor_heads":j["immutable_donor_head_shas"],
       "source_clock":j["source_clock"],
       "protected_R009":"HELD_NOT_ACCEPTED",
       "CPE":"NOT_PROMOTED"
    }
    agent={
       "schema":"scp.r009.agent-observer-capabilities.v1",
       "source_receipt_sha256":sourcehash,
       "mode":"READ_ONLY",
       "actions":["inspect_receipts","verify_public_synthetic_only","inspect_media_hashes"],
       "can_handle_protected_original":False,
       "can_merge":False,"can_release":False,"can_deploy":False,"can_promote_CPE":False,
       "science":"UNKNOWN",
       "protected_R009":"HELD_NOT_ACCEPTED"
    }
    for out,val in ((a.automation,automation),(a.agent,agent)):
        with pathlib.Path(out).open("x") as f:
            json.dump(val,f,sort_keys=True,indent=2);f.write("\n")
    print(json.dumps({"schema":"scp.r009.three-audience-live-evidence-receipt.v1",
                      "status":"PASS_SOURCE_SAFE_THREE_AUDIENCE_PRESENTATION_ONLY",
                      "source_receipt_sha256":sourcehash,
                      "human_markdown":a.human,"automation_json":a.automation,
                      "agent_json":a.agent,"protected_R009":"HELD_NOT_ACCEPTED"},sort_keys=True))
if __name__=="__main__":main()
