"""Original independent integer Fraction exact clock witness."""
import json,sys
from fractions import Fraction
r=json.load(open(sys.argv[1]))
assert r["schema"]=="scp.walk_exact_rational_av.v1"
assert r["source_rights"]=="ORIGINAL_SELF_AUTHORED_SYNTHETIC"
assert r["large_adjacent_tick_distinct"] is True
def frac(st):return Fraction(int(st["numerator"]),int(st["denominator"]))
assert frac(r["motion_frame_12_seconds"])==frac(r["video_frame_24_seconds"])==frac(r["audio_sample_48000_seconds"])==1
assert Fraction(r["samples_per_motion_frame"])==4000
assert Fraction(r["samples_per_video_frame"])==2000
assert frac(r["samples_per_30000_1001_video_frame"])==Fraction(8008,5)
large=2**60
assert Fraction(large,30)!=Fraction(large+1,30)
assert Fraction(1,12)*48000==Fraction(2,24)*48000
assert Fraction(1,30000)*1001*48000==Fraction(8008,5)
assert "NO_SOURCE_AV_MUX" in r["scope"]
print("W16E_THIRD_FRACTION_CLOCK_ORIGIN_PASS",r["profile"])
