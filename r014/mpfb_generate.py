"""R014 generic two-adult MPFB base bakeoff. Unmodified licensed upstream at runtime."""
import argparse,importlib,json,sys
from pathlib import Path
import bpy,addon_utils

def expose(suffix,name):
    for mod_name in list(sys.modules):
        if mod_name.endswith(suffix):
            mod=importlib.import_module(mod_name)
            if hasattr(mod,name):return getattr(mod,name)
    raise RuntimeError('MPFB API unavailable: '+suffix+':'+name)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--receipt',type=Path,required=True)
    a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
    a.output.mkdir(parents=True,exist_ok=True)
    addon='bl_ext.r014lab.mpfb'
    if addon not in bpy.context.preferences.addons:
        addon_utils.enable(addon,default_set=False)
    assert addon in bpy.context.preferences.addons,'MPFB extension not active'
    HumanService=expose('mpfb.services.humanservice','HumanService')
    TargetService=expose('mpfb.services.targetservice','TargetService')
    Props=expose('mpfb.entities.objectproperties','HumanObjectProperties')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    report={'schema':'r014.mpfb.native.v1','source_revision':'6ff1eb358f6c1959ced77e79e6dd2406d9a71f49',
            'blender':bpy.app.version_string,'characters':[],'status':'BLOCKED'}
    for sex,gender,x in (('female',1.0,-0.8),('male',0.0,0.8)):
        body=HumanService.create_human()
        Props.set_value('gender',gender,entity_reference=body)
        TargetService.reapply_macro_details(body)
        rig=HumanService.add_builtin_rig(body,'default')
        rig.location.x=x
        body.name='R014_'+sex+'_body';rig.name='R014_'+sex+'_rig'
        bpy.context.view_layer.update()
        assert len(body.data.vertices)>1000,'unexpectedly trivial body'
        assert len(rig.data.bones)>20,'unexpectedly trivial rig'
        assert len(body.vertex_groups)>20,'insufficient skin groups'
        report['characters'].append({'sex':sex,'vertices':len(body.data.vertices),
            'faces':len(body.data.polygons),'bones':len(rig.data.bones),
            'skinning_groups':len(body.vertex_groups),
            'shape_keys':len(body.data.shape_keys.key_blocks) if body.data.shape_keys else 0})
    blend=a.output/'R014_MPFB_female_male_native.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    glb=a.output/'R014_MPFB_female_male_native.glb'
    bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',
        export_animations=False,export_morph=True,export_skins=True,export_yup=True)
    assert blend.is_file() and glb.is_file()
    report['status']='PASS_NATIVE_ASSET_CREATED_STRUCTURAL_UNREVIEWED'
    report['blend']=blend.name;report['glb']=glb.name
    report['LIMITS']=['No independent reopen','No closeup, contact, or motion realism',
                      'No hair, realistic skin/eyes or soft tissue dynamics']
    a.receipt.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print('R014_MPFB_REPORT',json.dumps(report,sort_keys=True))
if __name__=='__main__':main()
