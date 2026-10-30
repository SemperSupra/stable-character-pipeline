"""W16-D independent receipt/scope guard, NOT an independent geometry engine."""
import json,sys,math
profile=sys.argv[1]
r=json.load(open(sys.argv[2],encoding="utf-8"))
assert r["Schema"]=="scp.walk_w16d_geometric_receipt.v1"
assert r["Scope"]=="ORIGINAL_SYNTHETIC_GEOMETRIC_FALSIFIERS_NOT_NATIVE_RIG_NOT_FORCE_NOT_PRIVATE"
assert r["Profile"]==profile and profile in ("forward","outward")
assert r["SyntheticClock"]=="12/1"
assert r["FrozenGroundTolerance"]==1e-4 and r["FrozenStanceSlipTolerance"]==1e-3
assert r["SweptActorRadius"]==.25
assert len(r["Checks"])==6
assert r["NegativeControls"]==0 # negative controls are run by Go test, not counted in CLI receipt
print("W16D_SCOPE_LIMITED_RECEIPT_PASS",profile)
