"""Direct public donor bakeoff: pinned upstream Manifold vs synthetic Oneirifact GLB; no private source."""
import json, math, pathlib, time, importlib.metadata
import manifold3d as m
ROOT=pathlib.Path(__file__).parent
manifest=json.loads((ROOT/'manifest.json').read_text())['fixtures']
source=json.loads((ROOT/'glb-measurements.json').read_text())

def construct(name):
 if name=='drilled-box':
  return m.Manifold.cube((2.0,2.0,2.0),center=True)-m.Manifold.cylinder(3.0,0.4,0.4,circular_segments=128,center=True)
 if name=='two-spheres-union':
  ball=m.Manifold.sphere(0.7,circular_segments=128)
  return ball.translate((-0.35,0,0))+ball.translate((0.35,0,0))
 if name=='two-spheres-disconnected':
  ball=m.Manifold.sphere(0.5,circular_segments=128)
  return ball.translate((-1,0,0))+ball.translate((1,0,0))
 if name=='sphere-box-intersection':
  return m.Manifold.sphere(0.8,circular_segments=128)^m.Manifold.cube((1.2,1.2,1.2),center=True)
 raise KeyError(name)

def main():
 out={};version=importlib.metadata.version('manifold3d')
 assert version=='3.5.4'
 for name,expected in manifest.items():
  start=time.perf_counter();solid=construct(name);elapsed=time.perf_counter()-start
  volume=solid.volume();verts=solid.num_vert();triangles=solid.num_tri();genus=solid.genus()
  assert not solid.is_empty(),name
  error=abs(volume-source[name]['volume'])/volume*100
  assert error<12,(name,error,volume,source[name])
  if name=='drilled-box':
   analytic=expected['analytic_volume_m3'];assert abs(volume-analytic)/analytic<0.002,(volume,analytic)
  out[name]={'donor':'manifold3d','version':version,'volume_m3':volume,'oneirifact_volume_m3':source[name]['volume'],'relative_volume_error_pct':error,'vertices':verts,'triangles':triangles,'genus':genus,'seconds':elapsed}
 (ROOT/'manifold-report.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
 print('ONEIRIFACT_MANIFOLD_R2_COMPARISON_PASS',json.dumps(out,sort_keys=True))
if __name__=='__main__':main()
