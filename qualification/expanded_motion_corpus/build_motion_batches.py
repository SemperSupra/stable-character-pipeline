#!/usr/bin/env python3
"""Expanded rights-original 3D motion corpus with sex, footwear, and activity variations.

Independent batches generate animated glTF mannequins, side-view H.264 videos,
and frame-level source ground truth for use in visual QA RDT&E.
"""
import argparse, hashlib, json, math, pathlib, struct, subprocess, textwrap
from dataclasses import dataclass
from typing import Dict, List, Tuple

import cv2
import numpy as np

FPS = 20
FRAMES = 40
SIZE = 320
GROUND_Z = 0.0

COLORS = {
    'torso': (54, 136, 150), 'pelvis': (49, 102, 122), 'head': (224, 183, 143),
    'arm': (208, 147, 112), 'left_leg': (54, 116, 218), 'right_leg': (219, 110, 76),
    'left_shoe': (39, 73, 125), 'right_shoe': (144, 65, 48), 'joint': (186, 195, 197),
    'chair': (112, 97, 77), 'water': (92, 161, 201)
}


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha_file(path: pathlib.Path) -> str:
    return sha_bytes(path.read_bytes())


def smooth01(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def lerp(a, b, t):
    return (1 - t) * np.asarray(a, float) + t * np.asarray(b, float)


def triwave(phase: float) -> float:
    phase = phase % 1.0
    return 1 - abs(2 * phase - 1)


@dataclass(frozen=True)
class Body:
    name: str
    shoulder_half: float
    hip_half: float
    thigh: float
    shin: float
    arm_upper: float
    arm_lower: float
    torso_base: float
    torso_top: float
    neck: float
    head_radius: float
    hand_radius: float
    bob: float
    stride_scale: float


@dataclass(frozen=True)
class Footwear:
    name: str
    heel_height: float
    toe_thickness: float
    sole_length: float
    stride_mul: float
    lift_mul: float
    contact_ratio: float
    stance_stability: float


BODIES = {
    'male': Body('male', 0.19, 0.14, 0.54, 0.53, 0.31, 0.28, 1.06, 1.46, 0.12, 0.13, 0.055, 0.012, 1.06),
    'female': Body('female', 0.17, 0.16, 0.52, 0.51, 0.29, 0.27, 1.02, 1.42, 0.12, 0.125, 0.053, 0.010, 0.98),
}

FOOTWEAR = {
    'barefoot': Footwear('barefoot', 0.00, 0.02, 0.19, 1.00, 1.00, 0.62, 1.00),
    'boots': Footwear('boots', 0.02, 0.03, 0.22, 0.93, 0.85, 0.66, 1.05),
    'sandals': Footwear('sandals', 0.01, 0.02, 0.20, 0.96, 0.95, 0.62, 0.92),
    'slippers': Footwear('slippers', 0.005, 0.025, 0.20, 0.88, 0.78, 0.70, 0.75),
    'high_heels': Footwear('high_heels', 0.09, 0.02, 0.20, 0.80, 0.70, 0.70, 0.82),
    'stiletto': Footwear('stiletto', 0.12, 0.015, 0.20, 0.72, 0.62, 0.72, 0.70),
}


CASE_ORDER = [
    # locomotion
    ('male_walk_barefoot', 'locomotion'), ('female_walk_high_heels', 'locomotion'),
    ('female_walk_stiletto', 'locomotion'), ('male_walk_boots', 'locomotion'),
    ('female_skip_sandals', 'locomotion'), ('male_run_boots', 'locomotion'),
    ('female_run_barefoot', 'locomotion'), ('male_jump_slippers', 'locomotion'),
    # exercise + poses
    ('male_stand_barefoot', 'exercise_pose'), ('female_sit_barefoot', 'exercise_pose'),
    ('male_squat_barefoot', 'exercise_pose'), ('female_jumping_jacks_sandals', 'exercise_pose'),
    ('female_cartwheel_barefoot', 'exercise_pose'), ('female_pinup_stiletto', 'exercise_pose'),
    ('female_photoshoot_high_heels', 'exercise_pose'),
    # dance + combat
    ('female_dance_high_heels', 'dance_combat'), ('male_dance_boots', 'dance_combat'),
    ('male_karate_kata_barefoot', 'dance_combat'), ('female_judo_kata_barefoot', 'dance_combat'),
    ('male_kickboxing_barefoot', 'dance_combat'),
    # aquatic
    ('female_swimming_barefoot', 'aquatic'), ('male_diving_barefoot', 'aquatic'),
]

CASE_SPECS: Dict[str, Dict] = {
    'male_walk_barefoot': dict(sex='male', motion='walk', footwear='barefoot', family='locomotion'),
    'female_walk_high_heels': dict(sex='female', motion='walk', footwear='high_heels', family='locomotion'),
    'female_walk_stiletto': dict(sex='female', motion='walk', footwear='stiletto', family='locomotion'),
    'male_walk_boots': dict(sex='male', motion='walk', footwear='boots', family='locomotion'),
    'female_skip_sandals': dict(sex='female', motion='skip', footwear='sandals', family='locomotion'),
    'male_run_boots': dict(sex='male', motion='run', footwear='boots', family='locomotion'),
    'female_run_barefoot': dict(sex='female', motion='run', footwear='barefoot', family='locomotion'),
    'male_jump_slippers': dict(sex='male', motion='jump', footwear='slippers', family='locomotion'),
    'male_stand_barefoot': dict(sex='male', motion='stand', footwear='barefoot', family='exercise_pose'),
    'female_sit_barefoot': dict(sex='female', motion='sit', footwear='barefoot', family='exercise_pose'),
    'male_squat_barefoot': dict(sex='male', motion='squat', footwear='barefoot', family='exercise_pose'),
    'female_jumping_jacks_sandals': dict(sex='female', motion='jumping_jacks', footwear='sandals', family='exercise_pose'),
    'female_cartwheel_barefoot': dict(sex='female', motion='cartwheel', footwear='barefoot', family='exercise_pose'),
    'female_pinup_stiletto': dict(sex='female', motion='pinup_pose', footwear='stiletto', family='exercise_pose'),
    'female_photoshoot_high_heels': dict(sex='female', motion='photoshoot', footwear='high_heels', family='exercise_pose'),
    'female_dance_high_heels': dict(sex='female', motion='dance', footwear='high_heels', family='dance_combat'),
    'male_dance_boots': dict(sex='male', motion='dance', footwear='boots', family='dance_combat'),
    'male_karate_kata_barefoot': dict(sex='male', motion='karate_kata', footwear='barefoot', family='dance_combat'),
    'female_judo_kata_barefoot': dict(sex='female', motion='judo_kata', footwear='barefoot', family='dance_combat'),
    'male_kickboxing_barefoot': dict(sex='male', motion='kickboxing', footwear='barefoot', family='dance_combat'),
    'female_swimming_barefoot': dict(sex='female', motion='swimming', footwear='barefoot', family='aquatic'),
    'male_diving_barefoot': dict(sex='male', motion='diving', footwear='barefoot', family='aquatic'),
}

BATCHES = {
    'locomotion': [c for c, b in CASE_ORDER if b == 'locomotion'],
    'exercise_pose': [c for c, b in CASE_ORDER if b == 'exercise_pose'],
    'dance_combat': [c for c, b in CASE_ORDER if b == 'dance_combat'],
    'aquatic': [c for c, b in CASE_ORDER if b == 'aquatic'],
    'all': [c for c, _ in CASE_ORDER],
}


# ---------- geometry and transforms ----------

def sphere_mesh(lat=6, lon=10):
    verts, faces = [], []
    for y in range(lat + 1):
        phi = math.pi * y / lat
        for x in range(lon + 1):
            theta = 2 * math.pi * x / lon
            verts.append([math.sin(phi) * math.cos(theta), math.sin(phi) * math.sin(theta), math.cos(phi)])
    for y in range(lat):
        for x in range(lon):
            a = y * (lon + 1) + x
            b = a + (lon + 1)
            faces.extend([a, b, a + 1, b, b + 1, a + 1])
    return np.asarray(verts, np.float32), np.asarray(faces, np.uint16).reshape(-1, 3)


def quat_z_to(target):
    z = np.array([0., 0., 1.])
    target = np.asarray(target, float)
    norm = np.linalg.norm(target)
    if norm < 1e-8:
        return np.array([0., 0., 0., 1.])
    target = target / norm
    v = np.cross(z, target)
    w = 1 + np.dot(z, target)
    if w < 1e-8:
        return np.array([1., 0., 0., 0.])
    q = np.array([v[0], v[1], v[2], w])
    return q / np.linalg.norm(q)


def transform(part):
    radius = part['radius']
    if part['type'] == 'ball':
        return part['point'], np.array([0, 0, 0, 1], float), np.array([radius] * 3, float)
    a, b = part['a'], part['b']
    midpoint = (a + b) / 2
    length = float(np.linalg.norm(b - a))
    return midpoint, quat_z_to(b - a), np.array([radius, radius, length / 2 + radius * .45])


def knee_ik(hip, ankle, thigh, shin, bend_sign=1):
    h, a = np.asarray(hip, float), np.asarray(ankle, float)
    d = np.array([a[0] - h[0], a[2] - h[2]], float)
    length = float(np.linalg.norm(d))
    length = min(length, thigh + shin - 1e-6)
    if length <= abs(thigh - shin) + 1e-6:
        length = abs(thigh - shin) + 1e-6
    unit = d / length
    along = (thigh * thigh - shin * shin + length * length) / (2 * length)
    aside = math.sqrt(max(0., thigh * thigh - along * along))
    perp = np.array([-unit[1], unit[0]])
    k = np.array([h[0], h[2]]) + along * unit + bend_sign * aside * perp
    return np.array([k[0], h[1], k[1]])


def camera(view):
    target = np.array([0.50, 0., 1.0])
    if view == 'side':
        eye = np.array([0.60, -4.8, 1.95])
    else:
        eye = np.array([2.8, -4.2, 2.1])
    look = target - eye
    look /= np.linalg.norm(look)
    right = np.cross(look, [0, 0, 1.]); right /= np.linalg.norm(right)
    up = np.cross(right, look); up /= np.linalg.norm(up)
    return eye, look, right, up


def project(points, cam):
    eye, forward, right, up = cam
    relative = np.asarray(points) - eye
    depth = np.dot(relative, forward)
    if np.any(depth <= .05):
        raise ValueError('geometry behind camera')
    return np.column_stack((SIZE / 2 + 520 * np.dot(relative, right) / depth,
                            SIZE / 2 - 520 * np.dot(relative, up) / depth)), depth


# ---------- motion generation ----------

def gait_motion(t, motion, body: Body, shoe: Footwear):
    cfg = {
        'walk': dict(speed=.62, stride=.54, contact=.62, lift=.17, bob=body.bob),
        'run': dict(speed=1.05, stride=.82, contact=.36, lift=.24, bob=body.bob * 1.6),
        'skip': dict(speed=.84, stride=.58, contact=.46, lift=.22, bob=body.bob * 1.8),
    }[motion]
    speed = cfg['speed'] * body.stride_scale * shoe.stride_mul
    stride = cfg['stride'] * body.stride_scale * shoe.stride_mul
    contact_ratio = cfg['contact'] * shoe.contact_ratio
    lift = cfg['lift'] * shoe.lift_mul
    cycle_hz = speed / max(0.4, stride)
    root_x = speed * t
    root_z = body.torso_base + cfg['bob'] * math.cos(2 * math.pi * cycle_hz * t)
    root = np.array([root_x, 0., root_z])

    feet = {}
    contacts = {}
    for side, offset in [('left', 0.0), ('right', 0.5)]:
        phase = (cycle_hz * t + offset) % 1.0
        step_id = math.floor(cycle_hz * t + offset)
        anchor = (step_id - offset) * stride + .10
        contact = phase < contact_ratio
        if contact:
            x = anchor
            z = shoe.heel_height
        else:
            portion = (phase - contact_ratio) / (1 - contact_ratio)
            swing = smooth01(portion)
            x = anchor + stride * swing
            z = shoe.heel_height + lift * math.sin(math.pi * portion)
            if motion == 'skip' and side == 'left':
                z += 0.05 * math.sin(math.pi * portion)
        feet[side] = np.array([x, -body.hip_half if side == 'left' else body.hip_half, z])
        contacts[side] = bool(contact)
    return root, feet, contacts


def jump_motion(t, body: Body, shoe: Footwear):
    phase = (t / (FRAMES / FPS)) % 1.0
    if phase < 0.2:
        crouch = smooth01(phase / 0.2)
        root = np.array([0.15 + 0.1 * phase, 0., body.torso_base - 0.20 * crouch])
        up = 0.0
    elif phase < 0.55:
        u = (phase - 0.2) / 0.35
        arc = 4 * u * (1 - u)
        root = np.array([0.17 + 0.35 * u, 0., body.torso_base + 0.40 * arc])
        up = 0.16 * math.sin(math.pi * u)
    else:
        u = (phase - 0.55) / 0.45
        settle = 1 - smooth01(u)
        root = np.array([0.52 + 0.06 * u, 0., body.torso_base - 0.05 * settle])
        up = 0.0
    feet = {
        'left': np.array([root[0] - 0.05, -body.hip_half, shoe.heel_height + up]),
        'right': np.array([root[0] + 0.05, body.hip_half, shoe.heel_height + up]),
    }
    contacts = {'left': phase < 0.2 or phase > 0.7, 'right': phase < 0.2 or phase > 0.7}
    return root, feet, contacts


def stand_motion(t, body, shoe):
    sway = 0.02 * math.sin(2 * math.pi * t / 2.0)
    root = np.array([0.20 + 0.02 * math.sin(2 * math.pi * t / 2.7), sway * 0.05, body.torso_base + body.bob * 0.5 * math.cos(2 * math.pi * t)])
    feet = {
        'left': np.array([root[0] - 0.05, -body.hip_half, shoe.heel_height]),
        'right': np.array([root[0] + 0.05, body.hip_half, shoe.heel_height])
    }
    contacts = {'left': True, 'right': True}
    return root, feet, contacts


def sit_motion(t, body, shoe):
    phase = min(1.0, t / 1.4)
    root = np.array([0.22, 0., body.torso_base - 0.42 * smooth01(phase)])
    forward = 0.22 * smooth01(phase)
    feet = {
        'left': np.array([0.32, -body.hip_half, shoe.heel_height]),
        'right': np.array([0.46, body.hip_half, shoe.heel_height]),
    }
    contacts = {'left': True, 'right': True}
    return root, feet, contacts, forward


def squat_motion(t, body, shoe):
    cyc = (t / 2.0) % 1.0
    depth = 0.26 * smooth01(triwave(cyc))
    root = np.array([0.26, 0., body.torso_base - depth])
    feet = {
        'left': np.array([0.17, -body.hip_half * 1.05, shoe.heel_height]),
        'right': np.array([0.35, body.hip_half * 1.05, shoe.heel_height]),
    }
    contacts = {'left': True, 'right': True}
    return root, feet, contacts, depth


def jumping_jacks_motion(t, body, shoe):
    cyc = (t / 1.2) % 1.0
    spread = smooth01(triwave(cyc))
    root = np.array([0.26, 0., body.torso_base + 0.02 * math.sin(2 * math.pi * cyc)])
    feet = {
        'left': np.array([0.24 - 0.15 * spread, -body.hip_half - 0.08 * spread, shoe.heel_height]),
        'right': np.array([0.28 + 0.15 * spread, body.hip_half + 0.08 * spread, shoe.heel_height]),
    }
    contacts = {'left': True, 'right': True}
    return root, feet, contacts, spread


def dance_motion(t, body, shoe):
    cyc = (t / 2.0) % 1.0
    sway = math.sin(2 * math.pi * cyc)
    root = np.array([0.22 + 0.10 * math.sin(2 * math.pi * cyc), 0.05 * sway, body.torso_base + 0.03 * math.sin(4 * math.pi * cyc)])
    feet = {
        'left': np.array([root[0] - 0.05 - 0.07 * max(0, sway), -body.hip_half - 0.04 * sway, shoe.heel_height + 0.05 * max(0, -sway)]),
        'right': np.array([root[0] + 0.05 + 0.07 * max(0, -sway), body.hip_half + 0.04 * sway, shoe.heel_height + 0.05 * max(0, sway)]),
    }
    contacts = {'left': sway < 0.7, 'right': sway > -0.7}
    return root, feet, contacts, sway


def pinup_motion(t, body, shoe):
    root = np.array([0.22, 0., body.torso_base + 0.01 * math.sin(2 * math.pi * t / 2.6)])
    feet = {
        'left': np.array([0.20, -body.hip_half - 0.02, shoe.heel_height]),
        'right': np.array([0.31, body.hip_half * 0.35, shoe.heel_height + 0.04]),
    }
    contacts = {'left': True, 'right': True}
    return root, feet, contacts


def photoshoot_motion(t, body, shoe):
    phase = (t / 2.0) % 1.0
    root = np.array([0.24 + 0.02 * math.sin(2 * math.pi * phase), 0., body.torso_base])
    if phase < 0.25:
        feet = {'left': np.array([0.20, -body.hip_half, shoe.heel_height]), 'right': np.array([0.31, body.hip_half*0.6, shoe.heel_height + 0.03])}
        mode = 'hip'
    elif phase < 0.5:
        feet = {'left': np.array([0.19, -body.hip_half*0.7, shoe.heel_height]), 'right': np.array([0.34, body.hip_half*0.9, shoe.heel_height])}
        mode = 'over_shoulder'
    elif phase < 0.75:
        feet = {'left': np.array([0.22, -body.hip_half*1.2, shoe.heel_height]), 'right': np.array([0.30, body.hip_half*0.5, shoe.heel_height])}
        mode = 'contrapposto'
    else:
        feet = {'left': np.array([0.20, -body.hip_half*0.9, shoe.heel_height]), 'right': np.array([0.29, body.hip_half*0.9, shoe.heel_height])}
        mode = 'turn'
    contacts = {'left': True, 'right': True}
    return root, feet, contacts, mode


def karate_motion(t, body, shoe):
    phase = (t / 2.0) % 1.0
    root = np.array([0.22 + 0.16 * phase, 0., body.torso_base])
    if phase < 0.33:
        feet = {'left': np.array([0.18, -body.hip_half-0.06, shoe.heel_height]), 'right': np.array([0.34, body.hip_half+0.04, shoe.heel_height])}
        arm = 'guard'
    elif phase < 0.66:
        feet = {'left': np.array([0.16, -body.hip_half-0.05, shoe.heel_height]), 'right': np.array([0.38, body.hip_half+0.05, shoe.heel_height])}
        arm = 'block'
    else:
        feet = {'left': np.array([0.18, -body.hip_half-0.05, shoe.heel_height]), 'right': np.array([0.40, body.hip_half+0.05, shoe.heel_height])}
        arm = 'strike'
    contacts = {'left': True, 'right': True}
    return root, feet, contacts, arm


def judo_motion(t, body, shoe):
    phase = (t / 2.0) % 1.0
    root = np.array([0.24 + 0.08 * math.sin(2 * math.pi * phase), 0., body.torso_base - 0.05])
    feet = {
        'left': np.array([0.20 - 0.05 * phase, -body.hip_half - 0.05, shoe.heel_height]),
        'right': np.array([0.34 + 0.04 * phase, body.hip_half + 0.05, shoe.heel_height]),
    }
    contacts = {'left': True, 'right': True}
    return root, feet, contacts, 'grip'


def kickboxing_motion(t, body, shoe):
    phase = (t / 2.0) % 1.0
    root = np.array([0.22 + 0.06 * math.sin(2 * math.pi * phase), 0., body.torso_base])
    if phase < 0.4:
        feet = {'left': np.array([0.18, -body.hip_half - 0.04, shoe.heel_height]), 'right': np.array([0.33, body.hip_half+0.03, shoe.heel_height])}
        mode = 'guard'
    elif phase < 0.7:
        u = (phase - 0.4) / 0.3
        feet = {'left': np.array([0.18, -body.hip_half - 0.04, shoe.heel_height]), 'right': np.array([0.33 + 0.22 * u, body.hip_half+0.03, shoe.heel_height + 0.22 * math.sin(math.pi * u)])}
        mode = 'kick'
    else:
        feet = {'left': np.array([0.18, -body.hip_half - 0.04, shoe.heel_height]), 'right': np.array([0.33, body.hip_half+0.03, shoe.heel_height])}
        mode = 'recover'
    contacts = {'left': True, 'right': phase < 0.4 or phase > 0.7}
    return root, feet, contacts, mode


def cartwheel_motion(t, body, shoe):
    phase = (t / (FRAMES / FPS)) % 1.0
    root = np.array([0.12 + 0.65 * phase, 0., body.torso_base + 0.10 * math.sin(math.pi * phase)])
    ang = 2 * math.pi * phase
    feet = {
        'left': np.array([root[0] - 0.10*math.cos(ang), -body.hip_half - 0.20*math.sin(ang), shoe.heel_height + 0.30*max(0, math.sin(ang))]),
        'right': np.array([root[0] + 0.10*math.cos(ang), body.hip_half + 0.20*math.sin(ang), shoe.heel_height + 0.30*max(0, -math.sin(ang))])
    }
    contacts = {'left': phase < 0.2 or phase > 0.8, 'right': phase < 0.2 or phase > 0.8}
    return root, feet, contacts, ang


def swimming_motion(t, body, shoe):
    phase = (t / 1.6) % 1.0
    root = np.array([0.18 + 0.30 * phase, 0., 0.78 + 0.02 * math.sin(2 * math.pi * phase)])
    feet = {
        'left': np.array([root[0] - 0.20, -body.hip_half, 0.68 + 0.08 * math.sin(2 * math.pi * phase)]),
        'right': np.array([root[0] - 0.05, body.hip_half, 0.68 - 0.08 * math.sin(2 * math.pi * phase)])
    }
    contacts = {'left': False, 'right': False}
    return root, feet, contacts, phase


def diving_motion(t, body, shoe):
    phase = (t / (FRAMES / FPS)) % 1.0
    if phase < 0.25:
        root = np.array([0.16, 0., body.torso_base - 0.16 * smooth01(phase/0.25)])
    else:
        u = (phase - 0.25) / 0.75
        root = np.array([0.16 + 0.85 * u, 0., body.torso_base + 0.42 * math.sin(math.pi * u) - 0.42 * u])
    feet = {
        'left': np.array([root[0] - 0.08, -body.hip_half, max(0.02, root[2] - 0.85)]),
        'right': np.array([root[0] + 0.03, body.hip_half, max(0.02, root[2] - 0.85)])
    }
    contacts = {'left': phase < 0.22, 'right': phase < 0.22}
    return root, feet, contacts, phase


def compute_pose(spec: Dict, frame_index: int):
    body = BODIES[spec['sex']]
    shoe = FOOTWEAR[spec['footwear']]
    t = frame_index / FPS
    motion = spec['motion']
    extras = {}
    if motion in ('walk', 'run', 'skip'):
        root, feet, contact = gait_motion(t, motion, body, shoe)
        arm_phase = 2 * math.pi * ((t * (1.2 if motion == 'walk' else 1.9)) % 1.0)
        torso_pitch = 0.04 if motion == 'walk' else 0.10
    elif motion == 'jump':
        root, feet, contact = jump_motion(t, body, shoe)
        arm_phase = math.pi * 0.5 + 2 * math.pi * t / 2.0
        torso_pitch = 0.08
    elif motion == 'stand':
        root, feet, contact = stand_motion(t, body, shoe)
        arm_phase = 0.2 * math.sin(2 * math.pi * t / 3.0)
        torso_pitch = 0.0
    elif motion == 'sit':
        root, feet, contact, forward = sit_motion(t, body, shoe)
        arm_phase = -0.8
        torso_pitch = -0.30 * smooth01(min(1.0, t / 1.4))
        extras['seat_forward'] = forward
    elif motion == 'squat':
        root, feet, contact, depth = squat_motion(t, body, shoe)
        arm_phase = -0.9 * smooth01(depth / 0.26)
        torso_pitch = -0.38 * smooth01(depth / 0.26)
        extras['squat_depth'] = depth
    elif motion == 'jumping_jacks':
        root, feet, contact, spread = jumping_jacks_motion(t, body, shoe)
        arm_phase = 1.3 * spread
        torso_pitch = 0.0
        extras['spread'] = spread
    elif motion == 'cartwheel':
        root, feet, contact, ang = cartwheel_motion(t, body, shoe)
        arm_phase = 2.0
        torso_pitch = 0.0
        extras['cartwheel_angle'] = ang
    elif motion == 'pinup_pose':
        root, feet, contact = pinup_motion(t, body, shoe)
        arm_phase = 0.0
        torso_pitch = 0.08
    elif motion == 'photoshoot':
        root, feet, contact, mode = photoshoot_motion(t, body, shoe)
        extras['pose_mode'] = mode
        arm_phase = 0.0
        torso_pitch = 0.04
    elif motion == 'dance':
        root, feet, contact, sway = dance_motion(t, body, shoe)
        extras['sway'] = sway
        arm_phase = 1.0 * sway
        torso_pitch = 0.05 * sway
    elif motion == 'karate_kata':
        root, feet, contact, mode = karate_motion(t, body, shoe)
        extras['mode'] = mode
        arm_phase = 0.0
        torso_pitch = 0.1
    elif motion == 'judo_kata':
        root, feet, contact, mode = judo_motion(t, body, shoe)
        extras['mode'] = mode
        arm_phase = -0.4
        torso_pitch = -0.08
    elif motion == 'kickboxing':
        root, feet, contact, mode = kickboxing_motion(t, body, shoe)
        extras['mode'] = mode
        arm_phase = 0.0
        torso_pitch = 0.08
    elif motion == 'swimming':
        root, feet, contact, phase = swimming_motion(t, body, shoe)
        extras['phase'] = phase
        arm_phase = 2 * math.pi * phase
        torso_pitch = 1.52
    elif motion == 'diving':
        root, feet, contact, phase = diving_motion(t, body, shoe)
        extras['phase'] = phase
        arm_phase = 1.7
        torso_pitch = -0.55 + 1.0 * max(0, phase - 0.25)
    else:
        raise ValueError(f'unsupported motion {motion}')

    return skeleton_from_state(spec, body, shoe, root, feet, contact, arm_phase, torso_pitch, extras)


def skeleton_from_state(spec, body: Body, shoe: Footwear, root, feet, contact, arm_phase, torso_pitch, extras):
    motion = spec['motion']
    parts, joints = [], {}

    def link(name, a, b, radius, material):
        parts.append({'name': name, 'type': 'segment', 'a': np.asarray(a, float), 'b': np.asarray(b, float), 'radius': radius, 'material': material})
    def ball(name, p, r, material):
        parts.append({'name': name, 'type': 'ball', 'point': np.asarray(p, float), 'radius': r, 'material': material})

    pelvis = root + np.array([0, 0, 0.02])
    chest = root + np.array([0.04 * math.cos(torso_pitch), 0, (body.torso_top - body.torso_base)])
    neck = chest + np.array([0.02 * math.cos(torso_pitch), 0, body.neck])
    head = neck + np.array([0.03 * math.cos(torso_pitch), 0, body.head_radius * 1.2])

    if motion == 'swimming':
        # rotate torso along forward direction by spreading root/chest/head in x.
        chest = root + np.array([0.40, 0, 0.02])
        neck = chest + np.array([0.10, 0, 0.01])
        head = neck + np.array([0.08, 0, 0.00])
        pelvis = root + np.array([0.06, 0, 0.0])
    elif motion == 'diving':
        phase = extras['phase']
        pitch = -1.0 * max(0, (phase - 0.25) / 0.75)
        chest = root + np.array([0.34 * math.cos(pitch), 0, 0.34 * math.sin(pitch) + 0.24])
        neck = chest + np.array([0.10 * math.cos(pitch), 0, 0.10 * math.sin(pitch)])
        head = neck + np.array([0.08 * math.cos(pitch), 0, 0.08 * math.sin(pitch)])
        pelvis = root + np.array([0.05, 0, 0.18])

    link('torso', pelvis, chest, .16 if spec['sex'] == 'male' else .15, 'torso')
    link('pelvis', pelvis + np.array([0, 0, -0.10]), pelvis + np.array([0, 0, 0.04]), .14 if spec['sex'] == 'male' else .145, 'pelvis')
    link('neck', neck - np.array([0, 0, .05]), neck + np.array([0, 0, .02]), .05, 'head')
    ball('head', head, body.head_radius, 'head')

    if motion == 'sit':
        chair_x = 0.38
        link('chair_post', [chair_x, 0., 0.0], [chair_x, 0., 0.48], .05, 'chair')
        link('chair_seat', [chair_x-0.15, 0., 0.48], [chair_x+0.12, 0., 0.48], .06, 'chair')
        link('chair_back', [chair_x+0.10, 0., 0.48], [chair_x+0.10, 0., 0.92], .05, 'chair')

    if motion in ('swimming', 'diving'):
        link('waterline', [-1.0, 0, 0.54], [2.4, 0, 0.54], .04, 'water')

    for side, sign in [('left', -1), ('right', 1)]:
        hip = pelvis + np.array([0.0, sign * body.hip_half, -0.05])
        ankle = feet[side]
        bend_sign = 1
        if motion == 'cartwheel':
            bend_sign = 1 if side == 'left' else -1
        knee = knee_ik(hip, ankle, body.thigh, body.shin, bend_sign=bend_sign)
        toe = ankle + np.array([shoe.sole_length * 0.55, 0., -shoe.toe_thickness])
        heel = ankle + np.array([-shoe.sole_length * 0.35, 0., shoe.heel_height])
        link(f'{side}_thigh', hip, knee, .088 if side == 'left' else .086, f'{side}_leg')
        link(f'{side}_shin', knee, ankle, .073 if side == 'left' else .071, f'{side}_leg')
        ball(f'{side}_knee_joint', knee, .068, 'joint')
        link(f'{side}_shoe', heel, toe, .058, f'{side}_shoe')
        joints[f'{side}_hip'] = hip.tolist()
        joints[f'{side}_knee'] = knee.tolist()
        joints[f'{side}_ankle'] = ankle.tolist()
        joints[f'{side}_toe'] = toe.tolist()

    # arms
    for side, sign in [('left', -1), ('right', 1)]:
        shoulder = chest + np.array([0.0, sign * body.shoulder_half, -0.02])
        if motion in ('walk', 'run', 'skip'):
            phase = arm_phase + (0 if side == 'right' else math.pi)
            elbow = shoulder + np.array([0.10 * math.cos(phase), 0., -body.arm_upper])
            hand = elbow + np.array([0.10 * math.cos(phase), 0., -body.arm_lower])
        elif motion == 'jump':
            elbow = shoulder + np.array([0.02, 0., -body.arm_upper + 0.16 * math.sin(arm_phase)])
            hand = elbow + np.array([0.08, 0., -body.arm_lower + 0.18 * math.sin(arm_phase)])
        elif motion == 'stand':
            elbow = shoulder + np.array([0.06, 0., -body.arm_upper])
            hand = elbow + np.array([0.05, 0., -body.arm_lower])
        elif motion == 'sit':
            elbow = shoulder + np.array([0.09, 0., -0.18])
            hand = elbow + np.array([0.05 + 0.02 * sign, 0., -0.20])
        elif motion == 'squat':
            elbow = shoulder + np.array([0.14, 0., -0.18])
            hand = elbow + np.array([0.11, 0., -0.12])
        elif motion == 'jumping_jacks':
            spread = extras['spread']
            elbow = shoulder + np.array([0.02, sign * 0.10 * spread, -body.arm_upper * (1 - 0.25 * spread)])
            hand = elbow + np.array([0.02, sign * 0.18 * spread, -body.arm_lower * (1 - 0.55 * spread)])
        elif motion == 'cartwheel':
            ang = extras['cartwheel_angle']
            elbow = shoulder + np.array([0.10 * math.cos(ang), sign * 0.18 * math.sin(ang), -0.18])
            hand = elbow + np.array([0.12 * math.cos(ang), sign * 0.24 * math.sin(ang), -0.24])
        elif motion == 'pinup_pose':
            if side == 'left':
                elbow = shoulder + np.array([-0.02, 0., 0.18])
                hand = elbow + np.array([0.00, 0., 0.14])
            else:
                elbow = shoulder + np.array([0.12, 0., -0.08])
                hand = elbow + np.array([0.10, 0., -0.05])
        elif motion == 'photoshoot':
            mode = extras['pose_mode']
            if mode == 'hip':
                if side == 'left':
                    elbow = shoulder + np.array([0.02, 0., -0.06]); hand = elbow + np.array([0.07, 0., -0.02])
                else:
                    elbow = shoulder + np.array([0.10, 0., -0.22]); hand = elbow + np.array([0.09, 0., -0.20])
            elif mode == 'over_shoulder':
                elbow = shoulder + np.array([0.02, 0., 0.08 if side == 'left' else -0.08]); hand = elbow + np.array([-0.03 if side == 'left' else 0.10, 0., 0.11 if side == 'left' else -0.10])
            elif mode == 'contrapposto':
                elbow = shoulder + np.array([0.14 if side == 'right' else 0.02, 0., -0.11]); hand = elbow + np.array([0.10 if side == 'right' else 0.03, 0., -0.10 if side == 'right' else 0.04])
            else:
                elbow = shoulder + np.array([0.06, 0., -0.12]); hand = elbow + np.array([0.07 + 0.02 * sign, 0., -0.15])
        elif motion == 'dance':
            sway = extras['sway']
            elbow = shoulder + np.array([0.10 * (1 if side == 'right' else -0.2), sign * 0.06 * sway, -0.18 + 0.12 * max(0, sway if side == 'right' else -sway)])
            hand = elbow + np.array([0.06, sign * 0.10 * sway, -0.16 + 0.18 * max(0, sway if side == 'right' else -sway)])
        elif motion == 'karate_kata':
            mode = extras['mode']
            if mode == 'guard':
                elbow = shoulder + np.array([0.02, 0., -0.12]); hand = elbow + np.array([0.15, 0., 0.02])
            elif mode == 'block':
                elbow = shoulder + np.array([0.10, 0., 0.02]); hand = elbow + np.array([0.08, 0., 0.20]) if side == 'left' else elbow + np.array([0.14, 0., -0.06])
            else:
                if side == 'right':
                    elbow = shoulder + np.array([0.11, 0., -0.06]); hand = elbow + np.array([0.18, 0., 0.0])
                else:
                    elbow = shoulder + np.array([0.04, 0., -0.12]); hand = elbow + np.array([0.08, 0., -0.02])
        elif motion == 'judo_kata':
            elbow = shoulder + np.array([0.12, 0., -0.08]); hand = elbow + np.array([0.12, 0., 0.02 if side == 'left' else -0.02])
        elif motion == 'kickboxing':
            mode = extras['mode']
            if mode == 'kick' and side == 'right':
                elbow = shoulder + np.array([0.10, 0., -0.08]); hand = elbow + np.array([0.18, 0., -0.02])
            else:
                elbow = shoulder + np.array([0.03, 0., -0.10]); hand = elbow + np.array([0.13, 0., 0.01])
        elif motion == 'swimming':
            ph = extras['phase'] + (0.0 if side == 'right' else 0.5)
            elbow = shoulder + np.array([0.18 * math.cos(2 * math.pi * ph), 0., -0.10 + 0.16 * math.sin(2 * math.pi * ph)])
            hand = elbow + np.array([0.20 * math.cos(2 * math.pi * ph), 0., -0.08 - 0.08 * math.sin(2 * math.pi * ph)])
        elif motion == 'diving':
            phase = extras['phase']
            reach = smooth01(max(0.0, (phase - 0.1) / 0.35))
            elbow = shoulder + np.array([0.12 + 0.12 * reach, 0., 0.02 + 0.04 * reach])
            hand = elbow + np.array([0.14 + 0.10 * reach, 0., 0.03])
        else:
            elbow = shoulder + np.array([0.06, 0., -body.arm_upper])
            hand = elbow + np.array([0.05, 0., -body.arm_lower])
        link(f'{side}_upper_arm', shoulder, elbow, .06, 'arm')
        link(f'{side}_forearm', elbow, hand, .05, 'arm')
        ball(f'{side}_hand', hand, body.hand_radius, 'head')
        joints[f'{side}_shoulder'] = shoulder.tolist(); joints[f'{side}_elbow'] = elbow.tolist(); joints[f'{side}_hand'] = hand.tolist()

    joints['root'] = root.tolist(); joints['head'] = head.tolist(); joints['chest'] = chest.tolist(); joints['pelvis'] = pelvis.tolist()
    return parts, joints, contact, extras


# ---------- glTF and rendering ----------

def build_animation(case_name, root_dir):
    poses = [compute_pose(CASE_SPECS[case_name], i)[0] for i in range(FRAMES)]
    names = [p['name'] for p in poses[0]]
    if any([p['name'] for p in parts] != names for parts in poses):
        raise ValueError('animated node ordering changed')
    verts, faces = sphere_mesh()
    stream = bytearray(); views = []; accessors = []
    def pack(a, component, kind, with_bounds=False):
        arr = np.ascontiguousarray(a)
        while len(stream) % 4: stream.append(0)
        off = len(stream); stream.extend(arr.tobytes())
        vid = len(views); views.append({'buffer': 0, 'byteOffset': off, 'byteLength': arr.nbytes})
        item = {'bufferView': vid, 'componentType': component, 'count': len(arr), 'type': kind}
        if with_bounds:
            flat = arr.reshape(len(arr), -1)
            item['min'] = flat.min(axis=0).tolist(); item['max'] = flat.max(axis=0).tolist()
        accessors.append(item); return len(accessors) - 1
    pos_acc = pack(verts, 5126, 'VEC3', True)
    nor_acc = pack(verts, 5126, 'VEC3')
    idx_acc = pack(faces.ravel(), 5123, 'SCALAR')
    times = pack(np.arange(FRAMES, dtype=np.float32) / FPS, 5126, 'SCALAR', True)
    mats = [{'name': k, 'pbrMetallicRoughness': {'baseColorFactor': [x/255 for x in c] + [1.0], 'metallicFactor': 0.0, 'roughnessFactor': .78}, 'doubleSided': True} for k, c in COLORS.items()]
    order = list(COLORS)
    meshes = [{'name': 'mesh_'+k, 'primitives': [{'attributes': {'POSITION': pos_acc, 'NORMAL': nor_acc}, 'indices': idx_acc, 'material': order.index(k)}]} for k in order]
    nodes = []; channels = []; samplers = []
    for n, name in enumerate(names):
        tr, qr, sc = transform(poses[0][n])
        nodes.append({'name': name, 'mesh': order.index(poses[0][n]['material']), 'translation': tr.tolist(), 'rotation': qr.tolist(), 'scale': sc.tolist()})
        rows = [transform(p[n]) for p in poses]
        for typ, data in [('translation', [r[0] for r in rows]), ('rotation', [r[1] for r in rows]), ('scale', [r[2] for r in rows])]:
            acc = pack(np.asarray(data, dtype=np.float32), 5126, 'VEC4' if typ == 'rotation' else 'VEC3')
            s = len(samplers); samplers.append({'input': times, 'output': acc, 'interpolation': 'LINEAR'})
            channels.append({'sampler': s, 'target': {'node': n, 'path': typ}})
    gltf = {
        'asset': {'version': '2.0', 'generator': 'SemperSupra expanded original motion corpus v1', 'copyright': 'Rights-original procedural research model'},
        'scene': 0, 'scenes': [{'nodes': list(range(len(nodes)))}], 'nodes': nodes,
        'meshes': meshes, 'materials': mats, 'accessors': accessors, 'bufferViews': views, 'buffers': [{'byteLength': len(stream)}],
        'animations': [{'name': case_name, 'channels': channels, 'samplers': samplers}],
        'extras': {'fps': FPS, 'frames': FRAMES, 'case': case_name, 'source': CASE_SPECS[case_name], 'rights': 'rights-original procedural research mannequin; no identity references'}
    }
    payload = json.dumps(gltf, separators=(',', ':'), sort_keys=True).encode('utf-8')
    payload += b' ' * ((-len(payload)) % 4)
    while len(stream) % 4: stream.append(0)
    total_len = 12 + 8 + len(payload) + 8 + len(stream)
    glb = struct.pack('<III', 0x46546c67, 2, total_len) + struct.pack('<II', len(payload), 0x4e4f534a) + payload + struct.pack('<II', len(stream), 0x004e4942) + stream
    out = pathlib.Path(root_dir) / f'{case_name}.glb'
    out.write_bytes(glb)
    return {'file': out.name, 'sha256': sha_bytes(glb), 'bytes': len(glb), 'animated_nodes': len(nodes), 'animation_channels': len(channels)}


def render_frame(case_name, i, view='side'):
    spec = CASE_SPECS[case_name]
    parts, joints, contact, extras = compute_pose(spec, i)
    cam = camera(view)
    frame = np.empty((SIZE, SIZE, 3), dtype=np.uint8)
    family = spec['family']
    if family == 'aquatic':
        for row in range(SIZE):
            if row < SIZE * 0.48:
                frame[row, :] = (238, 241, 244)
            else:
                frame[row, :] = (214 - row//8, 174, 102)
        # water band
        cv2.rectangle(frame, (0, int(SIZE*0.52)), (SIZE, SIZE), (201, 161, 92), -1)
    else:
        for row in range(SIZE):
            g = int(242 - row * 0.07)
            frame[row, :] = (max(175, g-4), max(175, g-1), max(175, g))
    def drawline(a, b, color=(214, 220, 225), thickness=1):
        p, _ = project([a, b], cam)
        cv2.line(frame, tuple(np.round(p[0]).astype(int)), tuple(np.round(p[1]).astype(int)), color, thickness, cv2.LINE_AA)
    # grid / ground
    if family != 'aquatic':
        for x in np.arange(-1.2, 2.5, .25): drawline((x, -.8, 0), (x, .8, 0))
        for y in np.arange(-.8, .9, .2): drawline((-1.2, y, 0), (2.5, y, 0))
    sphere, faces = sphere_mesh()
    all_faces = []
    light = np.array([-.4, -.5, .8]); light /= np.linalg.norm(light)
    for p in parts:
        tr, qt, sc = transform(p)
        qx, qy, qz, qw = qt
        rot = np.array([[1-2*(qy*qy+qz*qz), 2*(qx*qy-qz*qw), 2*(qx*qz+qy*qw)],
                        [2*(qx*qy+qz*qw), 1-2*(qx*qx+qz*qz), 2*(qy*qz-qx*qw)],
                        [2*(qx*qz-qy*qw), 2*(qy*qz+qx*qw), 1-2*(qx*qx+qy*qy)]])
        world = (sphere * sc) @ rot.T + tr
        proj_pts, depth = project(world, cam)
        rgb = COLORS[p['material']]
        for tri in faces:
            x, y, z = world[tri]
            nor = np.cross(y-x, z-x)
            mag = np.linalg.norm(nor)
            if mag < 1e-9:
                continue
            nor /= mag
            brightness = .56 + .44 * max(0., float(np.dot(nor, light)))
            shade = tuple(max(0, min(255, int(ch * brightness))) for ch in rgb[::-1])
            coords = np.round(proj_pts[tri]).astype(np.int32)
            if coords[:,0].max() < 0 or coords[:,0].min() >= SIZE or coords[:,1].max() < 0 or coords[:,1].min() >= SIZE:
                continue
            all_faces.append((float(np.mean(depth[tri])), coords, shade))
    all_faces.sort(key=lambda x: x[0], reverse=True)
    for _, pts, color in all_faces:
        cv2.fillConvexPoly(frame, pts, color, lineType=cv2.LINE_AA)
    for side in ('left', 'right'):
        p = np.asarray(joints[f'{side}_ankle']).copy(); p[2] = max(p[2], 0.005)
        location, _ = project([p], cam)
        xy = tuple(np.round(location[0]).astype(int))
        cv2.circle(frame, xy, 10, (199, 207, 210), 2, cv2.LINE_AA)
        if contact[side]:
            cv2.circle(frame, xy, 3, (65, 125, 75), -1, cv2.LINE_AA)
    label = case_name.replace('_', ' ').upper()
    overlay = f"{spec['sex'].upper()}  |  {spec['motion'].upper()}  |  {spec['footwear'].replace('_',' ').upper()}"
    cv2.rectangle(frame, (0, 0), (SIZE, 36), (37, 46, 58), -1)
    cv2.putText(frame, label[:39], (10, 15), cv2.FONT_HERSHEY_SIMPLEX, .36, (239,243,245), 1, cv2.LINE_AA)
    cv2.putText(frame, overlay[:48], (10, 30), cv2.FONT_HERSHEY_SIMPLEX, .32, (204,218,224), 1, cv2.LINE_AA)
    return frame


def create_video(case_name, out_dir):
    dest = pathlib.Path(out_dir) / f'{case_name}_side.mp4'
    args = ['ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{SIZE}x{SIZE}', '-r', str(FPS), '-i', 'pipe:0', '-an', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '22', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(dest)]
    cmd = subprocess.Popen(args, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    for i in range(FRAMES):
        cmd.stdin.write(render_frame(case_name, i, 'side').tobytes())
    cmd.stdin.close(); err = cmd.stderr.read(); rc = cmd.wait()
    if rc:
        raise RuntimeError(err.decode('utf-8', 'replace')[-600:])
    return {'file': dest.name, 'sha256': sha_file(dest), 'bytes': dest.stat().st_size}


# ---------- corpus assembly ----------

def build_case(case_name, out_dir):
    out_dir = pathlib.Path(out_dir)
    spec = CASE_SPECS[case_name]
    glb = build_animation(case_name, out_dir)
    frames = []
    for i in range(FRAMES):
        _, joints, contact, extras = compute_pose(spec, i)
        frames.append({'frame': i, 'time_s': round(i / FPS, 6), 'joints': joints, 'contact': contact, 'extras': extras})
    labels = {
        'schema': 'scp.expanded-original-3d-motion-labels.v1', 'case': case_name,
        'spec': spec, 'fps': FPS, 'frames': frames, 'source_model': glb['file'],
        'gltf_sha256': glb['sha256'], 'camera_profiles': ['side']
    }
    label_path = out_dir / f'{case_name}_ground_truth.json'
    label_path.write_text(json.dumps(labels, indent=2) + '\n')
    video = create_video(case_name, out_dir)
    return {
        'case': case_name, 'spec': spec, 'model': glb, 'ground_truth': {'file': label_path.name, 'sha256': sha_file(label_path)}, 'videos': [video]
    }


def build_batch(batch_name, out_root):
    cases = BATCHES[batch_name]
    out_root = pathlib.Path(out_root); out_root.mkdir(parents=True, exist_ok=True)
    items = []
    for case_name in cases:
        items.append(build_case(case_name, out_root))
    manifest = {
        'schema': 'scp.expanded-original-3d-motion-corpus.v1', 'batch': batch_name,
        'rights': 'CC0-1.0 for original generated files', 'generator': 'rights-original procedural full-body mesh motion corpus',
        'fps': FPS, 'frames': FRAMES, 'resolution': [SIZE, SIZE], 'cases': items,
        'notes': [
            'Actual animated glTF 2.0 mesh nodes and source 3-D frame poses',
            'Side-view H.264 videos derive from the animated mesh, not 2-D sprite substitution',
            'Sex, motion family, and footwear are explicit experimental factors',
            'Stylized mannequins are not real persons or licensed character assets'
        ]
    }
    (out_root / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    make_contact_sheet(out_root, cases)
    return manifest


def make_contact_sheet(out_root, cases):
    thumbs = []
    for case in cases:
        cap = cv2.VideoCapture(str(pathlib.Path(out_root) / f'{case}_side.mp4'))
        ok, frame = cap.read(); cap.release()
        if not ok:
            continue
        thumb = cv2.resize(frame, (200, 200))
        cv2.putText(thumb, case.replace('_', ' ')[:24], (8, 192), cv2.FONT_HERSHEY_SIMPLEX, .42, (255,255,255), 1, cv2.LINE_AA)
        thumbs.append(thumb)
    if not thumbs:
        return
    cols = 3
    rows = math.ceil(len(thumbs) / cols)
    sheet = np.zeros((rows * 200, cols * 200, 3), np.uint8)
    sheet[:] = (28, 34, 44)
    for idx, img in enumerate(thumbs):
        r, c = divmod(idx, cols)
        sheet[r*200:(r+1)*200, c*200:(c+1)*200] = img
    cv2.imwrite(str(pathlib.Path(out_root) / 'preview_contact_sheet.jpg'), sheet)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--batch', required=True, choices=sorted(BATCHES))
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    manifest = build_batch(args.batch, args.out)
    print(json.dumps({'batch': args.batch, 'case_count': len(manifest['cases']), 'video_count': len(manifest['cases']), 'glb_count': len(manifest['cases']), 'out': str(args.out)}, indent=2))

if __name__ == '__main__':
    main()
