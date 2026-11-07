#!/usr/bin/env python3
"""Fail-closed 73-pose contact + 72f bounded-strain *research* gate.

Unlike a rigid skirt's exact no-strain comparator, this separately requires
strictly no contact regressions AND a fixed conservative distortion envelope.
A relative result never constitutes cloth, wearability or product approval.
"""
from __future__ import annotations
import json,math
from triangle_vertex_contact_gate_v1 import compare,GateError
STRAIN_SCHEMA='scp.r009.skirt_cpu72_edge_strain.v1'
ACTORS=('AsterOriginal','JuniperOriginal')
RESEARCH_LIMITS={'p99_edge_ratio':1.15,'max_edge_ratio':1.15,
                 'min_edge_ratio':.80,'min_triangle_area_ratio':.80,
                 'fraction_strained_gt_50pct':0.,'fraction_area_lt_quarter':0.}
SCHEMA='scp.r009.skirt_contact_strain_candidate_gate.v1'
class BoundedGateError(ValueError):pass

def finite(x):return type(x) in (int,float) and math.isfinite(x)

def _strain_valid(before,after):
    for r in (before,after):
        if not isinstance(r,dict) or r.get('schema')!=STRAIN_SCHEMA or r.get('frames')!=72 or set(r.get('actors',{}))!=set(ACTORS):
            raise BoundedGateError('STRAIN_SCHEMA_OR_ACTORS')
        for key in ('native_blender_evaluated','physical_cloth_qualified','garment_fit_accepted','release_approved'):
            if r.get(key) is not False:raise BoundedGateError('FALSE_SCIENCE_APPROVAL')
        for actor in ACTORS:
            rows=r['actors'][actor]
            if type(rows) is not list or len(rows)!=72 or [x.get('frame') for x in rows]!=list(range(72)):
                raise BoundedGateError('MISSING_72_STRAIN_FRAMES')
            for row in rows:
                for key in RESEARCH_LIMITS:
                    if not finite(row.get(key)):raise BoundedGateError('NONFINITE_STRAIN')
                if row['min_edge_ratio']<=0 or row['max_edge_ratio']<row['min_edge_ratio'] or row['min_triangle_area_ratio']<=0:
                    raise BoundedGateError('IMPOSSIBLE_STRAIN')
    if before['source_sha256']==after['source_sha256']:
        raise BoundedGateError('IDENTICAL_SOURCE')
    return True

def evaluate(baseline_bvh,baseline_signed,candidate_bvh,candidate_signed,baseline_strain,candidate_strain):
    _strain_valid(baseline_strain,candidate_strain)
    result=compare(baseline_bvh,baseline_signed,candidate_bvh,candidate_signed)
    if baseline_bvh['source_sha256']!=baseline_strain['source_sha256'] or candidate_bvh['source_sha256']!=candidate_strain['source_sha256']:
        raise BoundedGateError('CROSS_METRIC_SOURCE_MISMATCH')
    if result.get('all_72_frames_evaluated') is not True:
        raise BoundedGateError('INCOMPLETE_CONTACT_FRAMES')
    # Actor isolation is strong and explicit: no geometry/contact change for
    # Aster or Juniper's non-skirt slots, and 72 strain frames identical there.
    for actor in ACTORS:
        for slot,row in result['per_actor_slot'][actor].items():
            if actor=='AsterOriginal' or slot!='costume_bottom':
                if row['triangles_before']!=row['triangles_after'] or abs(row['vertex_mean_before']-row['vertex_mean_after'])>1e-9:
                    raise BoundedGateError('OTHER_ACTOR_OR_SLOT_CHANGED')
        if actor=='AsterOriginal':
            for first,second in zip(baseline_strain['actors'][actor],candidate_strain['actors'][actor]):
                for key in RESEARCH_LIMITS:
                    if abs(first[key]-second[key])>1e-6:raise BoundedGateError('ASTER_STRAIN_DRIFT')
    breaks=[]
    for actor,rows in candidate_strain['actors'].items():
        for row in rows:
            for key,limit in RESEARCH_LIMITS.items():
                v=row[key]
                valid=(v>=limit-1e-8) if key in ('min_edge_ratio','min_triangle_area_ratio') else (v<=limit+1e-8)
                if not valid:breaks.append({'actor':actor,'frame':row['frame'],'metric':key,'observed':v,'research_limit':limit})
    verdict=('RED_CONTACT_REGRESSION' if result['regressions'] else
             'RED_DEFORMATION_ENVELOPE' if breaks else
             'PASS_BOUNDED_RELATIVE_RESEARCH_ONLY' if result['improvements'] else
             'HOLD_NO_GAIN')
    return {'schema':SCHEMA,'baseline_sha256':baseline_bvh['source_sha256'],'candidate_sha256':candidate_bvh['source_sha256'],
      'verdict':verdict,'pose_count':73,'actor_count':2,
      'contact_improvement_count':len(result['improvements']),'contact_regression_count':len(result['regressions']),
      'deformation_violations_count':len(breaks),'deformation_examples':breaks[:20],
      'limits':RESEARCH_LIMITS,'juniper_skirt':result['per_actor_slot']['JuniperOriginal']['costume_bottom'],
      'other_actor_and_slots_unchanged':True,
      'native_blender_evaluated':False,'anatomical_realism_accepted':False,
      'physical_cloth_qualified':False,'garment_fit_accepted':False,'release_approved':False}

if __name__=='__main__':
    import argparse,pathlib
    ap=argparse.ArgumentParser()
    for key in ('baseline_bvh','baseline_signed','candidate_bvh','candidate_signed','baseline_strain','candidate_strain','out'):
        ap.add_argument('--'+key.replace('_','-'),required=True,type=pathlib.Path)
    a=ap.parse_args()
    paths=[getattr(a,k) for k in ('baseline_bvh','baseline_signed','candidate_bvh','candidate_signed','baseline_strain','candidate_strain','out')]
    if len(set(p.resolve() for p in paths))!=len(paths) or a.out.exists():raise BoundedGateError('NO_OVERWRITE')
    r=evaluate(*(json.loads(p.read_text()) for p in paths[:-1]))
    a.out.write_text(json.dumps(r,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'verdict':r['verdict'],'improvements':r['contact_improvement_count'],'regressions':r['contact_regression_count'],'strain_violations':r['deformation_violations_count']},sort_keys=True))
    if r['verdict']!='PASS_BOUNDED_RELATIVE_RESEARCH_ONLY':raise SystemExit(12)
