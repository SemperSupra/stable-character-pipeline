"""Optional VTK CPU renderer for exported animated glTF; never render concept images as evidence."""
import argparse
from pathlib import Path
import vtk

parser=argparse.ArgumentParser()
parser.add_argument("--scene",default="out/mechanical_scene.gltf")
parser.add_argument("--out",default="out")
parser.add_argument("--frames",type=int,default=49)
parser.add_argument("--focus",choices=("all","titan"),default="all")
parser.add_argument("--width",type=int,default=960)
parser.add_argument("--height",type=int,default=540)
args=parser.parse_args()
if not (2 <= args.frames <= 121 and 320 <= args.width <= 1920 and 240 <= args.height <= 1080):
    parser.error("frame or resolution bound violated")
directory=Path(args.out); directory.mkdir(parents=True,exist_ok=True)
window=vtk.vtkRenderWindow()
window.SetSize(args.width,args.height)
window.SetOffScreenRendering(1)
importer=vtk.vtkGLTFImporter()
importer.SetFileName(str(Path(args.scene).resolve()))
importer.SetRenderWindow(window)
importer.Update()
if importer.GetNumberOfAnimations()<1:
    raise RuntimeError("export contains no glTF animations")
for i in range(importer.GetNumberOfAnimations()):
    importer.EnableAnimation(i)
renderer=importer.GetRenderer()
renderer.SetBackground(.92,.95,.98)
# The Go glTF file maps authored Z-up to glTF Y-up.
camera=renderer.GetActiveCamera()
if args.focus=="titan":
    camera.SetPosition(22.5,13,17)
    camera.SetFocalPoint(12.5,5.1,0)
else:
    camera.SetPosition(25,19,32)
    camera.SetFocalPoint(5.8,4.1,0)
camera.SetViewUp(0,1,0)
camera.SetViewAngle(42)
camera.ParallelProjectionOn()
camera.SetParallelScale(8.5 if args.focus=="titan" else 17)
renderer.ResetCameraClippingRange()
light=vtk.vtkLight()
light.SetLightTypeToSceneLight()
light.SetPosition(7,20,15)
light.SetFocalPoint(0,0,0)
light.SetIntensity(1.0)
renderer.AddLight(light)
grab=vtk.vtkWindowToImageFilter()
grab.SetInput(window)
grab.ReadFrontBufferOff()
writer=vtk.vtkPNGWriter()
writer.SetInputConnection(grab.GetOutputPort())
for i in range(args.frames):
    t=8.0*i/(args.frames-1)
    importer.UpdateAtTimeValue(t)
    window.Render()
    grab.Modified()
    grab.Update()
    writer.SetFileName(str(directory / ("frame_%04d.png" % i)))
    writer.Write()
window.Finalize()
print("Rendered",args.frames,"frames from exported glTF and animation.")
