#!/usr/bin/env python3
"""Small independent checks on exported artifacts; uses stdlib only."""
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

out = Path(sys.argv[1] if len(sys.argv) > 1 else 'out')
for name in ('tropical_scene.glb','tropical_scene.gltf','tropical_scene.bin','tropical_scene_v0.mp4'):
    path = out/name
    if not path.is_file() or path.stat().st_size <= 128:
        raise SystemExit(f'empty/missing artifact: {path}')
scene = json.loads((out/'tropical_scene.gltf').read_text())
if scene['asset']['version']!='2.0' or len(scene['nodes']) < 100:
    raise SystemExit('malformed/undersized scene')
if len(scene['meshes'])<100 or len(scene['animations'])<1:
    raise SystemExit('scene absent real geometry or motion')
tracks=sum(len(a['channels']) for a in scene['animations'])
if tracks < 40:
    raise SystemExit('insufficient animation tracks')
probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration:stream=nb_frames,width,height,r_frame_rate','-of','json',str(out/'tropical_scene_v0.mp4')],text=True))
video=next((s for s in probe['streams'] if 'width' in s),None)
if video is None or (video['width'],video['height'])!=(640,360):
    raise SystemExit('video resolution mismatch')
if int(video['nb_frames'])!=96 or not math.isclose(float(probe['format']['duration']),8.0,abs_tol=.05):
    raise SystemExit('video duration/framerate mismatch')
# Additional iOS-compatible video and universal GIF fallback.
ios=out/'tropical_scene_iphone.mp4'
gif=out/'tropical_scene_preview.gif'
for artifact in (ios,gif):
    if not artifact.is_file() or artifact.stat().st_size <= 128:
        raise SystemExit(f'missing/empty mobile preview: {artifact}')
mobile=json.loads(subprocess.check_output([
    'ffprobe','-v','error','-show_entries',
    'format=duration:stream=codec_name,profile,pix_fmt,width,height,level',
    '-of','json',str(ios)],text=True))
v=next((s for s in mobile['streams'] if s.get('codec_name')=='h264'),{})
a=next((s for s in mobile['streams'] if s.get('codec_name')=='aac'),{})
if (v.get('width'),v.get('height'),v.get('pix_fmt'))!=(640,360,'yuv420p') or v.get('profile') not in ('Baseline','Constrained Baseline') or not a:
    raise SystemExit('iOS compatibility profile/audio checks failed')
if not math.isclose(float(mobile['format']['duration']),8.0,abs_tol=.08):
    raise SystemExit('mobile video duration mismatch')
for item in (ios,gif):
    subprocess.run(['ffmpeg','-v','error','-i',str(item),'-f','null','-'],check=True,
                   stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=60)
print('PASS: iOS H.264 baseline + AAC and decoded animated GIF')
receipt=json.loads((out/'receipt.json').read_text())
print('receipt keys:',sorted(receipt.keys()))
for name in ('tropical_scene.glb','tropical_scene.gltf','tropical_scene.bin','tropical_scene_v0.mp4'):
    print(name,hashlib.sha256((out/name).read_bytes()).hexdigest())
print('PASS: glTF 2.0, geometry, animation, full frame count, video size and length')
