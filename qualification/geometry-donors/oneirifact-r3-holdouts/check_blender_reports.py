import json,pathlib,math
R=pathlib.Path(__file__).parent
manifest=json.loads((R/'manifest.json').read_text())['fixtures']
source=json.loads((R/'glb-measurements.json').read_text())
report={}
for name,expected in manifest.items():
 a=json.loads((R/'fixtures'/f'{name}.import.json').read_text())
 b=json.loads((R/'fixtures'/f'{name}.reimport.json').read_text())
 for item in [a,b]:
  assert item['components']==expected['components'],(name,item)
  assert item['genus_sum']==expected['genus_sum'],(name,item)
  assert item['nonmanifold_edges']==0
  assert item['faces']==source[name]['faces']
  assert abs(item['volume']-source[name]['volume'])<1e-4,(name,item,source[name])
 assert abs(a['volume']-b['volume'])<1e-4
 for k in ['bounds_min','bounds_max']:
  assert all(abs(x-y)<1e-4 for x,y in zip(a[k],b[k]))
 report[name]={'import':a,'reimport':b}
(R/'blender-reports.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
print('ONEIRIFACT_MULTI_DCC_ROUNDTRIP_PASS',len(report))
