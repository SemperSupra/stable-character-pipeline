#!/usr/bin/env python3
"""Render the generated glTF scene on CPU/EGL using VTK.

This is a narrow glTF 2.0 preview adapter: consumes exported glTF vertices,
material colors, node parentage, and LINEAR translation/quaternion tracks.
No independently scripted scene geometry or synthetic motion substitutes.
"""
import argparse
import json
from pathlib import Path
import numpy as np
import vtk
from vtk.util.numpy_support import numpy_to_vtk, numpy_to_vtkIdTypeArray

p = argparse.ArgumentParser()
p.add_argument('--scene', default='out/tropical_scene.gltf')
p.add_argument('--out', default='out')
p.add_argument('--frames', type=int, default=96)
p.add_argument('--fps', type=int, default=12)
p.add_argument('--width', type=int, default=960)
p.add_argument('--height', type=int, default=540)
a = p.parse_args()
if not (1 <= a.frames <= 720 and 1 <= a.fps <= 30 and 320 <= a.width <= 1920):
    raise SystemExit('Invalid output bounds')
source = Path(a.scene).resolve()
g = json.loads(source.read_text())
if g['asset']['version'] != '2.0':
    raise SystemExit('Only glTF 2.0 accepted')
binfile = source.parent / g['buffers'][0]['uri']
blob = binfile.read_bytes()
out = Path(a.out)
out.mkdir(exist_ok=True, parents=True)

def accessor(ai):
    acc = g['accessors'][ai]
    bv = g['bufferViews'][acc['bufferView']]
    size = {'SCALAR': 1, 'VEC3': 3, 'VEC4': 4}[acc['type']]
    dtype = {5126: '<f4', 5125: '<u4'}[acc['componentType']]
    start = bv.get('byteOffset', 0) + acc.get('byteOffset', 0)
    return np.frombuffer(blob, dtype=dtype, count=acc['count'] * size, offset=start).reshape(-1, size).copy()

# Exactly the glTF node hierarchy and sampler data written by the Go modeler.
parents = {}
for i,n in enumerate(g['nodes']):
    for child in n.get('children', []):
        parents[child] = i
channels = {}
for anim in g.get('animations', []):
    for c in anim['channels']:
        sampler = anim['samplers'][c['sampler']]
        if sampler.get('interpolation', 'LINEAR') != 'LINEAR':
            raise SystemExit('Non-LINEAR animation is unsupported')
        channels[(c['target']['node'], c['target']['path'])] = (
            accessor(sampler['input']).ravel(), accessor(sampler['output']))

def sample(node_id, path, t, fallback):
    info = channels.get((node_id, path))
    if info is None:
        return np.asarray(fallback, dtype=np.float64)
    times, values = info
    if t <= times[0]: return values[0].astype(np.float64)
    if t >= times[-1]: return values[-1].astype(np.float64)
    idx = int(np.searchsorted(times, t, side='right') - 1)
    w = (t-times[idx]) / (times[idx+1]-times[idx])
    val = (1-w)*values[idx] + w*values[idx+1]
    if path == 'rotation': val = val / max(1e-12, np.linalg.norm(val))
    return val

def matrix(node_id, t, cache):
    if node_id in cache:
        return cache[node_id]
    node=g['nodes'][node_id]
    trans=sample(node_id,'translation',t,node.get('translation',[0,0,0]))
    q=sample(node_id,'rotation',t,node.get('rotation',[0,0,0,1]))
    x,y,z,w=q
    rot=np.array([
        [1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
        [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
        [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])
    m=np.eye(4); m[:3,:3]=rot;m[:3,3]=trans
    if node_id in parents:
        m=matrix(parents[node_id],t,cache)@m
    cache[node_id]=m
    return m

ren=vtk.vtkRenderer()
ren.SetBackground(0.57, 0.77, 0.90)
ren.SetBackground2(0.89, 0.94, 0.96)
ren.GradientBackgroundOn()
ren.SetAmbient(.17,.19,.22)
win=vtk.vtkRenderWindow();win.SetOffScreenRendering(1);win.SetSize(a.width,a.height);win.AddRenderer(ren)
light=vtk.vtkLight();light.SetLightTypeToSceneLight();light.SetPosition(-5,17,6);light.SetFocalPoint(-2,0,0);light.SetIntensity(1.65);ren.AddLight(light)
fill=vtk.vtkLight();fill.SetLightTypeToSceneLight();fill.SetPosition(6,11,-9);fill.SetFocalPoint(-3,0,0);fill.SetIntensity(.54);ren.AddLight(fill)
actors=[]
for node_id,node in enumerate(g['nodes']):
    if 'mesh' not in node: continue
    mesh=g['meshes'][node['mesh']]['primitives'][0]
    pos=accessor(mesh['attributes']['POSITION']).astype(np.float64)
    tris=accessor(mesh['indices']).ravel().astype(np.int64).reshape(-1,3)
    points=vtk.vtkPoints();points.SetData(numpy_to_vtk(pos,deep=True))
    cells=np.column_stack((np.full(len(tris),3,dtype=np.int64),tris)).ravel()
    poly=vtk.vtkPolyData();poly.SetPoints(points)
    ca=vtk.vtkCellArray();ca.SetCells(len(tris),numpy_to_vtkIdTypeArray(cells,deep=True))
    poly.SetPolys(ca)
    mapper=vtk.vtkPolyDataMapper();mapper.SetInputData(poly)
    actor=vtk.vtkActor();actor.SetMapper(mapper)
    rgba=g['materials'][mesh['material']]['pbrMetallicRoughness']['baseColorFactor']
    actor.GetProperty().SetColor(*rgba[:3])
    actor.GetProperty().SetAmbient(.28)
    actor.GetProperty().SetDiffuse(.72)
    actor.GetProperty().SetSpecular(.14)
    actor.GetProperty().SetSpecularPower(10)
    actor.GetProperty().BackfaceCullingOff()
    ren.AddActor(actor)
    actors.append((node_id,actor))
cam=ren.GetActiveCamera()
cam.SetPosition(4,6.5,15)
cam.SetFocalPoint(-3,1.2,0)
cam.SetViewUp(0,1,0)
cam.SetViewAngle(43)
print('loaded geometry:',len(actors),'nodes, animated properties:',len(channels),flush=True)
for frame in range(a.frames):
    t=frame/a.fps
    cache={}
    for node_id,actor in actors:
        m=matrix(node_id,t,cache)
        vtkm=vtk.vtkMatrix4x4()
        for i in range(4):
            for j in range(4):vtkm.SetElement(i,j,float(m[i,j]))
        actor.SetUserMatrix(vtkm)
    ren.ResetCameraClippingRange()
    win.Render()
    image=vtk.vtkWindowToImageFilter();image.SetInput(win);image.SetInputBufferTypeToRGB();image.ReadFrontBufferOff();image.Update()
    writer=vtk.vtkPNGWriter();writer.SetFileName(str(out/f'frame_{frame:04d}.png'));writer.SetInputConnection(image.GetOutputPort());writer.Write()
    if (frame+1)%24==0 or frame==0: print('rendered frame',frame+1,'/',a.frames,flush=True)
