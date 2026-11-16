// R036 independently computed candidate signed volume on exact vertex-remapped
// original atomic BodyParts3D polygon surfaces. Geometry remains unqualified.
package main

import (
 "archive/zip"
 "encoding/json"
 "errors"
 "fmt"
 "math"
 "path"
 "sort"
 "strings"
)
const solidSchema="scp.anatomy.bp3d.atomic_signed_volume.v1"
type Vec3 struct{X,Y,Z float64}
func minus(a,b vertex)Vec3{return Vec3{a.X-b.X,a.Y-b.Y,a.Z-b.Z}}
func cross3(a,b Vec3)Vec3{return Vec3{a.Y*b.Z-a.Z*b.Y,a.Z*b.X-a.X*b.Z,a.X*b.Y-a.Y*b.X}}
func dot3(a,b Vec3)float64{return a.X*b.X+a.Y*b.Y+a.Z*b.Z}
type SolidCandidate struct{
 SourceFJ string `json:"source_fj"`
 SourceMemberSHA256 string `json:"source_member_sha256"`
 OriginalVertices int `json:"original_vertices"`
 DistinctExactCoordinates int `json:"distinct_exact_coordinates"`
 DuplicateVertexIndices int `json:"duplicate_vertex_indices"`
 Faces int `json:"source_faces"`
 Edges int `json:"exact_weld_edges"`
 OpenEdges int `json:"open_edges"`
 NonmanifoldEdges int `json:"nonmanifold_edges"`
 OrientationConflicts int `json:"orientation_conflicts"`
 DegenerateFaceCount int `json:"degenerate_face_count"`
 Components int `json:"vertex_connected_components"`
 EulerCharacteristic int `json:"euler_characteristic"`
 SignedVolumeRawUnitsCubed *float64 `json:"signed_volume_raw_units_cubed,omitempty"`
 IndependentOriginDiscrepancyRawUnitsCubed *float64 `json:"independent_origin_discrepancy_raw_units_cubed,omitempty"`
 Status string `json:"status"`
}
type SolidReport struct{
 Schema string `json:"schema"`
 Status string `json:"status"`
 SourceTableSHA256 string `json:"source_table_sha256"`
 SourceArchiveSHA256 string `json:"source_archive_sha256"`
 ReferenceCoordinateUnits string `json:"reference_coordinate_units"`
 Probed []SolidCandidate `json:"probed"`
 Caveats []string `json:"caveats"`
}
func exactVertexRemap(m meshData)([]vertex,[]int,error){
 canon:=make([]vertex,0,len(m.Vertices))
 indices:=make([]int,len(m.Vertices))
 ids:=map[vertex]int{}
 for i,v:=range m.Vertices{
  if math.IsNaN(v.X)||math.IsNaN(v.Y)||math.IsNaN(v.Z)||
     math.IsInf(v.X,0)||math.IsInf(v.Y,0)||math.IsInf(v.Z,0){
    return nil,nil,errors.New("NONFINITE_EXACT_VERTEX")
  }
  idx,ok:=ids[v]
  if !ok{idx=len(canon);ids[v]=idx;canon=append(canon,v)}
  indices[i]=idx
 }
 return canon,indices,nil
}
func volumeFromOrigin(verts []vertex,faces [][]int,origin vertex)float64{
 total:=0.0
 for _,face:=range faces{
  if len(face)<3{continue}
  a:=minus(verts[face[0]],origin)
  for i:=1;i+1<len(face);i++{
   b:=minus(verts[face[i]],origin)
   c:=minus(verts[face[i+1]],origin)
   total+=dot3(a,cross3(b,c))/6
  }
 }
 return total
}
func signedVolumeCandidate(m meshData,source string)(SolidCandidate,error){
 out:=SolidCandidate{SourceFJ:source,SourceMemberSHA256:m.SourceSHA,
  OriginalVertices:len(m.Vertices),Faces:len(m.Faces),Status:"HOLD_UNINSPECTED"}
 if len(m.Vertices)<4||len(m.Faces)<2{return out,errors.New("NOT_A_SURFACE")}
 v,remap,e:=exactVertexRemap(m);if e!=nil{return out,e}
 out.DistinctExactCoordinates=len(v)
 out.DuplicateVertexIndices=out.OriginalVertices-len(v)
 edges:=map[Edge]int{};oriented:=map[Edge]int{}
 faceIndex:=make([][]int,0,len(m.Faces))
 connectivity:=newDSU(len(v))
 touched:=map[int]bool{}
 for _,old:=range m.Faces{
  if len(old)<3{return out,errors.New("INVALID_SOURCE_POLYGON")}
  face:=make([]int,len(old));seen:=map[int]bool{}
  for i,idx:=range old{
   if idx<0||idx>=len(remap){return out,errors.New("BAD_SOURCE_VERTEX_INDEX")}
   face[i]=remap[idx]
   if seen[face[i]]{out.DegenerateFaceCount++}
   seen[face[i]]=true;touched[face[i]]=true
  }
  if len(seen)<3{out.DegenerateFaceCount++}
  for i:=range face{
   a,b:=face[i],face[(i+1)%len(face)]
   if a==b{out.DegenerateFaceCount++;continue}
   key:=Edge{A:a,B:b};direction:=1
   if a>b{key=Edge{A:b,B:a};direction=-1}
   edges[key]++;oriented[key]+=direction
   connectivity.union(a,b)
  }
  faceIndex=append(faceIndex,face)
 }
 out.Edges=len(edges)
 for key,n:=range edges{
  if n==1{out.OpenEdges++}
  if n>2{out.NonmanifoldEdges++}
  if n==2&&oriented[key]!=0{out.OrientationConflicts++}
 }
 comps:=map[int]bool{}
 for idx:=range touched{comps[connectivity.find(idx)]=true}
 out.Components=len(comps)
 out.EulerCharacteristic=len(touched)-len(edges)+len(faceIndex)
 if out.OpenEdges>0||out.NonmanifoldEdges>0||
    out.OrientationConflicts>0||out.DegenerateFaceCount>0||
    len(touched)!=len(v)||out.Components!=1{
  out.Status="HOLD_NONMANIFOLD_OPEN_OR_MULTICOMPONENT_SOLID"
  return out,nil
 }
 // Origin translation makes tetrahedralization less vulnerable to catastrophic
 // cancellation on atlas-world coordinates far from zero.
 origin:=v[0]
 centroid:=vertex{}
 for _,p:=range v{centroid.X+=p.X;centroid.Y+=p.Y;centroid.Z+=p.Z}
 n:=float64(len(v));centroid.X/=n;centroid.Y/=n;centroid.Z/=n
 first:=volumeFromOrigin(v,faceIndex,origin)
 second:=volumeFromOrigin(v,faceIndex,centroid)
 if math.IsNaN(first)||math.IsNaN(second)||math.IsInf(first,0)||math.IsInf(second,0){
  return out,errors.New("NONFINITE_VOLUME")
 }
 out.IndependentOriginDiscrepancyRawUnitsCubed=new(float64)
 *out.IndependentOriginDiscrepancyRawUnitsCubed=math.Abs(first-second)
 out.SignedVolumeRawUnitsCubed=&second
 // Both computations share triangles but differ in numerically challenging
 // origin; this is a stability check, NOT an independent clinical oracle.
 if math.Abs(first-second)>1e-8*math.Max(1,math.Abs(second)){
  out.Status="HOLD_ORIGIN_VOLUME_INSTABILITY"
 }else if second<=0{
  out.Status="HOLD_INWARD_OR_ZERO_SIGNED_VOLUME"
 }else{
  out.Status="CANDIDATE_SIGNED_VOLUME_SURFACE_ONLY"
 }
 return out,nil
}
func inspectRealSourceVolume(table,archive string)(SolidReport,error){
 out:=SolidReport{Schema:solidSchema,
  Status:"SOURCE_ATOMIC_SIGNED_VOLUME_NOT_BIOMECHANICS_QUALIFIED",
  ReferenceCoordinateUnits:"UNKNOWN_NOT_SI_ADMITTED",Probed:[]SolidCandidate{},
  Caveats:[]string{
   "Only exact duplicate source coordinates are remapped, without moving any source vertex",
   "Signed volume is an algebraic surface integral, not a physical tissue measurement or self-intersection oracle",
   "A closed edge-paired surface may self-intersect or represent multiple overlapping shells",
   "Composite FMA organs consist of many FJ components; this workcell inspects only 5 atomic original meshes",
   "Reference source units, anatomy-side registration, phenotype and rib/pleura boundaries unqualified",
  }}
 var e error
 out.SourceTableSHA256,_,e=digestFile(table);if e!=nil{return out,e}
 out.SourceArchiveSHA256,_,e=digestFile(archive);if e!=nil{return out,e}
 if out.SourceTableSHA256!="3f5f6df1028eb122b30de77c711597b6bb8e5541658e5985859fd228adbf88ea"||
    out.SourceArchiveSHA256!="9fbc713fffeee924a5a657d9813d84d7eb957bded63adb854931dd5e3eb61c97"{
  return out,errors.New("ORIGINAL_SOURCE_SHA256_MISMATCH")
 }
 z,e:=zip.OpenReader(archive);if e!=nil{return out,e};defer z.Close()
 members:=map[string]*zip.File{}
 for _,file:=range z.File{
  if strings.HasPrefix(file.Name,"/")||strings.Contains(file.Name,"..")||
     strings.Contains(file.Name,"\\"){return out,errors.New("UNSAFE_SOURCE_ZIP_MEMBER")}
  id:=strings.TrimSuffix(strings.ToUpper(path.Base(file.Name)),".OBJ")
  if fj.MatchString(id){if members[id]!=nil{return out,errors.New("DUPLICATE_ATOMIC_SOURCE_ID")};members[id]=file}
 }
 if len(members)!=1258{return out,errors.New("ORIGINAL_SOURCE_ATOMIC_MESH_COUNT_CHANGED")}
 ids:=[]string{"FJ2417","FJ2441","FJ2041","FJ3131","FJ1883"}
 for _,id:=range ids{
  f:=members[id];if f==nil{return out,fmt.Errorf("source missing %s",id)}
  if f.UncompressedSize64>6*1024*1024{return out,errors.New("SOURCE_MEMBER_SIZE_CAP")}
  reader,e:=f.Open();if e!=nil{return out,e}
  m,parseE:=originalMesh(reader,6*1024*1024)
  closeE:=reader.Close();if parseE!=nil{return out,parseE};if closeE!=nil{return out,closeE}
  candidate,e:=signedVolumeCandidate(m,id);if e!=nil{return out,e}
  out.Probed=append(out.Probed,candidate)
 }
 sort.Slice(out.Probed,func(i,j int)bool{return out.Probed[i].SourceFJ<out.Probed[j].SourceFJ})
 return out,nil
}
func emitRealVolume(table,archive string)error{
 x,e:=inspectRealSourceVolume(table,archive);if e!=nil{return e}
 b,e:=json.Marshal(x);if e!=nil{return e}
 fmt.Println("R036_BP3D_SIGNED_VOLUME_RECEIPT",string(b))
 return nil
}
