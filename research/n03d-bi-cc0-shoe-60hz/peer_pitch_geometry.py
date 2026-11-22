"""Read-only outsole heel/ball pitch observables from genuine evaluated CC0 mesh.

This is a geometric diagnostic. Heel/ball IDs are original rest-proxy cohorts;
they are NOT independently validated plantar landmarks or force sensors.
"""
import math


def require(ok, code):
    if not ok:
        raise ValueError(code)


def measure(heel, ball):
    for p in (heel, ball):
        require(isinstance(p, (list, tuple)) and len(p) == 3, "POINT_SHAPE")
        require(all(type(v) in (float, int) and math.isfinite(v) for v in p), "POINT_FINITE")
    dx=float(ball[0])-float(heel[0])
    dy=float(ball[1])-float(heel[1])
    drop=float(heel[2])-float(ball[2])
    horizontal=math.hypot(dx,dy)
    chord=math.hypot(horizontal,drop)
    require(0.025 < horizontal < 1.0 and 0.025 < chord < 1.1, "SHOE_LONGITUDINAL_SPAN_DEGENERATE")
    # The equivalent atan2 and asin use DIFFERENT distance definitions:
    # horizontal length and sloped chord, respectively. Do not use asin with
    # horizontal length; doing so invents a pitch angle.
    horizontal_angle=math.degrees(math.atan2(drop,horizontal))
    sloped_angle=math.degrees(math.asin(drop/chord))
    require(abs(horizontal_angle-sloped_angle)<1e-9, "PITCH_COORDINATE_CONVENTION")
    return {
        "heel_above_ball_z_m":round(drop,8),
        "horizontal_heel_ball_span_m":round(horizontal,8),
        "sloped_heel_ball_chord_m":round(chord,8),
        "observed_world_pitch_deg":round(horizontal_angle,6),
        "atan2_asin_agreement_deg":round(abs(horizontal_angle-sloped_angle),10),
        "anatomical_heel_ball_verified":False,
        "physical_contact_accepted":False,
    }
