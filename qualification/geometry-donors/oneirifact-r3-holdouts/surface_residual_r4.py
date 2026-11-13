"""One-sided vertex-to-analytic-zero-set residual check for public synthetic GLBs.

Python standard library only. NOT a bidirectional Hausdorff/small-feature test.
"""
import base64
import hashlib
import json
import math
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parent
FIXTURES = ROOT / "fixtures"
MAX_GRID_PITCH_MULTIPLIER = 1.10  # R4 proposed fixture gate, not a generic precision guarantee

def points(glb):
    if len(glb) < 28: raise ValueError("short GLB")
    magic, version, length = struct.unpack_from("<III", glb, 0)
    if (magic, version, length) != (0x46546c67, 2, len(glb)):
        raise ValueError("GLB header mismatch")
    jsize, jtype = struct.unpack_from("<II", glb, 12)
    if jtype != 0x4e4f534a: raise ValueError("JSON chunk missing")
    obj = json.loads(glb[20:20+jsize])
    ptr = 20 + jsize
    binary_size, binary_type = struct.unpack_from("<II", glb, ptr)
    if binary_type != 0x004e4942: raise ValueError("BIN chunk missing")
    data = glb[ptr+8:ptr+8+binary_size]
    primitive = obj['meshes'][0]['primitives'][0]
    attr = obj['accessors'][primitive['attributes']['POSITION']]
    if attr['type'] != 'VEC3' or attr['componentType'] != 5126:
        raise ValueError("unsupported POSITION accessor")
    view = obj['bufferViews'][attr['bufferView']]
    offset = attr.get('byteOffset', 0) + view.get('byteOffset', 0)
    step = view.get('byteStride', 12)
    if step < 12: raise ValueError("invalid vertex stride")
    if attr['count'] > 50000: raise ValueError("bounded fixture vertex budget exceeded")
    for i in range(attr['count']):
        x,y,z = struct.unpack_from('<fff',data,offset+i*step)
        if not all(math.isfinite(n) for n in (x,y,z)):
            raise ValueError("invalid vertex")
        # glTF Y-up -> canonical graph Z-up. Synthetic fixtures have identity nodes.
        yield (x,z,y)

def sdf_box(xyz,h):
    q = [abs(p)-r for p,r in zip(xyz,h)]
    return math.sqrt(sum(max(0.0, v)**2 for v in q)) + min(max(q), 0.0)

def sdf_sphere(xyz,cx,r):
    return math.sqrt((xyz[0]-cx)**2+xyz[1]**2+xyz[2]**2)-r

def sdf_cylinder(xyz,r,height):
    a = math.hypot(xyz[0],xyz[1])-r
    b = abs(xyz[2])-height/2
    return math.hypot(max(a,0.0),max(b,0.0))+min(max(a,b),0.0)

def reference(name,xyz):
    if name=='rectangular-box': return sdf_box(xyz,(.95,.55,.4))
    if name=='sphere': return sdf_sphere(xyz,0,.73)
    if name=='cylinder': return sdf_cylinder(xyz,.42,1.6)
    if name=='drilled-block': return max(sdf_box(xyz,(1,1,1)),-sdf_cylinder(xyz,.38,3))
    if name=='disconnected-spheres': return min(sdf_sphere(xyz,-.65,.35),sdf_sphere(xyz,.65,.35))
    raise ValueError('unknown synthetic fixture')

def run():
    manifest=json.loads((ROOT/'manifest.json').read_text())
    detail=manifest['fixture_tolerance']['detail']
    if detail < 8: raise ValueError('invalid detail')
    report={}
    for name,expected in sorted(manifest['fixtures'].items()):
        raw=base64.b64decode((FIXTURES/(name+'.glb.b64')).read_text().strip(),validate=True)
        digest=hashlib.sha256(raw).hexdigest()
        assert digest==expected['sha256'],(name,'SHA mismatch')
        bounds=expected['expected_bounds_y_up']
        pitch=max(float(b[1])-float(b[0]) for b in bounds)/(detail-4)
        residuals=sorted(abs(reference(name,p)) for p in points(raw))
        assert residuals,(name,'empty mesh')
        max_residual=residuals[-1]
        p95=residuals[int(.95*(len(residuals)-1))]
        assert max_residual <= pitch*MAX_GRID_PITCH_MULTIPLIER,(name,'residual exceeds pitch budget',max_residual,pitch)
        report[name]={'vertices':len(residuals),'max_abs_vertex_residual_m':round(max_residual,8),'p95_abs_vertex_residual_m':round(p95,8),'pitch_m':round(pitch,8),'max_error_in_grid_cells':round(max_residual/pitch,5)}
    (ROOT/'surface-residual-report.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print('ONEIRIFACT_R4_VERTEX_SURFACE_RESIDUAL_PASS',json.dumps(report,sort_keys=True))
if __name__=='__main__':run()
