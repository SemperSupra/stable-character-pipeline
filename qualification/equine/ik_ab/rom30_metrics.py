"""Independent actual three-segment 30-joint equine GLB kinematic verifier.

The legacy two-link observer spans a *bending pair* of lower segments on the
30-joint rig. This inspector measures each actual animated bone separately.
This is an engineering guardrail only, never equine normative anatomy/contact.
"""
import math

FEET=('front_L','front_R','hind_L','hind_R')
LINKS={f:(f+'_upper',f+('_forearm' if f.startswith('front') else '_stifle'),f+'_lower') for f in FEET}

def _v(v):
    if len(v)!=3 or not all(isinstance(x,(int,float)) and math.isfinite(float(x)) for x in v):
        raise ValueError('non-finite 3D joint coordinate')
    return tuple(float(x) for x in v)
def _length(v):return math.sqrt(sum(x*x for x in v))
def _sub(a,b):return tuple(x-y for x,y in zip(a,b))
def _angle(a,b):
    aa=_length(a);bb=_length(b)
    if aa<.04 or bb<.04:raise ValueError('short or degenerate source joint')
    cosine=sum(x*y for x,y in zip(a,b))/(aa*bb)
    return math.degrees(math.acos(min(1.,max(-1.,cosine))))

def evaluate(samples,source_bones):
    if set(samples)!=set(FEET):raise ValueError('four exact 30-joint feet required')
    if len(source_bones)!=30 or not set(n for trio in LINKS.values() for n in trio).issubset(source_bones):
        raise ValueError('requires 30-joint source with all 12 articulated segments')
    failures=[];result={}
    for foot in FEET:
        observed=samples[foot]
        if len(observed)!=48 or [r.get('frame') for r in observed]!=list(range(1,49)):
            raise ValueError('requires 48 contiguous actual native frames')
        first=None;max_drift=0.;max_gap=0.;angles=[[],[]]
        for sample in observed:
            links=sample.get('links')
            if not isinstance(links,list) or len(links)!=3 or [x.get('name') for x in links]!=list(LINKS[foot]):
                raise ValueError('wrong segment order or missing segment')
            vec=[];ends=[];lengths=[]
            for link in links:
                h,t=_v(link['head']),_v(link['tail'])
                v=_sub(t,h)
                length=_length(v)
                if length<.04 or length>.90:raise ValueError('implausible actual rigged bone length')
                vec.append(v);ends.append((h,t));lengths.append(length)
            if first is None:first=tuple(lengths)
            max_drift=max(max_drift,max(abs(x-y) for x,y in zip(lengths,first)))
            max_gap=max(max_gap,max(_length(_sub(ends[i][1],ends[i+1][0])) for i in (0,1)))
            for i in (0,1):angles[i].append(_angle(vec[i],vec[i+1]))
        max_step=max(abs(series[i]-series[i-1]) for series in angles for i in range(1,48))
        flag=[]
        if max_drift>.002:flag.append('actual_segment_length_drift')
        if max_gap>.005:flag.append('disconnected_joint_centers')
        if max_step>25:flag.append('joint_one_frame_snap_provisional')
        for issue in flag:failures.append(f'{foot}:{issue}')
        result[foot]={'source_bones':list(LINKS[foot]),'frame_count':48,
            'baseline_segment_lengths_m':[round(x,7) for x in first],
            'max_actual_segment_length_change_m':round(max_drift,7),
            'max_actual_joint_center_gap_m':round(max_gap,7),
            'max_joint_angle_step_deg':round(max_step,4),
            'elbow_or_stifle_angle_range_deg':[round(min(angles[0]),4),round(max(angles[0]),4)],
            'carpus_or_hock_angle_range_deg':[round(min(angles[1]),4),round(max(angles[1]),4)],
            'violations':flag}
    return {'schema':'equine.rom.actual-three-segment.v1','basis':'NATIVE_IMPORTED_30_JOINT_GLTF_48F',
        'source_class':'PUBLIC_ORIGINAL_SYNTHETIC',
        'measurement':'THREE_ACTUAL_BONE_HEAD_TO_TAIL_SEGMENTS_NOT_TWO_LINK_PROJECTION',
        'scientific_verdict':'ENGINEERING_THREE_LINK_FAIL' if failures else 'THREE_LINK_GUARDS_NO_FAILURE_BIOLOGICAL_UNKNOWN',
        'failure_codes':failures,'joint_reports':result,'observed_frames':48,
        'engineering_thresholds':{'length_drift_m':.002,'joint_center_gap_m':.005,'max_one_frame_angle_step_deg':25},
        'horse_joint_limits':'NOT_VALIDATED','ground_reaction_force':'UNKNOWN',
        'animal_motion_accepted':False,'owner_release_authorized':False}
