"""Independent stdlib W13-A numerical oracle and W16-B scope witness."""
import hashlib, json, math, sys
from pathlib import Path
from independent_ik import process
source=Path(sys.argv[1]).read_bytes()
r=json.loads(Path(sys.argv[2]).read_text())
oracle=process(source)
assert r["Schema"]=="scp.walk_w16b_ik_join_receipt.v1"
assert r["SourceRights"]=="ORIGINAL_PROGRAMMATIC_PROCEDURAL_ONLY"
assert r["SourceSHA256"]==hashlib.sha256(source).hexdigest()==oracle["source_sha256"]
assert r["ReachableCompared"]==4 and r["UnreachablePolicyDifferences"]==1
assert r["ClockScope"]=="SYNTHETIC_12_OVER_1_NOT_SOURCE_MEASURED"
assert "NOT_SKIN_NOT_PRIVATE" in r["Scope"]
assert len(r["Cases"])==5
for i,(a,b) in enumerate(zip(oracle["cases"],r["Cases"])):
    assert a["id"]==b["ID"] and a["status"]==b["AStatus"]
    assert b["Frame"]==b["TimeNumerator"]==12*i and b["TimeDenominator"]==12
    if a["reached"]:
        assert b["BStatus"]=="REACHED"
        assert math.isfinite(b["KneeError"]) and b["KneeError"]<=1e-8
        assert math.isfinite(b["WorldFKError"]) and b["WorldFKError"]<=1e-8
        assert math.isfinite(b["ChildLocalMisuseError"])
    else:
        assert b["BStatus"]=="REJECT_UNREACHABLE"
print("W16B_THIRD_NUMERIC_ORACLE_PASS",r["SourceSHA256"])
