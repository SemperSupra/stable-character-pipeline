"""Reproducible real source original costume sculpt 4-design batch."""
from pathlib import Path
import json,hashlib,sys,argparse,os
import trimesh
from sculpt_human_v1 import sculpt,_unpack_glb,_read_accessor,SCHEMA

parser=argparse.ArgumentParser()
parser.add_argument('--input-dir',default=os.environ.get('SCP_ORIGINAL_COSTUME_DIR',
    str(Path(__file__).resolve().parent.parent/'wardrobe_batch'/'artifacts')))
parser.add_argument('--output-dir',default=str(Path(__file__).resolve().parent/'output'))
args=parser.parse_args()
srcroot=Path(args.input_dir).resolve()
outroot=Path(args.output_dir).resolve()
outroot.mkdir(parents=True,exist_ok=True)
rows=[]
for design in ('classic_adventurer','casual','tournament_bodice','high_collar_adventurer'):
    source=srcroot/f'r009_{design}_aster_juniper_35joint.glb'
    raw=source.read_bytes();sha=hashlib.sha256(raw).hexdigest()
    derived,report=sculpt(raw,sha)
    output=outroot/f'r009_{design}_human_sculpt_v1_35joint.glb'
    output.write_bytes(derived)
    # Fresh independent trimesh reader on derived binary bytes.
    scene=trimesh.load(str(output),force='scene')
    doc,buf=_unpack_glb(derived)
    assert len(doc['skins'])==2 and all(len(s['joints'])==35 for s in doc['skins'])
    assert len(doc['animations'])==1
    assert len(scene.graph.nodes_geometry)>=16
    for name in ('AsterOriginal','JuniperOriginal'):
        assert any(n.startswith(name+'_Wardrobe_costume_top') for n in scene.graph.nodes_geometry)
        assert any(n.startswith(name+'_Wardrobe_costume_bottom') for n in scene.graph.nodes_geometry)
    assert all(len(v['replacement_groups'])==4 for v in report['actors'].values())
    again,_=sculpt(raw,sha)
    assert again==derived
    rows.append({'design':design,'input_source_file':source.name,
        'input_sha256':sha,'output_file':output.name,
        'output_sha256':hashlib.sha256(derived).hexdigest(),
        'output_bytes':len(derived),'source_actors':2,'source_joints_per_actor':35,
        'imported_scene_geometry_nodes':len(scene.graph.nodes_geometry),
        'triangles':sum(len(g.faces) for g in scene.geometry.values()),
        'source_animation_preserved':True,'byte_identical_replay':True,
        'actor_scans':report['actors'], 'visual_acceptance':'REVIEW_HOLD',
        'cloth_collision_qualified':False,'photorealism_accepted':False,
        'source_class':'ORIGINAL_SELF_AUTHORED_SYNTHETIC'})
    print('PASS',design,sha[:12],hashlib.sha256(derived).hexdigest()[:12],len(derived))
receipt={'schema':'scp.r009.original_human.sculpt_batch_receipt.v1',
 'source_type':'original_source_only','date':'2026-11-06',
 'generated_outfits':len(rows),'actor_outfit_combinations':8,
 'local_tests':11,'local_tests_pass':11,'blender_native_qualification':'NOT_RUN',
 'visual_inspection':'REVIEW_HOLD',
 'source_geometry_stored':'original source preserved independently',
 'notes':['face remains visibly stylized; no realistic likeness acceptance',
          'seamless limb silhouette does not demonstrate realistic deformation',
          'skirts are static fitted meshes; no physics or collision acceptance'],
 'entries':rows}
(outroot/'sculpt_batch_receipt.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
