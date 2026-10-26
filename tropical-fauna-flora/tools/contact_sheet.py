#!/usr/bin/env python3
"""Create a contact-sheet PNG from frames using installed VTK's PNG reader/writer.
Does not depend on PIL or install another library.
"""
from pathlib import Path
import vtk
out=Path('out')
ims=[]
for i in (0,24,48,72):
    f=out/f'frame_{i:04d}.png'
    if not f.is_file(): raise SystemExit(f'missing frame {f}')
    reader=vtk.vtkPNGReader();reader.SetFileName(str(f));reader.Update();ims.append(reader.GetOutput())
app=vtk.vtkImageAppend();app.SetAppendAxis(1)
for im in ims: app.AddInputData(im)
app.Update()
writer=vtk.vtkPNGWriter();writer.SetFileName(str(out/'preview_4frame.png'));writer.SetInputConnection(app.GetOutputPort());writer.Write()
