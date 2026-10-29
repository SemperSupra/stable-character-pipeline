"""Original-only independent Python standard-library GLB LBS animation reader.
No Blender/bpy, other renderer, or glTF loader. Unsupported formats fail closed.
"""
import argparse,bisect,hashlib,json,math,struct
from pathlib import Path
COMP={5121:"B",5123:"H",5125:"I",5126:"f"}
SIZE={"SCALAR":1,"VEC2":2,"VEC3":3,"VEC4":4,"MAT4":16}
def read_glb(path):
 raw=Path(path).read_bytes()
 if len(raw)<20 or raw[:4]!=b"glTF" or struct.unpack_from("<II",raw,4)!=(2,len(raw)):
  raise ValueError("GLB_MAGIC_VERSION_OR_SIZE")
 o=12;doc=None;binary=None
 while o<len(raw):
  if o+8>len(raw):raise ValueError("GLB_TRUNCATED_CHUNK")
  n,typ=struct.unpack_from("<I4s",raw,o);o+=8
  if o+n>len(raw):raise ValueError("GLB_CHUNK_BOUNDS")
  chunk=raw[o:o+n];o+=n
  if typ==b"JSON":doc=json.loads(chunk)
  elif typ==b"BIN\x00":binary=chunk
 if doc is None or binary is None:raise ValueError("GLB_JSON_OR_BIN_MISSING")
 if not doc.get("scenes"):raise ValueError("NO_SCENE")
 return doc,binary,hashlib.sha256(raw).hexdigest()
def accessor(d,b,index):
 a=d["accessors"][index];v=d["bufferViews"][a["bufferView"]]
 if a.get("sparse") or a.get("normalized"):raise ValueError("UNSUPPORTED_SPARSE_OR_NORMALIZED_ACCESSOR")
 if a["componentType"] not in COMP or a["type"] not in SIZE:raise ValueError("UNSUPPORTED_ACCESSOR_TYPE")
 count=SIZE[a["type"]];fmt="<"+COMP[a["componentType"]]*count
 n=struct.calcsize(fmt);stride=v.get("byteStride",n)
 off=v.get("byteOffset",0)+a.get("byteOffset",0)
 if stride<n or off+stride*(a["count"]-1)+n>len(b):raise ValueError("ACCESSOR_BOUNDS")
 return [struct.unpack_from(fmt,b,off+i*stride) for i in range(a["count"])]
def mul(a,b):
 return tuple(sum(a[4*k+r]*b[4*c+k] for k in range(4)) for c in range(4) for r in range(4))
def mv(m,p):
 return tuple(sum(m[4*j+i]*p[j] for j in range(4)) for i in range(4))
def trs(t,q,s):
 x,y,z,w=q;n=math.sqrt(sum(v*v for v in q))
 if not math.isfinite(n) or n<1e-9:raise ValueError("INVALID_ROTATION_QUATERNION")
 x/=n;y/=n;z/=n;w/=n
 xx,yy,zz=x*x,y*y,z*z;xy,xz,yz=x*y,x*z,y*z;wx,wy,wz=w*x,w*y,w*z
 return ((1-2*(yy+zz))*s[0],(2*(xy+wz))*s[0],(2*(xz-wy))*s[0],0,
         (2*(xy-wz))*s[1],(1-2*(xx+zz))*s[1],(2*(yz+wx))*s[1],0,
         (2*(xz+wy))*s[2],(2*(yz-wx))*s[2],(1-2*(xx+yy))*s[2],0,
         t[0],t[1],t[2],1)
def interp(samples,vals,t,kind,rotation=False):
 if len(samples)!=len(vals) or not samples:raise ValueError("BAD_ANIMATION_SAMPLER")
 if any(samples[i]>=samples[i+1] for i in range(len(samples)-1)):raise ValueError("NONMONOTONIC_SAMPLER")
 if t<=samples[0]:return vals[0]
 if t>=samples[-1]:return vals[-1]
 j=bisect.bisect_right(samples,t)-1;a,b=samples[j],samples[j+1]
 if abs(t-a)<5e-5:return vals[j]
 if abs(t-b)<5e-5:return vals[j+1]
 if kind=="STEP":return vals[j]
 if kind!="LINEAR":raise ValueError("CUBICSPLINE_NOT_QUALIFIED")
 u=(t-a)/(b-a)
 if rotation:
  q0,q1=vals[j],vals[j+1];dot=sum(x*y for x,y in zip(q0,q1))
  if dot<0:q1=tuple(-x for x in q1);dot=-dot
  dot=min(1,max(-1,dot))
  if dot>.9995:res=[(1-u)*x+u*y for x,y in zip(q0,q1)]
  else:
   angle=math.acos(dot);scale=math.sin(angle)
   res=[(math.sin((1-u)*angle)*x+math.sin(u*angle)*y)/scale for x,y in zip(q0,q1)]
  n=math.sqrt(sum(x*x for x in res));return tuple(x/n for x in res)
 return tuple((1-u)*x+u*y for x,y in zip(vals[j],vals[j+1]))
def evaluate(d,b,second):
 nodes=d["nodes"];parents={}
 for i,node in enumerate(nodes):
  for ch in node.get("children",[]):
   if ch in parents:raise ValueError("NODE_MULTIPLE_PARENTS")
   parents[ch]=i
 pose={}
 for animation in d.get("animations",[]):
  for channel in animation["channels"]:
   node=channel["target"]["node"];prop=channel["target"]["path"]
   if prop not in ("translation","rotation","scale"):raise ValueError("UNSUPPORTED_ANIM_CHANNEL")
   s=animation["samplers"][channel["sampler"]]
   times=[v[0] for v in accessor(d,b,s["input"])]
   vals=accessor(d,b,s["output"])
   if (node,prop) in pose:raise ValueError("OVERLAPPING_ANIMATION_CHANNELS")
   pose[(node,prop)]=interp(times,vals,second,s.get("interpolation","LINEAR"),prop=="rotation")
 cache={};visiting=set()
 def world(node):
  if node in cache:return cache[node]
  if node in visiting:raise ValueError("CYCLIC_JOINT_HIERARCHY")
  visiting.add(node);v=nodes[node]
  if "matrix" in v:
   if any(key[0]==node for key in pose):raise ValueError("ANIMATING_MAT4_NODE")
   local=tuple(v["matrix"])
  else:
   local=trs(pose.get((node,"translation"),v.get("translation",(0,0,0))),
             pose.get((node,"rotation"),v.get("rotation",(0,0,0,1))),
             pose.get((node,"scale"),v.get("scale",(1,1,1))))
  cache[node]=mul(world(parents[node]),local) if node in parents else local
  visiting.remove(node)
  return cache[node]
 result={}
 for node in nodes:
  if "mesh" not in node or "skin" not in node:continue
  skin=d["skins"][node["skin"]]
  if len(skin["joints"])<2:raise ValueError("NO_REAL_HIERARCHICAL_SKIN")
  ibm=accessor(d,b,skin["inverseBindMatrices"])
  if len(ibm)<len(skin["joints"]):raise ValueError("IBM_JOINT_COUNT")
  matrices=[mul(world(j),ibm[i]) for i,j in enumerate(skin["joints"])]
  vertices=[]
  for primitive in d["meshes"][node["mesh"]]["primitives"]:
   attrs=primitive["attributes"]
   positions=accessor(d,b,attrs["POSITION"])
   joints=accessor(d,b,attrs["JOINTS_0"])
   weights=accessor(d,b,attrs["WEIGHTS_0"])
   if len(positions)!=len(joints) or len(positions)!=len(weights):raise ValueError("ATTR_COUNT")
   for pos,js,ws in zip(positions,joints,weights):
    if abs(sum(ws)-1)>1e-4 or any(w<0 or not math.isfinite(w) for w in ws):
     raise ValueError("SKIN_WEIGHTS_NOT_NORMALIZED")
    xyz=[0.,0.,0.,0.]
    for j,weight in zip(js,ws):
     if not weight:continue
     if j>=len(matrices):raise ValueError("OUT_OF_RANGE_JOINT_INDEX")
     value=mv(matrices[j],tuple(pos)+(1.,))
     for component in range(4):xyz[component]+=weight*value[component]
    vertices.append((xyz[0],-xyz[2],xyz[1]))
  result[node["name"].split("_SkinnedMesh")[0]]=vertices
 if not result:raise ValueError("NO_IMPORTED_SKINNED_MESH")
 return result
def main():
 parser=argparse.ArgumentParser()
 parser.add_argument("--glb",required=True)
 parser.add_argument("--truth",required=True)
 parser.add_argument("--out",required=True)
 args=parser.parse_args()
 d,b,sha=read_glb(args.glb);truth=json.loads(Path(args.truth).read_text())
 if truth["schema"]!="scp.walk_w15_source_truth.v1" or truth["source_rights"]!="ORIGINAL_SELF_AUTHORED_SYNTHETIC":
  raise ValueError("TRUTH_PROVENANCE")
 if truth["frames"]!=[0,12,24,36,48,60,71]:raise ValueError("SOURCE_FRAME_TIMES_OR_ORDER")
 if len(truth["world_vertices"])!=7:raise ValueError("SOURCE_TRUTH_FRAME_COUNT")
 if truth["glb_sha256"]!=sha:raise ValueError("TRUTH_NOT_BOUND_TO_EXACT_GLB")
 maximum=0.;sample_count=0
 for f in truth["frames"]:
  actual=evaluate(d,b,f/12)
  expected=truth["world_vertices"][str(f)]
  if set(actual)!=set(expected):raise ValueError("ACTOR_NAMES_MISMATCH")
  for actor,refs in expected.items():
   data=actual[actor]
   if len(refs)!=len(data):raise ValueError("INDEXED_VERTEX_COUNT_CHANGED")
   for i,(a,v) in enumerate(zip(refs,data)):
    error=math.dist(a,v);maximum=max(maximum,error);sample_count+=1
    if error>5e-4:raise ValueError("PURE_GLTF_INDEXED_VERTEX_MISMATCH:"+actor+":"+str(f)+":"+str(i)+":"+str(error))
 receipt={"schema":"scp.walk_w15_independent_gltf_lbs.v1",
          "status":"PASS_PURE_STDLIB_GLTF_LBS_ANIMATION_INDEXED",
          "source_rights":"ORIGINAL_SELF_AUTHORED_SYNTHETIC",
          "glb_sha256":sha,"indexed_vertex_observations":sample_count,
          "maximum_world_position_error":maximum,
          "truth_source":"NATIVE_ORIGINAL_BLENDER_BEFORE_EXPORT",
          "reader":"PURE_PYTHON_STDLIB_NO_BPY_NO_GLTF_LOADER",
          "scope":"TWO_SOURCE_ORIGINAL_3D_SKINNED_AVATARS_NOT_BIOMECHANICS",
          "unqualified_features":["CUBICSPLINE","sparse_accessor","multiple_influence_sets","dual_quaternion"]}
 Path(args.out).write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
 print("W15_PURE_INDEPENDENT_GLTF_VERTEX_PASS",json.dumps(receipt,sort_keys=True))
if __name__=="__main__":main()
