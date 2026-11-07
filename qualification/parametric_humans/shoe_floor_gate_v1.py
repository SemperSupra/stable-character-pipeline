#!/usr/bin/env python3
"""Fail-closed source-free floor-distance validation (not biomechanics acceptance)."""
from __future__ import annotations
import math
from shoe_floor_contact_v1_schema import SCHEMA, INPUT_SHA256
ACTORS=('AsterOriginal','JuniperOriginal')
class FloorGateError(ValueError): pass

def require(ok,reason):
    if not ok:raise FloorGateError(reason)

def gate(report):
    require(type(report) is dict and report.get('schema')==SCHEMA,'SCHEMA')
    require(report.get('source_sha256')==INPUT_SHA256,'SOURCE_PIN')
    require(report.get('coordinate_up')=='Y' and type(report.get('floor_y_m')) in (int,float)
            and report['floor_y_m']==0.0,'FLOOR_CONTRACT')
    require(report.get('frames_evaluated')==72,'FRAME_COUNT')
    for flag in ('root_shift_applied','native_blender_evaluated','physical_contact_accepted','realistic_gait_accepted','release_approved'):
        require(report.get(flag) is False,'FORGED_APPROVAL:'+flag)
    require(type(report.get('actors')) is dict and set(report['actors'])==set(ACTORS),'ACTOR_SET')
    require(type(report.get('summary')) is dict and set(report['summary'])==set(ACTORS),'SUMMARY_SET')
    rejects=[]
    hovering=[]
    for actor in ACTORS:
        samples=report['actors'][actor]
        require(type(samples) is list and len(samples)==144,'SAMPLE_COUNT')
        seen=set(); min_y={}; bad_vertex_frames=set()
        for row in samples:
            require(type(row) is dict and set(row)=={'frame','side','min_y_m','vertices','vertices_below_minus_1mm','vertices_below_minus_5mm','vertices_within_10mm_floor'},'SAMPLE_FIELDS')
            f=row['frame'];s=row['side'];require(type(f) is int and 0<=f<72 and s in ('L','R'),'FRAME_SIDE')
            key=(f,s);require(key not in seen,'DUPLICATE_SAMPLE');seen.add(key)
            val=row['min_y_m'];require(type(val) in (float,int) and math.isfinite(val) and -1.0<val<1.0,'MIN_Y_INVALID')
            n=row['vertices'];require(type(n) is int and n>=300,'VERTEX_COUNT')
            c1=row['vertices_below_minus_1mm'];c5=row['vertices_below_minus_5mm'];c10=row['vertices_within_10mm_floor']
            require(all(type(c) is int and 0<=c<=n for c in (c1,c5,c10)) and c5<=c1,'COUNT_BOUNDS')
            require((val<-.001)==(c1>0) and (val<-.005)==(c5>0),'COUNT_MIN_INCONSISTENT')
            require(val<=.010 or c10==0,'NEAR_FLOOR_COUNT_INCONSISTENT')
            min_y[key]=val
            if c5:bad_vertex_frames.add(f)
        require(len(seen)==144,'MISSING_SAMPLES')
        stance=[min(min_y[(f,'L')],min_y[(f,'R')]) for f in range(72)]
        s=report['summary'][actor];require(type(s) is dict,'SUMMARY_STRUCTURE')
        def eq(k,v):
            w=s.get(k)
            require(type(w) in (int,float) and math.isfinite(w) and abs(w-v)<1e-7,'SUMMARY_INCONSISTENT:'+k)
        eq('worst_min_y_m',min(stance))
        eq('stance_min_mean_y_m',sum(stance)/72)
        eq('frames_with_sole_below_minus_1mm',sum(v<-.001 for v in stance))
        eq('frames_with_sole_below_minus_5mm',sum(v<-.005 for v in stance))
        eq('foot_frame_count_below_minus_1mm',sum(min_y[k]<-.001 for k in seen))
        eq('frames_both_feet_above_plus_10mm',sum(all(min_y[(f,x)]>.010 for x in ('L','R')) for f in range(72)))
        eq('diagnostic_only_root_clearance_shift_m_min',min(-v for v in stance))
        eq('diagnostic_only_root_clearance_shift_m_max',max(-v for v in stance))
        eq('max_root_shift_delta_m_per_frame',max(abs(stance[f]-stance[f-1]) for f in range(1,72)))
        if bad_vertex_frames:rejects.append({'actor':actor,'affected_frames':len(bad_vertex_frames),'min_y_m':min(stance)})
        elevated=[f for f,v in enumerate(stance) if v>.010]
        if elevated:hovering.append({'actor':actor,'affected_frames':len(elevated),'min_stance_y_m':min(stance)})
    return {'schema':'scp.r009.shoe_floor_gate.v1','source_sha256':INPUT_SHA256,
        'verdict':'RED_FOOT_FLOOR_PENETRATION' if rejects else 'RED_FOOT_FLOATING' if hovering else 'PASS_FLOOR_DISTANCE_PROXY_ONLY',
        'rejects':rejects,'hovering':hovering,'native_blender_evaluated':False,'realistic_gait_accepted':False,'release_approved':False}
