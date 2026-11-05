#!/usr/bin/env python3
"""Source-pinned original synthetic Blender rig render A/B mask witness.

A genuine pixel-test integration, NOT photogrammetry or accepted equine anatomy.
Requires source original Shetland 26-joint .blend produced in a public GHCR job.
"""
import bpy
import hashlib
import json
import math
import sys
from pathlib import Path
from mathutils import Vector

if '--' not in sys.argv or len(sys.argv[sys.argv.index('--')+1:]) != 2:
    raise SystemExit("usage: blender --python pony_blender_qa.py -- source.blend output_dir")
source, out = map(Path, sys.argv[sys.argv.index('--')+1:])
source = source.resolve(strict=True)
out.mkdir(parents=True, exist_ok=True)
out = out.resolve()
bpy.ops.wm.open_mainfile(filepath=str(source))
scene = bpy.context.scene
arm = bpy.data.objects.get('PonyRig26')
assert arm and arm.type == 'ARMATURE', 'missing exact source armature'
assert len(arm.data.bones) == 26, 'wrong source anatomical rig count'
for obj in scene.objects:
    if obj.type == 'MESH' and obj.name.lower() == 'ground':
        obj.hide_render = True

scene.frame_set(12)
scene.render.engine = 'CYCLES'
scene.cycles.samples = 4
scene.render.resolution_x = 256
scene.render.resolution_y = 256
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.render.film_transparent = True
cam = scene.camera
assert cam and cam.type == 'CAMERA'
cam.location = (0.25, -3.2, 1.22)
cam.rotation_euler = (Vector((0.04, 0.0, 0.76)) - cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.type = 'ORTHO'
cam.data.ortho_scale = 2.35
bpy.context.view_layer.update()

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def render(name):
    path = out / (name + '.png')
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    assert path.exists() and path.stat().st_size > 256
    return {'path': path.name, 'sha256': sha(path)}

def save_scene(name):
    path = out / (name + '.blend')
    bpy.ops.wm.save_as_mainfile(filepath=str(path), compress=True)
    return sha(path)

# Camera/view is not part of the source modeling fit; reference is wholly synthetic.
ref = render('reference')
bones = [arm.pose.bones[n] for n in ('front_L_upper', 'neck')]
before = [bone.rotation_euler.copy() for bone in bones]
for bone in bones: bone.rotation_mode = 'XYZ'
bones[0].rotation_euler.x += 0.85
bones[1].rotation_euler.z += 0.48
bpy.context.view_layer.update()
baseline_model_sha = save_scene('baseline_pose')
baseline = render('baseline')

for bone, vec in zip(bones, before):
    bone.rotation_euler = vec
bpy.context.view_layer.update()
candidate_model_sha = save_scene('candidate_pose')
candidate = render('candidate')
assert baseline_model_sha != candidate_model_sha, 'A/B scene state did not change'
assert baseline['sha256'] != candidate['sha256'], 'A/B rendering did not detect pose perturbation'

manifest = {
  'schema': 'scp.render_masks.v1',
  'experiment_id': 'synthetic_pony_native_blender_ab',
  'baseline_sha256': baseline_model_sha,
  'candidate_sha256': candidate_model_sha,
  'subject_class': 'public_original_synthetic_equine',
  'camera_id': 'native_new_side_camera',
  'frame_index': 12,
  'split': 'heldout',
  'mask_channel': 'alpha',
  'threshold': 128,
  'reference': ref,
  'baseline_render': baseline,
  'candidate_render': candidate,
}
(out/'manifest.json').write_text(json.dumps(manifest, sort_keys=True, indent=2)+'\n')
producer = {
  'schema': 'scp.native_mask_provenance.v1',
  'source_blend_sha256': sha(source),
  'source_rig_joint_count': len(arm.data.bones),
  'blender_version': bpy.app.version_string,
  'reference_type': 'synthetic_self_render_not_external_observation',
  'candidate_type': 'same_original_mesh_restored_pose_not_sculpting',
  'baseline_type': 'two_bone_perturbed_pose',
  'camera_type': 'new_orthographic_side_view',
  'frame_index': 12,
  'render_output': {k:v['sha256'] for k,v in [('reference',ref),('baseline',baseline),('candidate',candidate)]},
}
(out/'provenance.json').write_text(json.dumps(producer,sort_keys=True,indent=2)+'\n')
print('NATIVE_SYNTHETIC_MASK_WITNESS',json.dumps(producer,sort_keys=True))
