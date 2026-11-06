#!/usr/bin/env python3
"""Produce deterministic variant inputs; never touches baseline presets."""
import json,pathlib,subprocess
base=pathlib.Path(__file__).resolve().parents[1]
variants=base/'outputs-v02'/'variants';variants.mkdir(exist_ok=True,parents=True)
for id in ['zea_mays','helianthus_annuus','vitis_vinifera']:
 s=json.loads((base/'presets'/(id+'.json')).read_text())
 s['growth_stage']=.4
 s['seed']=s['seed']
 p=variants/(id+'_juvenile.json');p.write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n')
 subprocess.run([str(base/'flora-gen-v02'),'-preset',str(p),'-out',str(variants/(id+'_juvenile.glb'))],check=True)
old=json.loads((base/'presets'/'quercus_robur.json').read_text());old['seed']+=1
p=variants/'quercus_robur_seed33.json';p.write_text(json.dumps(old,ensure_ascii=False,indent=2)+'\n')
subprocess.run([str(base/'flora-gen-v02'),'-preset',str(p),'-out',str(variants/'quercus_robur_seed33.glb')],check=True)
