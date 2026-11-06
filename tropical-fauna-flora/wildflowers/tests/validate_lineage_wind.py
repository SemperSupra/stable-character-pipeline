#!/usr/bin/env python3
"""Read serialized W05 sidecars independently of the Go model implementation."""
import json, math, sys
from pathlib import Path

def verify(root):
    result=[]
    for path in sorted(root.glob('*.lineage.json')):
        plant=path.name.removesuffix('.lineage.json')
        cross=json.loads(path.read_text())
        organs=json.loads((root/(plant+'.organs.json')).read_text())
        wind=json.loads((root/(plant+'.wind.json')).read_text())
        assert cross['schema']=='scp.flora.sourcepath-developmental-crosswalk.v1'
        assert organs['schema']=='scp.flora.organ-geometry-receipt.v2'
        assert wind['schema']=='scp.flora.wind-single-mode-qualification.v1'
        assert cross['status']=='source-path-correspondence-only-not-observed-ontogeny'
        assert cross['visual_validation_status']=='unqualified' and cross['biological_identity_state']=='unknown'
        assert cross['species']==organs['species']==wind['plant_id']==plant
        assert cross['earlier_stage'] < cross['later_stage']
        assert cross['later_organ_sha256']==organs['organ_records_sha256']
        records=organs['organs']; assert len(records)==organs['organ_count']
        keys=[o['semantic_key'] for o in records]
        assert len(keys)==len(set(keys)) and all(o['generator_scope']!='unscoped' for o in records)
        prev={x['semantic_key'] for x in cross['persistent']}
        added={x['semantic_key'] for x in cross['introduced']}
        gone={x['semantic_key'] for x in cross['disappeared']}
        assert not prev&added and not gone and prev and prev|added==set(keys)
        assert wind['model_status']=='synthetic-unmeasured-lumped-mass-drag-not-botanical-physics'
        params=wind['parameters']; samples=wind['samples']
        assert len(samples)==481 and samples[0]['time_s']==0 and abs(samples[-1]['time_s']-params['duration_s'])<1e-8
        assert wind['max_abs_displacement_m']>0
        for t in samples:
            assert all(isinstance(x,(int,float)) and math.isfinite(x) for x in t.values())
            energy=.5*params['effective_mass_kg']*t['tip_velocity_m_per_s']**2+.5*params['lateral_stiffness_n_per_m']*t['tip_displacement_m']**2
            assert abs(energy-t['mechanical_energy_j']) < max(1e-8,energy*1e-6)
            assert abs(t['tip_displacement_m'])<=params['allowed_displacement_m']
        result.append({'species':plant,'persistent':len(prev),'introduced':len(added),'organs':len(records),'wind_max_m':wind['max_abs_displacement_m']})
    assert len(result)==12
    return {'schema':'scp.flora.w05-independent-oracle.v1','status':'PASS','plants':result}

if __name__=='__main__':
    print(json.dumps(verify(Path(sys.argv[1])),indent=2))
