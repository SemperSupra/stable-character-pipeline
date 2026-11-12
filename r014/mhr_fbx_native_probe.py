"""Headless pinned MHR LOD1 FBX native Blender interchange research."""
import argparse,hashlib,json,shutil,sys,zipfile
from pathlib import Path
import bpy

def report(path,data):
    path.write_text(json.dumps(data,indent=2,sort_keys=True)+'\n')
    print('R014_MHR_NATIVE',json.dumps(data,sort_keys=True))
def create(args):
    h=hashlib.sha256()
    with args.archive.open('rb') as src:
        while data:=src.read(1024*1024):h.update(data)
    assert h.hexdigest()==args.sha256,'MHR source archive hash mismatch'
    args.output.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(args.archive) as zip:
        assert zip.testzip() is None,'zip corrupt'
        assert b'Apache License' in zip.read('assets/LICENSE.txt')
        member=zip.getinfo('assets/lod1.fbx')
        assert member.file_size<15*1024*1024,'unexpected size of pinned LOD1 FBX'
        dest=args.output/'mhr_lod1_input.fbx'
        with zip.open(member) as inp,dest.open('wb') as out:shutil.copyfileobj(inp,out)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    try:
        bpy.ops.wm.fbx_import(filepath=str(dest))
        importer='wm.fbx_import'
    except (RuntimeError,AttributeError,TypeError) as error:
        print('FALLBACK FBX importer',repr(error))
        bpy.ops.import_scene.fbx(filepath=str(dest),use_anim=False)
        importer='import_scene.fbx'
    meshes=[o for o in bpy.data.objects if o.type=='MESH']
    rigs=[o for o in bpy.data.objects if o.type=='ARMATURE']
    assert meshes and rigs,'FBX missing imported skinned body/armature'
    body=max(meshes,key=lambda o:len(o.data.vertices))
    rig=max(rigs,key=lambda o:len(o.data.bones))
    shape_count=len(body.data.shape_keys.key_blocks) if body.data.shape_keys else 0
    assert len(body.data.vertices)>5000,'imported mesh too small'
    assert len(rig.data.bones)>20,'imported rig too simple'
    assert shape_count>10,'no MHR identity/face shapekeys imported'
    mods=[m for m in body.modifiers if m.type=='ARMATURE']
    assert mods,'imported body unskinned'
    body.name='R014_MHR_neutral_body'
    rig.name='R014_MHR_neutral_rig'
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output/'R014_MHR_neutral_lod1.blend'))
    out={'status':'PASS_SOURCE_IMPORT_UNREVIEWED','source_archive_sha256':h.hexdigest(),
         'lod':1,'blender':bpy.app.version_string,'importer':importer,
         'vertices':len(body.data.vertices),'faces':len(body.data.polygons),
         'shape_keys':shape_count,'bones':len(rig.data.bones),
         'skinning_groups':len(body.vertex_groups),
         'limits':['No animation/pose retarget qualification',
                   'No CPU TorchScript nonlinear corrective live inference in Blender',
                   'No photoreal materials or male/female shape semantics',
                   'No soft-tissue physics or close-up human likeness verification']}
    report(args.receipt,out)
def verify(args):
    path=(args.output/'R014_MHR_neutral_lod1.blend').resolve()
    assert Path(bpy.data.filepath).resolve()==path,'not fresh reopened'
    body=bpy.data.objects['R014_MHR_neutral_body']
    rig=bpy.data.objects['R014_MHR_neutral_rig']
    assert len(body.data.vertices)>5000
    assert len(body.data.shape_keys.key_blocks)>10
    assert len(rig.data.bones)>20
    assert any(m.type=='ARMATURE' for m in body.modifiers)
    glb=args.output/'R014_MHR_neutral_lod1.glb'
    bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',export_morph=True,
                              export_skins=True,export_yup=True,export_animations=False)
    assert glb.is_file() and glb.stat().st_size>100_000
    report(args.receipt,{'status':'PASS_FRESH_REOPEN_GLTF_EXPORT_STRUCTURAL_ONLY',
          'blender':bpy.app.version_string,'vertices':len(body.data.vertices),
          'shape_keys':len(body.data.shape_keys.key_blocks),
          'bones':len(rig.data.bones),'glb':glb.name,
          'limits':['No nonlinear pose corrections supported in this portable export',
                    'Not accepted as photoreal video character or full MHR behavioral parity']})
def main():
    p=argparse.ArgumentParser()
    p.add_argument('--phase',choices=['create','verify'],required=True)
    p.add_argument('--archive',type=Path)
    p.add_argument('--sha256')
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--receipt',type=Path,required=True)
    args=p.parse_args(sys.argv[sys.argv.index('--')+1:])
    create(args) if args.phase=='create' else verify(args)
if __name__=='__main__':main()
