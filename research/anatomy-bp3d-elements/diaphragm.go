// R036 forensic report on original BP3D FJ3131 diaphragm component topology.
// Exact coordinate identities only, never mutate or export original geometry.
package main

import(
 "archive/zip"
 "encoding/json"
 "errors"
 "fmt"
 "math"
 "path"
 "sort"
 "strings"
)
type RawBox struct{
 Min [3]float64 `json:"min_raw"`
 Max [3]float64 `json:"max_raw"`
}
type AtomicComponent struct{
 VertexCount int `json:"vertices"`
 SourceFaces int `json:"source_faces"`
 UniqueEdges int `json:"unique_edges"`
 Bounds RawBox `json:"raw_source_bounds"`
}
type EdgeIncident struct{
 CanonicalA int `json:"canonical_vertex_a"`
 CanonicalB int `json:"canonical_vertex_b"`
 FaceCount int `json:"face_incidence"`
 FaceExamples []int `json:"face_indices_sample"`
 DuplicateFaceIncidences int `json:"duplicate_source_face_count"`
}
type DiaphragmReceipt struct{
 Schema string `json:"schema"`
 Status string `json:"status"`
 OriginalSourceSHA256 string `json:"source_fj3131_sha256"`
 SourceZIP_SHA256 string `json:"source_zip_sha256"`
 SourceTableSHA256 string `json:"source_table_sha256"`
 SourceUnits string `json:"source_units"`
 SourceVertices int `json:"source_vertices"`
 SourceFaces int `json:"source_faces"`
 ExactCanonicalVertices int `json:"canonical_exact_coordinate_vertices"`
 ExactMerged int `json:"merged_zero_displacement_vertices"`
 VertexConnectedComponentCount int `json:"vertex_connected_component_count"`
 EdgeConnectedFaceComponents int `json:"edge_connected_face_components"`
 SourceDuplicateFaces int `json:"source_duplicate_faces_after_exact_remap"`
 NonmanifoldEdges int `json:"nonmanifold_edges"`
 BoundaryEdges int `json:"boundary_edges"`
 NonmanifoldExamples []EdgeIncident `json:"nonmanifold_examples"`
 LargestComponents []AtomicComponent `json:"largest_components"`
 Caveats []string `json:"caveats"`
}
func forensic(m meshData)(DiaphragmReceipt,error){
 out:=DiaphragmReceipt{Schema:"scp.anatomy.bp3d.diaphragm_incidence.v1",
  Status:"HOLD_DIAPHRAGM_NONMANIFOLD_OR_DISCONNECTED",
  OriginalSourceSHA256:m.SourceSHA,
  SourceUnits:"UNKNOWN_ORIGINAL_BP3D_RAW_COORDINATES",
  NonmanifoldExamples:[]EdgeIncident{},
  LargestComponents:[]AtomicComponent{},
  Caveats:[]string{
   "Connected by a shared vertex does not mean connected by manifold face edges",
   "A duplicated face can create >2 incidence, but its deletion is NOT automatically authorized",
   "Source FJ3131 is a single atomic mesh, not an assembled/registered whole-body diaphragm",
   "No source data, shape, face winding or topology are edited by this forensic audit",
  }}
 if len(m.Vertices)<4||len(m.Faces)<2{return out,errors.New("EMPTY_SOURCE_DIAPHRAGM")}
 out.SourceVertices=len(m.Vertices);out.SourceFaces=len(m.Faces)
 exact:=map[vertex]int{}
 reverse:=[]vertex{}
 remap:=make([]int,len(m.Vertices))
 for i,v:=range m.Vertices{
  if math.IsNaN(v.X)||math.IsNaN(v.Y)||math.IsNaN(v.Z)||
  math.IsInf(v.X,0)||math.IsInf(v.Y,0)||math.IsInf(v.Z,0){return out,errors.New("NONFINITE_SOURCE")}
  id,ok:=exact[v]
  if !ok{id=len(reverse);exact[v]=id;reverse=append(reverse,v)}
  remap[i]=id
 }
 out.ExactCanonicalVertices=len(reverse)
 out.ExactMerged=len(m.Vertices)-len(reverse)
 verts:=newDSU(len(reverse))
 faces:=newDSU(len(m.Faces))
 incidence:=map[Edge][]int{}
 signed:=map[Edge]int{}
 faceHashes:=map[string]int{}
 duplicateFaces:=map[int]bool{}
 touched:=map[int]bool{}
 faceCanonical:=make([][]int,len(m.Faces))
 for fi,f:=range m.Faces{
  if len(f)<3{return out,errors.New("INVALID_SOURCE_POLYGON")}
  indices:=make([]int,len(f))
  for i,old:=range f{
   if old<0||old>=len(remap){return out,errors.New("FACE_INDEX_OOB")}
   indices[i]=remap[old];touched[indices[i]]=true
  }
  faceCanonical[fi]=indices
  sorted:=append([]int(nil),indices...)
  sort.Ints(sorted)
  signature:=fmt.Sprint(sorted)
  if old,ok:=faceHashes[signature];ok{
   duplicateFaces[old]=true;duplicateFaces[fi]=true
  }else{faceHashes[signature]=fi}
  for i:=0;i<len(indices);i++{
   a,b:=indices[i],indices[(i+1)%len(indices)]
   if a==b{return out,errors.New("EXACT_WELD_COLLAPSED_SOURCE_FACE")}
   verts.union(a,b)
   key:=Edge{A:a,B:b};sign:=1
   if a>b{key=Edge{A:b,B:a};sign=-1}
   incidence[key]=append(incidence[key],fi);signed[key]+=sign
  }
 }
 out.SourceDuplicateFaces=len(duplicateFaces)
 for _,incident:=range incidence{
  if len(incident)>=2{
   first:=incident[0]
   for _,second:=range incident[1:]{faces.union(first,second)}
  }
 }
 componentIdx:=map[int]int{}
 components:=[]AtomicComponent{}
 for vi:=range touched{
  root:=verts.find(vi)
  n,ok:=componentIdx[root]
  if !ok{
   n=len(components);componentIdx[root]=n
   components=append(components,AtomicComponent{
    Bounds:RawBox{
     Min:[3]float64{math.Inf(1),math.Inf(1),math.Inf(1)},
     Max:[3]float64{math.Inf(-1),math.Inf(-1),math.Inf(-1)},
    },
   })
  }
  v:=reverse[vi];c:=&components[n]
  c.VertexCount++
  for ax,x:=range []float64{v.X,v.Y,v.Z}{
   if x<c.Bounds.Min[ax]{c.Bounds.Min[ax]=x}
   if x>c.Bounds.Max[ax]{c.Bounds.Max[ax]=x}
  }
 }
 for _,f:=range faceCanonical{
  root:=verts.find(f[0])
  ci,ok:=componentIdx[root];if !ok{return out,errors.New("LOST_VERTEX_COMPONENT")}
  components[ci].SourceFaces++
 }
 for edge,incident:=range incidence{
  root:=verts.find(edge.A);ci,ok:=componentIdx[root]
  if !ok{return out,errors.New("LOST_EDGE_COMPONENT")}
  components[ci].UniqueEdges++
  if len(incident)==1{out.BoundaryEdges++}
  if len(incident)>2{
   out.NonmanifoldEdges++
   observed:=append([]int(nil),incident...)
   sort.Ints(observed)
   preview:=observed
   if len(preview)>10{preview=preview[:10]}
   dup:=0
   for _,idx:=range observed{if duplicateFaces[idx]{dup++}}
   out.NonmanifoldExamples=append(out.NonmanifoldExamples,EdgeIncident{
    CanonicalA:edge.A,CanonicalB:edge.B,FaceCount:len(incident),
    FaceExamples:preview,DuplicateFaceIncidences:dup,
   })
  }
 }
 faceRoots:=map[int]bool{}
 for i:=range m.Faces{faceRoots[faces.find(i)]=true}
 out.EdgeConnectedFaceComponents=len(faceRoots)
 out.VertexConnectedComponentCount=len(components)
 sort.Slice(out.NonmanifoldExamples,func(i,j int)bool{
  a,b:=out.NonmanifoldExamples[i],out.NonmanifoldExamples[j]
  if a.FaceCount!=b.FaceCount{return a.FaceCount>b.FaceCount}
  if a.CanonicalA!=b.CanonicalA{return a.CanonicalA<b.CanonicalA}
  return a.CanonicalB<b.CanonicalB
 })
 sort.Slice(components,func(i,j int)bool{
  if components[i].VertexCount!=components[j].VertexCount{return components[i].VertexCount>components[j].VertexCount}
  return components[i].SourceFaces>components[j].SourceFaces
 })
 out.LargestComponents=components
 if len(out.LargestComponents)>16{out.LargestComponents=out.LargestComponents[:16]}
 if out.NonmanifoldEdges==0&&out.BoundaryEdges==0&&
 out.VertexConnectedComponentCount==1&&out.EdgeConnectedFaceComponents==1&&out.SourceDuplicateFaces==0{
  out.Status="SOURCE_TOPOLOGY_CANDIDATE_NEEDS_SELF_INTERSECTION_AND_VOLUME"
 }
 return out,nil
}
func inspectDiaphragm(table,archive string)(DiaphragmReceipt,error){
 out:=DiaphragmReceipt{Schema:"scp.anatomy.bp3d.diaphragm_incidence.v1"}
 var e error
 out.SourceTableSHA256,_,e=digestFile(table);if e!=nil{return out,e}
 out.SourceZIP_SHA256,_,e=digestFile(archive);if e!=nil{return out,e}
 if out.SourceTableSHA256!="3f5f6df1028eb122b30de77c711597b6bb8e5541658e5985859fd228adbf88ea"||
    out.SourceZIP_SHA256!="9fbc713fffeee924a5a657d9813d84d7eb957bded63adb854931dd5e3eb61c97"{
  return out,errors.New("UNVERIFIED_PRIMARY_SOURCE")
 }
 z,e:=zip.OpenReader(archive);if e!=nil{return out,e};defer z.Close()
 var source *zip.File
 for _,f:=range z.File{
  if strings.Contains(f.Name,"..")||strings.Contains(f.Name,"\\")||strings.HasPrefix(f.Name,"/"){return out,errors.New("UNSAFE_SOURCE_ZIP_PATH")}
  id:=strings.TrimSuffix(strings.ToUpper(path.Base(f.Name)),".OBJ")
  if id=="FJ3131"{if source!=nil{return out,errors.New("DUPLICATE_FJ3131")};source=f}
 }
 if source==nil||source.UncompressedSize64>6*1024*1024{return out,errors.New("ABSENT_OR_OVERSIZED_FJ3131")}
 reader,e:=source.Open();if e!=nil{return out,e}
 m,parseE:=originalMesh(reader,6*1024*1024)
 closeE:=reader.Close()
 if parseE!=nil{return out,parseE}
 if closeE!=nil{return out,closeE}
 if m.SourceSHA!="2a78d0f155249d4b8348e9656170af4caf2b41778c0e047fc8c1c6890878058b"{
  return out,errors.New("PRIMARY_FJ3131_FILE_SHA_MISMATCH")
 }
 found,e:=forensic(m);if e!=nil{return out,e}
 found.SourceZIP_SHA256=out.SourceZIP_SHA256
 found.SourceTableSHA256=out.SourceTableSHA256
 return found,nil
}
func emitDiaphragm(table,archive string)error{
 r,e:=inspectDiaphragm(table,archive);if e!=nil{return e}
 b,e:=json.Marshal(r);if e!=nil{return e}
 fmt.Println("R036_DIAPHRAGM_INCIDENCE_RECEIPT",string(b))
 return nil
}
