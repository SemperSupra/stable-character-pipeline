import json
from pathlib import Path

a=json.loads(Path('out/first-import.json').read_text())
b=json.loads(Path('out/second-import.json').read_text())
for r in (a,b):
    assert r['components']==1, r
    assert r['nonmanifold_edges']==0, r
    assert r['euler_characteristic']==0, r
    assert 6.5 < r['volume_m3'] < 7.5, r
for axis in range(3):
    assert abs(a['bounds_min_m'][axis] - b['bounds_min_m'][axis]) < 0.005
    assert abs(a['bounds_max_m'][axis] - b['bounds_max_m'][axis]) < 0.005
assert abs(a['volume_m3']-b['volume_m3']) < 0.01, (a,b)
print('INDEPENDENT_DCC_ROUNDTRIP_PASS', json.dumps({'input':a,'roundtrip':b},sort_keys=True))
