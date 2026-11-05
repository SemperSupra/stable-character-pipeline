"""Source-independent hoof center/minZ temporal contact screen; not veterinary gait diagnosis."""
import math

FEET = ("front_L_hoof", "front_R_hoof", "hind_L_hoof", "hind_R_hoof")

def evaluate(foot_samples, ground_z=-0.015, near_m=0.05, slide_m=0.03, penetration_m=0.015, swing_m=0.045):
    if set(foot_samples) != set(FEET):
        raise ValueError("all four named hoof meshes required")
    summaries = {}
    total_skate = 0
    max_slide = 0.0
    worst_penetration = 0.0
    missing_swing = 0
    for foot in FEET:
        observations = foot_samples[foot]
        if len(observations) < 24:
            raise ValueError("too few frames")
        for idx, point in enumerate(observations):
            if point["frame"] != idx + 1:
                raise ValueError("noncontiguous animation frame")
            if not all(math.isfinite(point[k]) for k in ("x", "y", "min_z")):
                raise ValueError("NaN or infinite geometry")
        slides = []
        nearest = 0
        penetrations = []
        for idx,point in enumerate(observations):
            gap = point["min_z"] - ground_z
            penetrations.append(max(0.0, -gap))
            if idx == 0:
                continue
            prior = observations[idx-1]
            prior_gap = prior["min_z"] - ground_z
            if gap <= near_m and prior_gap <= near_m:
                nearest += 1
                dxy = math.hypot(point["x"]-prior["x"],point["y"]-prior["y"])
                slides.append(dxy)
        max_foot_slide = max(slides,default=0.0)
        max_foot_penetration = max(penetrations,default=0.0)
        foot_skates = sum(d > slide_m for d in slides)
        max_clearance = max(point["min_z"] - ground_z for point in observations)
        elevated_frames = sum(point["min_z"] - ground_z > swing_m for point in observations)
        missing_swing += int(elevated_frames == 0)
        total_skate += foot_skates
        max_slide = max(max_slide,max_foot_slide)
        worst_penetration = max(worst_penetration,max_foot_penetration)
        summaries[foot] = {"near_ground_frame_pairs":nearest,
            "skate_pairs_over_3cm":foot_skates,
            "max_near_ground_displacement_m":round(max_foot_slide,6),
            "max_ground_penetration_m":round(max_foot_penetration,6),
            "max_clearance_m":round(max_clearance,6),
            "frames_above_swing_clearance":elevated_frames}
    verdict = ("FOOT_CONTACT_PROXY_FAIL" if total_skate > 0 or worst_penetration > penetration_m or missing_swing > 0
               else "NO_FAILURE_DETECTED_CONTACT_STILL_UNKNOWN")
    return {"schema":"equine.foot.science.v1","source":"native_evaluated_skin_mesh",
        "assumed_ground_z_m":ground_z,"near_ground_threshold_m":near_m,
        "skate_threshold_m_per_frame":slide_m,"penetration_threshold_m":penetration_m,
        "minimum_swing_clearance_m":swing_m,"hooves_without_minimum_swing_clearance":missing_swing,
        "frames":len(foot_samples[FEET[0]]),"feet":summaries,
        "total_skate_pairs_over_threshold":total_skate,
        "maximum_near_ground_displacement_m":round(max_slide,6),
        "maximum_ground_penetration_m":round(worst_penetration,6),
        "scientific_verdict":verdict,
        "limitation":"majority/centroid ground proxy: no actual force/contact labels, anatomical JCS or external baseline"}
