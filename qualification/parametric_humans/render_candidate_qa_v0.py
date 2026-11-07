#!/usr/bin/env python3
"""Source-bound static rest geometry render; no skin, animation or cloth acceptance."""
import sys
import argparse
import vtk
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
from costume_garment_v1 import _unpack_glb
from sculpt_human_v1 import _read_accessor

cli=argparse.ArgumentParser()
cli.add_argument('--source', type=Path, required=True)
cli.add_argument('--out-dir', type=Path, required=True)
args=cli.parse_args()
src=args.source
d,buf=_unpack_glb(src.read_bytes())
meshmap={m['name']:m for m in d['meshes']}
root=args.out_dir;root.mkdir(parents=True,exist_ok=True)
cleared='wardrobe_clearance_candidate_v0' in d.get('extras',{})

def make_actor(meshname, color):
    mesh=meshmap[meshname]
    append=vtk.vtkAppendPolyData()
    for pr in mesh['primitives']:
        x=np.asarray(_read_accessor(d,buf,pr['attributes']['POSITION']),dtype=np.float32).reshape(-1,3)
        idx=np.asarray(_read_accessor(d,buf,pr['indices']),dtype=np.int64).reshape(-1,3)
        pts=vtk.vtkPoints();pts.SetDataTypeToFloat();pts.SetNumberOfPoints(len(x))
        for i,row in enumerate(x): pts.SetPoint(i,float(row[0]),float(row[1]),float(row[2]))
        cells=vtk.vtkCellArray()
        for face in idx:
            tri=vtk.vtkTriangle()
            for j,ii in enumerate(face):tri.GetPointIds().SetId(j,int(ii))
            cells.InsertNextCell(tri)
        pd=vtk.vtkPolyData();pd.SetPoints(pts);pd.SetPolys(cells)
        append.AddInputData(pd)
    append.Update()
    norms=vtk.vtkPolyDataNormals();norms.SetInputConnection(append.GetOutputPort());norms.AutoOrientNormalsOff();norms.SplittingOff();norms.ConsistencyOn();norms.Update()
    mapper=vtk.vtkPolyDataMapper();mapper.SetInputConnection(norms.GetOutputPort())
    act=vtk.vtkActor();act.SetMapper(mapper)
    prop=act.GetProperty();prop.SetColor(*color);prop.SetInterpolationToPhong();prop.SetAmbient(.3);prop.SetDiffuse(.65);prop.SetSpecular(.08)
    return act

names=[('AsterOriginal',(0.74,0.64,0.57),(.38,.56,.76)),('JuniperOriginal',(.81,.67,.55),(.68,.36,.56))]
for actor,skin,cloth in names:
 for view in ('front','side','face'):
    renderer=vtk.vtkRenderer();renderer.SetBackground(.09,.105,.13)
    renderer.AddActor(make_actor(actor+'_MakeHuman_CC0_BodyOnly_Retarget_V0',skin))
    if view!='face':
        layers=[('top',cloth),('bottom',cloth),('trim',(.65,.62,.25))]
        for name,c in layers:
            renderer.AddActor(make_actor(actor+'_'+('costume_'+name+'_signed_rest_clearance_candidate' if cleared and name in ('top','bottom','trim') else name+'_ProceduralMesh'),c))
        renderer.AddActor(make_actor(actor+'_footwear_SeparateSkinnedMesh',(.23,.23,.25)))
    w=vtk.vtkRenderWindow();w.SetOffScreenRendering(True);w.AddRenderer(renderer)
    w.SetSize(650,750)
    cam=renderer.GetActiveCamera();cam.ParallelProjectionOn()
    if view=='front': cam.SetPosition(0,.90,-4);cam.SetFocalPoint(0,.90,0);cam.SetViewUp(0,1,0);cam.SetParallelScale(1.0)
    elif view=='side':cam.SetPosition(4,.90,0);cam.SetFocalPoint(0,.90,0);cam.SetViewUp(0,1,0);cam.SetParallelScale(1.0)
    else:cam.SetPosition(0,1.58,-4);cam.SetFocalPoint(0,1.58,0);cam.SetViewUp(0,1,0);cam.SetParallelScale(.28)
    renderer.ResetCameraClippingRange();w.Render()
    filt=vtk.vtkWindowToImageFilter();filt.SetInput(w);filt.Update()
    writer=vtk.vtkPNGWriter();writer.SetInputConnection(filt.GetOutputPort())
    out=root/(actor+'_'+view+'_retarget_v0.png');writer.SetFileName(str(out));writer.Write()
    print(out)

images=[]
for actor,_skin,_cloth in names:
    row=[]
    for view in ('front','side','face'):
        img=Image.open(root/(actor+'_'+view+'_retarget_v0.png')).convert('RGB')
        row.append(img)
    images.append(row)
canvas=Image.new('RGB',(1950,1560),(22,26,33));draw=ImageDraw.Draw(canvas)
for i,row in enumerate(images):
    for j,im in enumerate(row):
        canvas.paste(im,(j*650,i*780+30));draw.text((j*650+15,i*780+8),names[i][0]+' '+('front','side','face')[j],fill=(240,240,235))
out=root/'six_view_qa.png';canvas.save(out)
print('MONTAGE',out)
