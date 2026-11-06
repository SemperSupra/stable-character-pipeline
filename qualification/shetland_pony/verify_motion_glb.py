#!/usr/bin/env python3
"""Independent stdlib GLB motion verifier (not a visual/ethological acceptance)."""
import json
import math
import struct
import sys
from pathlib import Path

MAX_BYTES = 100 * 1024 * 1024
CHANNELS = ('upper_eyelid_L', 'upper_eyelid_R', 'nostril_L', 'nostril_R', 'geometric_coat_mane_tail')
TAIL = ('tail_1', 'tail_2', 'tail_3')


def parse_glb(blob):
    if not (20 <= len(blob) <= MAX_BYTES):
        raise ValueError('bad GLB size')
    magic, version, nbytes = struct.unpack_from('<4sII', blob)
    if magic != b'glTF' or version != 2 or nbytes != len(blob):
        raise ValueError('bad GLB header')
    offset = 12
    chunks = []
    while offset < len(blob):
        if offset + 8 > len(blob):
            raise ValueError('truncated chunk')
        n, kind = struct.unpack_from('<I4s', blob, offset)
        if n % 4 or n > MAX_BYTES or offset + 8 + n > len(blob):
            raise ValueError('invalid chunk length')
        chunks.append((kind, blob[offset + 8: offset + 8 + n]))
        offset += 8 + n
    if len(chunks) != 2 or chunks[0][0] != b'JSON' or chunks[1][0] != b'BIN\x00':
        raise ValueError('expected JSON plus BIN GLB')
    data = json.loads(chunks[0][1].decode('utf-8'))
    if not isinstance(data, dict) or not isinstance(data.get('animations'), list):
        raise ValueError('missing glTF animations')
    return data, chunks[1][1]


def accessor(data, binary, index):
    a = data['accessors'][index]
    v = data['bufferViews'][a['bufferView']]
    if a['componentType'] != 5126 or a['type'] not in ('SCALAR', 'VEC4'):
        raise ValueError('unsupported animation sample encoding')
    comps = 1 if a['type'] == 'SCALAR' else 4
    n = a['count']
    if n < 1 or n > 100000:
        raise ValueError('unbounded accessor samples')
    stride = v.get('byteStride', 4 * comps)
    if stride < 4 * comps or stride % 4:
        raise ValueError('bad sample stride')
    start = v.get('byteOffset', 0) + a.get('byteOffset', 0)
    if start < 0 or start + (n - 1) * stride + 4 * comps > len(binary):
        raise ValueError('sample beyond binary chunk')
    out = [struct.unpack_from('<' + 'f' * comps, binary, start + i * stride) for i in range(n)]
    if any(not math.isfinite(x) for q in out for x in q):
        raise ValueError('nonfinite animation samples')
    return out


def quat_span_degrees(poses):
    if not poses or any(len(p) != 4 or any(not math.isfinite(x) for x in p) for p in poses):
        raise ValueError('missing/invalid rotations')
    origin = poses[0]
    mag = math.sqrt(sum(v*v for v in origin))
    if mag < 0.99 or mag > 1.01:
        raise ValueError('nonunit quaternion')
    max_angle = 0.0
    for q in poses:
        length = math.sqrt(sum(v*v for v in q))
        if length < 0.99 or length > 1.01:
            raise ValueError('nonunit quaternion')
        dot = abs(sum(a*b for a,b in zip(origin, q))) / (mag * length)
        max_angle = max(max_angle, math.degrees(2 * math.acos(min(1., max(-1., dot)))))
    return max_angle


def verify(blob):
    g, binary = parse_glb(blob)
    nodes = g['nodes']; meshes = g['meshes']; skins = g['skins']
    if not skins or max(len(s['joints']) for s in skins) < 30:
        raise ValueError('lost 30-joint rig')
    node_index = {n.get('name'):i for i,n in enumerate(nodes)}
    if not set(CHANNELS + TAIL).issubset(node_index):
        raise ValueError('missing facial, hair or tail nodes')
    channel_samples = {}
    for animation in g['animations']:
        for channel in animation['channels']:
            target = channel['target']; name = nodes[target['node']].get('name')
            path = target['path']
            if (name not in CHANNELS or path != 'weights') and (name not in TAIL or path != 'rotation'):
                continue
            key = (name, path)
            if key in channel_samples:
                raise ValueError('duplicate control across animation tracks')
            sampler = animation['samplers'][channel['sampler']]
            times = [v[0] for v in accessor(g, binary, sampler['input'])]
            if len(times) != 48 or any(b <= a for a,b in zip(times, times[1:])):
                raise ValueError('missing complete increasing 48-frame action')
            out = accessor(g, binary, sampler['output'])
            channel_samples[key] = (times, out)
    result = {'schema':'equine.motion.observer.v1','frames':48,'face':{},'tail':{},'hair':{},
              'verdict':'ENGINEERING_MOTION_OBSERVED_NOT_VISUAL_ACCEPTANCE'}
    for name in CHANNELS:
        key = (name, 'weights')
        if key not in channel_samples:
            raise ValueError('missing '+name+' morph animation')
        _, out = channel_samples[key]
        idx = node_index[name]
        mi = nodes[idx].get('mesh')
        if mi is None:
            raise ValueError('no morph mesh for '+name)
        targets = meshes[mi]['primitives'][0].get('targets', [])
        count = len(targets)
        if count != (9 if name == 'geometric_coat_mane_tail' else 1):
            raise ValueError('incorrect '+name+' target count')
        values = [v[0] for v in out]
        if len(values) != len(channel_samples[key][0]) * count:
            raise ValueError('wrong morph animation sample shape')
        if any(x < -1e-5 or x > 1.00001 for x in values):
            raise ValueError('out of bounds morph weight')
        for j in range(count):
            series = values[j::count]
            if max(series) < (0.5 if name.startswith('nostril') else 0.9) or max(series) - min(series) < .3:
                raise ValueError(name+' morph target '+str(j)+' stuck')
        result['hair' if count == 9 else 'face'][name] = {'targets':count,'samples':len(out), 'max_weight':max(values)}
    for name in TAIL:
        key = (name,'rotation')
        if key not in channel_samples:
            raise ValueError('missing tail animation '+name)
        _,out = channel_samples[key]
        if len(out) != 48:
            raise ValueError('incorrect tail sample count')
        span = quat_span_degrees(out)
        if span < 2.0 or span > 100.:
            raise ValueError('tail animation missing/implausible '+name+': '+str(span))
        result['tail'][name] = {'angular_span_deg':round(span,4)}
    return result


def selftest():
    for bad in (b'', b'garbage', b'glTF' + b'\x00'*100):
        try: parse_glb(bad)
        except (ValueError, struct.error): pass
        else: raise AssertionError('accepted invalid GLB')
    assert quat_span_degrees([(0.,0.,0.,1.), (0.,0.,0.,1.)]) < 1e-5
    assert 4 < quat_span_degrees([(0.,0.,0.,1.),(0.,0.,math.sin(.1),math.cos(.1))]) < 20
    try:quat_span_degrees([(0.,0.,0.,1.),(float('nan'),0.,0.,1.)])
    except ValueError:pass
    else:raise AssertionError('accepted invalid quaternion')


if __name__ == '__main__':
    selftest()
    if len(sys.argv) != 2:
        raise SystemExit('usage: verify_motion_glb.py <real-animated.glb>')
    result = verify(Path(sys.argv[1]).read_bytes())
    print(json.dumps(result,sort_keys=True,indent=2))
