"""Fail-closed probe for native MPFB/Blender eye shader node warnings.

A clean log is a *syntax/runtime* signal, not evidence of accurate eye optics.
"""
import argparse,json,re,sys,unittest
from pathlib import Path

NODE_PATTERN=re.compile(r"\[ERROR\]\s+services\.nodeservice\b[^:\n]*:")
def audit(log,mode):
    errors=[line.strip() for line in log.splitlines() if NODE_PATTERN.search(line)]
    severe=[line.strip() for line in log.splitlines() if
            "Traceback (most recent call last)" in line or
            ("RuntimeError:" in line and "Caught" not in line)]
    return {"shader_mode":mode,
            "status":"PASS_SHADER_LOG_COMPAT_ONLY" if not errors and not severe else "HOLD_SHADER_LOG_COMPAT",
            "node_error_count":len(errors),"severe_error_count":len(severe),
            "examples":errors[:6]+severe[:2],
            "limitations":["No optical/photoreal eye quality evaluation",
                           "MPFB source must remain pinned",
                           "Only this Blender build and shader configuration measured"]}
class Tests(unittest.TestCase):
    def test_clean(self):
        self.assertEqual(audit("ok", "MAKESKIN")["status"],"PASS_SHADER_LOG_COMPAT_ONLY")
    def test_bad_socket(self):
        s="[ERROR] services.nodeservice ................: Found an input name which didn't exist as socket: Scale"
        self.assertEqual(audit(s,"PROCEDURAL_EYES")["status"],"HOLD_SHADER_LOG_COMPAT")
    def test_blender_traceback(self):
        self.assertEqual(audit("Traceback (most recent call last)", "MAKESKIN")["severe_error_count"],1)
if __name__=="__main__":
    if "--self-test" in sys.argv:
        unittest.main(argv=[sys.argv[0]],verbosity=2)
    else:
        p=argparse.ArgumentParser()
        p.add_argument("--log",type=Path,required=True)
        p.add_argument("--shader-mode",choices=["PROCEDURAL_EYES","MAKESKIN"],required=True)
        p.add_argument("--receipt",type=Path,required=True)
        a=p.parse_args()
        result=audit(a.log.read_text(errors="replace"),a.shader_mode)
        a.receipt.parent.mkdir(parents=True,exist_ok=True)
        a.receipt.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
        print("R014_EYE_SHADER_AUDIT",json.dumps(result,sort_keys=True))
        # Baseline procedural mode intentionally records a HOLD receipt, not a
        # waived pass. MAKESKIN is the explicitly selected corrective candidate.
        raise SystemExit(result["status"]!="PASS_SHADER_LOG_COMPAT_ONLY" and a.shader_mode=="MAKESKIN")
