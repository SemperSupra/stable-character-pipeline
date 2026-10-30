"""Original independent integer Fraction exact clock witness."""
import json,sys
from fractions import Fraction
r=json.load(open(sys.argv[1]))
assert r["Schema"]=="scp.walk_exact_rational_av.v1"
assert r["Rights"]=="ORIGINAL_SELF_AUTHORED_SYNTHETIC"
assert r["LargeAdjacentTickDistinct"] is True
def frac(st):return Fraction(int(st["Numerator"]),int(st["Denominator"]))
assert frac(r["MotionFrame12"])==frac(r["VideoFrame24"])==frac(r["AudioSample48000"])==1
assert Fraction(r["MotionToPCMExactSamples"])==4000
assert Fraction(r["VideoToPCMExactSamples"])==2000
assert frac(r["OneNTSCFrameInPCMSamples"])==Fraction(8008,5)
large=2**60
assert Fraction(large,30)!=Fraction(large+1,30)
assert Fraction(1,12)*48000==Fraction(2,24)*48000
assert Fraction(1,30000)*1001*48000==Fraction(8008,5)
assert "NO_SOURCE_AV_MUX" in r["Scope"]
print("W16E_THIRD_FRACTION_CLOCK_ORIGIN_PASS",r["Profile"])
