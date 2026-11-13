"""Independent stdlib GLB index/geometry oracle. Only synthetic derived assets."""
from __future__ import annotations
import base64, collections, hashlib, json, math, pathlib, struct, sys
ROOT=pathlib.Path(__file__).parent
D=ROOT/'fixtures'
D.mkdir(exist_ok=True)


def read_glb(path):
    raw=path.read_bytes()
    magic, ver, total=struct.unpack_from('<III',raw,0)
    assert magic==0x46546C67 and ver==2 and total==len(raw),(path,ver,total,len(raw))
    jsize,jtype=struct.unpack_from('<II',raw,12)
    assert jtype==0x4E4F534A
    gltf=json.loads(raw[20:20+jsize])
    pos=20+jsize
    bsize,btype=struct.unpack_from('<II',raw,pos)
    assert btype==0x004E4942
    binary=raw[pos+8:pos+8+bsize]
    primitive=gltf['meshes'][0]['primitives'][0]
    assert primitive['mode']==4 and 'indices' in primitive
    def accessor(idx):
        a=gltf['accessors'][idx]
        view=gltf['bufferViews'][a['bufferView']]
        off=a.get('byteOffset',0)+view.get('byteOffset',0)
        component={5123:('H',2),5125:('I',4),5126:('f',4)}[a['componentType']]
        n={'SCALAR':1,'VEC3':3}[a['type']]
        stride=view.get('byteStride',n*component[1]);assert stride>=n*component[1]
        rows=[]
        for i in range(a['count']):
            row=struct.unpack_from('<'+component[0]*n,binary,off+i*stride)
            rows.append(row[0] if n==1 else row)
        return rows
    vertices=accessor(primitive['attributes']['POSITION'])
    indices=accessor(primitive['indices'])
    assert len(indices)%3==0 and all(0<=i<len(vertices) for i in indices)
    edges=collections.defaultdict(int)
    adj=[set() for _ in vertices]
    volume=0.0
    for i in range(0,len(indices),3):
        t=indices[i:i+3]
        assert len(set(t))==3
        a,b,c=(vertices[k] for k in t)
        ab=[b[k]-a[k] for k in range(3)];ac=[c[k]-a[k] for k in range(3)]
        normal=(ab[1]*ac[2]-ab[2]*ac[1],ab[2]*ac[0]-ab[0]*ac[2],ab[0]*ac[1]-ab[1]*ac[0])
        assert sum(v*v for v in normal)>1e-16
        volume+=(a[0]*normal[0]+a[1]*normal[1]+a[2]*normal[2])/6
        for u,v in ((t[0],t[1]),(t[1],t[2]),(t[2],t[0])):
            adj[u].add(v);adj[v].add(u)
            edges[tuple(sorted((u,v)))]+=1
    assert all(v==2 for v in edges.values()),f'nonmanifold mesh {path}'
    seen=set();components=0
    for i in range(len(vertices)):
        if i in seen:continue
        components+=1;stack=[i];seen.add(i)
        while stack:
            for j in adj[stack.pop()]:
                if j not in seen:seen.add(j);stack.append(j)
    bounds_min=[min(v[k] for v in vertices) for k in range(3)]
    bounds_max=[max(v[k] for v in vertices) for k in range(3)]
    chi=len(vertices)-len(edges)+len(indices)//3
    assert (2*components-chi)%2==0
    genus=(2*components-chi)//2
    return {'vertices':len(vertices),'edges':len(edges),'faces':len(indices)//3,'components':components,'chi':chi,'genus_sum':genus,'volume':abs(volume),'bounds_min':bounds_min,'bounds_max':bounds_max,'sha256':hashlib.sha256(raw).hexdigest()}


def validate():
    manifest=json.loads((ROOT/'manifest.json').read_text())
    out={}
    max_err=manifest['fixture_tolerance']['max_relative_volume_error_pct']
    max_bound=manifest['fixture_tolerance']['max_abs_bound_error_m']
    for name,expected in manifest['fixtures'].items():
        f=D/f'{name}.glb'
        f.write_bytes(base64.b64decode((D/f'{name}.glb.b64').read_text().strip(),validate=True))
        got=read_glb(f)
        assert got['sha256']==expected['sha256'],name
        assert got['components']==expected['components'],(name,got)
        assert got['genus_sum']==expected['genus_sum'],(name,got)
        assert got['volume']>0,(name,got)
        rel_error=abs(got['volume']-expected['analytic_volume_m3'])/expected['analytic_volume_m3']*100
        berror=max(abs(got['bounds_min'][k]-expected['expected_bounds_y_up'][k][0]) for k in range(3))
        berror=max(berror,*[abs(got['bounds_max'][k]-expected['expected_bounds_y_up'][k][1]) for k in range(3)])
        assert rel_error<=max_err,(name,'volume_error_pct',rel_error,max_err)
        assert berror<=max_bound,(name,'bound_error_m',berror,max_bound)
        got['analytic_volume_error_pct']=rel_error
        got['max_bound_error_m']=berror
        out[name]=got
    (ROOT/'glb-measurements.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print('ONEIRIFACT_R3_ANALYTIC_PRECISION_PASS',json.dumps(out,sort_keys=True))
    return out
if __name__=='__main__':validate()
