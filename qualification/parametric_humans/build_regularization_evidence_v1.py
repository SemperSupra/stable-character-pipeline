#!/usr/bin/env python3
"""Source-safe local research evidence packager; no network/repository writes."""
import hashlib,json,zipfile
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).parent
before=json.loads((ROOT/'retarget_cpu72_motion_qa.json').read_text())
after=json.loads((ROOT/'regularization_motion72_qa.json').read_text())
contact_before=json.loads((ROOT/'retarget_sparse_frame_signed_garment_qa.json').read_text())
contact_after=json.loads((ROOT/'regularization_signed_garment_qa.json').read_text())
summary={'schema':'scp.r009.makehuman35.weight_regularization_comparison.v1',
    'baseline_candidate_sha256':hashlib.sha256((ROOT/'aster_juniper_makehuman35_candidate_v0.glb').read_bytes()).hexdigest(),
    'regularized_candidate_sha256':hashlib.sha256((ROOT/'aster_juniper_makehuman35_regularized_v1.glb').read_bytes()).hexdigest(),
    'actors':{},'full_72_frame_CPU_LBS':True,
    'garment_contact_frames':['rest',0,24,48,71],
    'native_blender':False,'anatomical_accuracy':False,'realistic_motion_accepted':False,
    'garment_collision_accepted':False,'release_approved':False}
fig,ax=plt.subplots(figsize=(9.5,4.9))
for actor in ('AsterOriginal','JuniperOriginal'):
    b=before['actors'][actor]; a=after['actors'][actor]
    old=np.array([x['edge_stretch_ratio_p99'] for x in b['frames']]);new=np.array([x['edge_stretch_ratio_p99'] for x in a['frames']]);
    bd=np.array([x['edge_strain_gt_50pct_fraction'] for x in b['frames']]);ad=np.array([x['edge_strain_gt_50pct_fraction'] for x in a['frames']]);
    assert len(old)==len(new)==len(bd)==len(ad)==72
    assert np.all(new<old) and np.all(ad<bd)
    actor_contact={}
    for slot,rows in contact_after['actors'][actor]['slots'].items():
        oldrows=contact_before['actors'][actor]['slots'][slot]
        actor_contact[slot]={
          'rest_penetration_beyond_5mm_before':oldrows[0]['negative_gt_5mm_fraction'],
          'rest_penetration_beyond_5mm_after':rows[0]['negative_gt_5mm_fraction'],
          'worst_five_witness_penetration_before':max(r['negative_gt_5mm_fraction'] for r in oldrows),
          'worst_five_witness_penetration_after':max(r['negative_gt_5mm_fraction'] for r in rows),
          'fit_accepted':False}
    summary['actors'][actor]={
      'p99_stretch_worst_before':float(old.max()),'p99_stretch_worst_after':float(new.max()),
      'framewise_p99_improved_count':int(np.sum(new<old)),
      'worst_gt_50pct_edge_strain_before':float(bd.max()),
      'worst_gt_50pct_edge_strain_after':float(ad.max()),
      'framewise_severe_edge_strain_improved_count':int(np.sum(ad<bd)),
      'worst_single_edge_stretch_before':b['worst_deformed_edge_ratio'],
      'worst_single_edge_stretch_after':a['worst_deformed_edge_ratio'],
      'max_rest_bind_error_after':a['max_bind_rest_error'],
      'contact':actor_contact}
    ax.plot(np.arange(72),old,linestyle='--',label=f'{actor} baseline')
    ax.plot(np.arange(72),new,label=f'{actor} regularized')
ax.set_xlabel('Sampled animation frame (0–71)')
ax.set_ylabel('99th-percentile triangle-edge stretch ratio')
ax.set_title('Source-pinned retarget: 72-frame CPU linear-skinning quality diagnostic')
ax.legend(fontsize=8,ncol=2)
ax.grid(alpha=.25)
fig.tight_layout()
plot=ROOT/'retarget_weight_regularization_72frame_before_after.png'
fig.savefig(plot,dpi=160);plt.close(fig)
receipt_path=ROOT/'regularization_72frame_comparison_v1.json'
receipt_path.write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
readme=ROOT/'REGULARIZATION_RESEARCH_V1.md'
readme.write_text('''# R009 MakeHuman 35-joint weight regularization v1 — research only

## Source and custody

- Inputs are source-hash-pinned project-original Aster/Juniper and MakeHuman official CC0 body.
- Body already aligned to source-original experimental 35-joint rigs and 72-frame animation in v0.
- New operation: 4 iterations of bounded alpha=0.5 adjacency Laplacian applied to each body’s 35-dimensional joint-weight probability distribution, matching coincident UV-seam vertices without merging geometry. Retain four strongest influences and renormalize.
- Appends new skinned attribute accessors; does not modify or delete the source binary prefix, original geometry, 35-joint armatures, wardrobe, materials or motion.

## Executed / independent controls

- Python source-free and actual-source adversarial tests: 9/9 pass.
- Complete 72-frame CPU linear blend skinning comparison across both actors: all 72/72 frames show lower p99 edge stretch and lower severe (>50%) edge-strain fraction, separately for Aster and Juniper.
- Signed body/garment contact in rest and four selected animation frames: garment penetration persists and remains a first scientific failure.
- UV seam weight continuity, normalized nonnegative 4-influence weights, 35-joint index limits and binary-prefix immutability independently asserted.
- Official Blender-native post-transfer evaluation: NOT_RUN. Physical cloth simulation: NOT_RUN. Face/expression realism: NOT_QUALIFIED.

## Stage-specific holds

- Does not establish correct anatomical skinning; synthetic test movement is not natural human locomotion.
- Aster masculine form still provisional: official MakeHuman male/female morph geometry must be source-pinned, composed and visually audited before any realism claim.
- Juniper torso and outfit bodice clipping substantially fails signed-distance QA. Full 72-frame cloth collision required.
- This ZIP belongs in owner-private Drive; tested source and concise evidence belong in existing public draft PR #336 and DLE #272. No merge/release/branch deletion.

## Reproduce

With NumPy, SciPy, trimesh, project-original companion code (`costume_garment_v1.py` and `sculpt_human_v1.py` in original public PR) and exact source-bound candidate GLB:

```sh
python -m unittest -v test_weight_transfer_regularize_v1
python weight_transfer_regularize_v1.py --candidate-glb aster_juniper_makehuman35_candidate_v0.glb --out-glb /tmp/regularized.glb --receipt /tmp/regularized.json
python observe_makehuman35_motion_v0.py --glb /tmp/regularized.glb --out /tmp/regularized_motion.json
python observe_makehuman35_garment_v0.py --glb /tmp/regularized.glb --expected-sha256 $(sha256sum /tmp/regularized.glb | cut -d' ' -f1) --out /tmp/regularized_garment.json
```

The original broad research producer `retarget_makehuman_v0.py` requires the CC0 body-only OBJ and pinned costume source; it is included in this bundle. No protected real-person model sources are required or included.
''')
files=[
'aster_juniper_makehuman35_candidate_v0.glb',
'aster_juniper_makehuman35_regularized_v1.glb',
'retarget_makehuman_v0.py',
'weight_transfer_regularize_v1.py',
'test_weight_transfer_regularize_v1.py',
'test_retarget_makehuman_v0.py',
'observe_makehuman35_motion_v0.py',
'observe_makehuman35_garment_v0.py',
'test_observe_makehuman35_motion_v0.py',
'retarget_receipt_v0.json',
'regularization_receipt_v1.json',
'retarget_cpu72_motion_qa.json',
'regularization_motion72_qa.json',
'retarget_sparse_frame_signed_garment_qa.json',
'regularization_signed_garment_qa.json',
'regularization_72frame_comparison_v1.json',
'retarget_weight_regularization_72frame_before_after.png',
'retarget_v0_six_view_qa.png',
'REGULARIZATION_RESEARCH_V1.md'
]
archive=ROOT/'R009_Aster_Juniper_MakeHuman35_Weight_Regularization_v1.zip'
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=8) as z:
    for name in sorted(files):
        path=ROOT/name
        assert path.is_file(),name
        z.write(path,'research/'+name)
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    members=z.namelist()
    assert len(members)==len(files) and len(set(members))==len(files)
print(json.dumps({'archive':str(archive),'bytes':archive.stat().st_size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
 'entries':len(files),'actors':{a:{'all_72_p99_improved':v['framewise_p99_improved_count']==72,'p99_before':v['p99_stretch_worst_before'],'p99_after':v['p99_stretch_worst_after']} for a,v in summary['actors'].items()}},indent=2))
