#!/usr/bin/env python3
"""Blender-specific quality gate; rejects placeholders/frozen imported tracks."""
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

folder=Path(sys.argv[1] if len(sys.argv)>1 else 'out/blender')
receipt=json.loads((folder/'blender_receipt.json').read_text())
assert receipt['schema']=='tropical.blender.receipt.v1'
assert receipt['imported_meshes']>=150, receipt
assert receipt['buffalo_root_count']>=2, receipt
assert receipt['max_buffalo_root_displacement_m']>.08, receipt
assert receipt['frames']==48 and receipt['fps']==12
assert receipt['resolution']==[640,360]
assert receipt['renderer']=='Blender Cycles CPU'
for name in ('tropical_scene.blend','contact_sheet.png','tropical_scene_blender.mp4'):
    f=folder/name
    assert f.is_file() and f.stat().st_size>1024, f
frames=sorted(folder.glob('frame_*.png'))
assert len(frames)==48,len(frames)
assert frames[0].name=='frame_0000.png' and frames[-1].name=='frame_0047.png'
a=hashlib.sha256(frames[0].read_bytes()).hexdigest()
b=hashlib.sha256(frames[24].read_bytes()).hexdigest()
assert a!=b,'Frozen rendered frames'
probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries',
    'stream=nb_frames,width,height,codec_name:format=duration','-of','json',
    str(folder/'tropical_scene_blender.mp4')],text=True))
stream=next(x for x in probe['streams'] if 'width' in x)
assert (stream['width'],stream['height'])==(640,360)
assert stream['codec_name']=='h264'
assert int(stream['nb_frames'])==48
assert math.isclose(float(probe['format']['duration']),4.0,abs_tol=.05)
if len(sys.argv)>2:
    binding=json.loads(Path(sys.argv[2]).read_text())
    assert binding['schema']=='scp.ecology.scene-binding.v1'
    assert receipt['ecology_binding_sha256']==binding['binding_sha256']
    assert receipt['ecology_report_sha256']==binding['source_report_sha256']
    assert receipt['ecology_actor_drivers']==6
    assert receipt['ecology_resource_proxies']==3
    assert receipt['ecology_visualization'].startswith('SYNTHETIC_')
    ratios=[[p['ratio'] for p in frame['patches']] for frame in binding['frames']]
    assert ratios[0]!=ratios[-1], 'unanimated forage state'
    changes=[a['offset'] for a in binding['frames'][-1]['actors']]
    assert any(sum(abs(x) for x in pos)>.1 for pos in changes), 'unanimated animal ecology positions'
    print('PASS: imported actor drivers and visible forage proxies bound to exact verified ecology trace')
print('PASS: imported GLB animated roots, 48 distinct-frame sequence, Blender scene, H.264, and contact sheet')
print(json.dumps(receipt,sort_keys=True))
