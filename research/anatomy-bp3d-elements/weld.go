// Bounded read-only donor-mesh seam qualification. An edge-paired surface after
// coordinate welding is NOT automatically medically accurate or volumetric.
package main

import (
 "archive/zip"
 "bufio"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "math"
 "path"
 "sort"
 "strconv"
 "strings"
)
const seamSchema="scp.anatomy.bp3d.atomic_seam_diagnostics.v1"
type vertex struct{X,Y,Z float64}
type meshData struct{
 Vertices []vertex
 Faces [][]int
 SourceSHA string
}
type SeamState struct{
 ToleranceRawUnits float64 `json:"candidate_tolerance_raw_source_units"`
 OriginalVertices int `json:"original_vertices"`
 CandidateVertices int `json:"candidate_vertices"`
 VerticesMerged int `json:"candidate_vertices_merged"`
 MaximumWeldDisplacementRaw float64 `json:"maximum_weld_displacement_raw_units"`
 OriginalFaces int `json:"original_faces"`
 DegeneratePostWeldFaces int `json:"post_weld_degenerate_faces"`
 BoundaryEdges int `json:"post_weld_boundary_edges"`
 NonmanifoldEdges int `json:"post_weld_nonmanifold_edges"`
 OrientedConflicts int `json:"post_weld_oriented_edge_conflicts"`
 Components int `json:"post_weld_vertex_components"`
 Status string `json:"status"`
}
type SeamMesh struct {
 SourceFJ string `json:"source_fj"`
 OriginalMemberSHA256 string `json:"source_member_sha256"`
 OriginalTopology MeshTopology `json:"original_topology"`
 Candidate []SeamState `json:"candidate_welds"`
}
type SeamReport struct{
 Schema string `json:"schema"`
 Status string `json:"status"`
 SourceArchiveSHA256 string `json:"source_archive_sha256"`
 SourceTableSHA256 string `json:"source_table_sha256"`
 SourceUnitProof string `json:"source_unit_proof"`
 Meshes []SeamMesh `json:"meshes"`
 Limits string `json:"limits"`
}
func originalMesh(f io.Reader,maxBytes int64)(meshData,error){
 m:=meshData{Vertices:[]vertex{},Faces:[][]int{}}
 hash:=sha256.New()
 s:=bufio.NewScanner(io.TeeReader(io.LimitReader(f,maxBytes+1),hash))
 s.Buffer(make([]byte,2048),2*1024*1024)
 total:=int64(0)
 for s.Scan(){
  row:=s.Bytes();total+=int64(len(row))+1
  if total>maxBytes{return m,errors.New("source OBJ uncompressed component cap")}
  tok:=strings.Fields(string(row));if len(tok)==0{continue}
  switch tok[0]{
  case "v":
   if len(tok)<4{return m,errors.New("malformed source mesh vertex")}
   var v vertex
   a,e1:=strconv.ParseFloat(tok[1],64)
   b,e2:=strconv.ParseFloat(tok[2],64)
   c,e3:=strconv.ParseFloat(tok[3],64)
   if e1!=nil||e2!=nil||e3!=nil||math.IsNaN(a)||math.IsNaN(b)||math.IsNaN(c)||
    math.IsInf(a,0)||math.IsInf(b,0)||math.IsInf(c,0){return m,errors.New("source non-finite vertex")}
   v=vertex{a,b,c};m.Vertices=append(m.Vertices,v)
   if len(m.Vertices)>100000{return m,errors.New("component vertex memory cap")}
  case "f":
   if len(tok)<4{return m,errors.New("source degenerate face")}
   face:=[]int{}
   for _,term:=range tok[1:]{
    p,e:=faceVertexIndex(term,len(m.Vertices))
    if e!=nil{return m,e}
    face=append(face,p)
   }
   m.Faces=append(m.Faces,face)
   if len(m.Faces)>200000{return m,errors.New("component face memory cap")}
  }
 }
 if e:=s.Err();e!=nil{return m,e}
 if len(m.Vertices)<4||len(m.Faces)<2{return m,errors.New("not an admitted mesh surface sample")}
 m.SourceSHA=hex.EncodeToString(hash.Sum(nil))
 return m,nil
}
type quant [3]int64
func vDelta(a,b vertex)float64{
 x,y,z:=a.X-b.X,a.Y-b.Y,a.Z-b.Z
 return math.Sqrt(x*x+y*y+z*z)
}
func quantize(v vertex,eps float64)(quant,error){
 var out quant
 for i,x:=range []float64{v.X,v.Y,v.Z}{
  q:=math.Round(x/eps)
  if math.IsInf(q,0)||math.IsNaN(q)||math.Abs(q)>9e15{return out,errors.New("unsafe weld bin dimension")}
  out[i]=int64(q)
 }
 return out,nil
}
func checkMeshAfterWeld(m meshData,eps float64)(SeamState,error){
 out:=SeamState{ToleranceRawUnits:eps,OriginalVertices:len(m.Vertices),OriginalFaces:len(m.Faces),
  Status:"HOLD_UNMEASURED_SOURCE_WELD"}
 if eps<=0||eps>.01||math.IsNaN(eps)||math.IsInf(eps,0){
  return out,errors.New("unbounded source seam tolerance")
 }
 assign:=make([]int,len(m.Vertices))
 first:=map[quant]int{}
 representatives:=[]vertex{}
 for i,v:=range m.Vertices{
  q,e:=quantize(v,eps);if e!=nil{return out,e}
  if prior,ok:=first[q];ok{
   assign[i]=prior
   dist:=vDelta(v,representatives[prior])
   if dist>math.Sqrt(3)*eps+1e-8{return out,errors.New("weld displacement above conservative voxel cap")}
   if dist>out.MaximumWeldDisplacementRaw{out.MaximumWeldDisplacementRaw=dist}
  }else{
   assign[i]=len(representatives)
   first[q]=len(representatives)
   representatives=append(representatives,v)
  }
 }
 out.CandidateVertices=len(representatives)
 out.VerticesMerged=len(m.Vertices)-len(representatives)
 edges:=map[Edge]int{};orientation:=map[Edge]int{}
 touched:=map[int]bool{}
 connectivity:=newDSU(len(representatives))
 for _,old:=range m.Faces{
  ids:=make([]int,len(old))
  seen:=map[int]bool{}
  for i,v:=range old{
   ids[i]=assign[v]
   if seen[ids[i]]{out.DegeneratePostWeldFaces++}
   seen[ids[i]]=true;touched[ids[i]]=true
  }
  for i:=range ids{
   a,b:=ids[i],ids[(i+1)%len(ids)]
   if a==b{continue}
   edge:=Edge{a,b};sign:=1
   if a>b{edge=Edge{b,a};sign=-1}
   edges[edge]++;orientation[edge]+=sign
   connectivity.union(a,b)
  }
 }
 for e,n:=range edges{
  if n==1{out.BoundaryEdges++}
  if n>2{out.NonmanifoldEdges++}
  if n==2&&orientation[e]!=0{out.OrientedConflicts++}
 }
 comps:=map[int]bool{}
 for v:=range touched{comps[connectivity.find(v)]=true}
 out.Components=len(comps)
 if out.BoundaryEdges==0&&out.NonmanifoldEdges==0&&out.OrientedConflicts==0&&
  out.DegeneratePostWeldFaces==0&&len(touched)==len(representatives){
  out.Status="EDGE_PAIRED_AFTER_PROPOSED_WELD_NOT_ANATOMICAL_ACCEPTANCE"
 }else{
  out.Status="HOLD_OPEN_OR_NONMANIFOLD_AFTER_PROPOSED_WELD"
 }
 return out,nil
}
func investigateSeams(table,archive string)(SeamReport,error){
 result:=SeamReport{
  Schema:seamSchema,Status:"SOURCE_SEAM_EXPERIMENT_ONLY_NO_ANATOMICAL_FIT",
  SourceUnitProof:"UNKNOWN_ATLAS_COORDINATES_NOT_SI_CALIBRATED",
  Limits:"Only 5 selected original atomic OBJ meshes, <=6MiB per member, candidate tolerances 0.00001, 0.001, 0.01 raw dataset coordinates; source immutable",
  Meshes:[]SeamMesh{},
 }
 var err error
 result.SourceTableSHA256,_,err=digestFile(table);if err!=nil{return result,err}
 result.SourceArchiveSHA256,_,err=digestFile(archive);if err!=nil{return result,err}
 if result.SourceTableSHA256!="3f5f6df1028eb122b30de77c711597b6bb8e5541658e5985859fd228adbf88ea"||
  result.SourceArchiveSHA256!="9fbc713fffeee924a5a657d9813d84d7eb957bded63adb854931dd5e3eb61c97"{
  return result,errors.New("unverified original BP3D source hash")
 }
 z,e:=zip.OpenReader(archive);if e!=nil{return result,e};defer z.Close()
 members:=map[string]*zip.File{}
 for _,file:=range z.File{
  if strings.Contains(file.Name,"..")||strings.HasPrefix(file.Name,"/")||strings.Contains(file.Name,"\\"){return result,errors.New("unsafe source ZIP member")}
  id:=strings.TrimSuffix(strings.ToUpper(path.Base(file.Name)),".OBJ")
  if fj.MatchString(id){
   if members[id]!=nil{return result,errors.New("duplicate atomic FJ source")}
   members[id]=file
  }
 }
 selected:=[]string{"FJ2417","FJ2441","FJ2041","FJ3131","FJ1883"}
 for _,id:=range selected{
  file:=members[id]
  if file==nil{return result,fmt.Errorf("missing source atomic component %s",id)}
  if file.UncompressedSize64>6*1024*1024{return result,errors.New("selected source component is no longer bounded")}
  handle,e:=file.Open();if e!=nil{return result,e}
  donor,readErr:=originalMesh(handle,6*1024*1024)
  closeErr:=handle.Close()
  if readErr!=nil{return result,readErr}
  if closeErr!=nil{return result,closeErr}
  handle,e=file.Open();if e!=nil{return result,e}
  original,scanErr:=scanTopology(handle,6*1024*1024,id)
  closeErr=handle.Close()
  if scanErr!=nil{return result,scanErr}
  if closeErr!=nil{return result,closeErr}
  if original.SourceSHA256!=donor.SourceSHA{return result,errors.New("independent source parser hash mismatch")}
  item:=SeamMesh{SourceFJ:id,OriginalMemberSHA256:donor.SourceSHA,
   OriginalTopology:original,Candidate:[]SeamState{}}
  for _,epsilon:=range []float64{.00001,.001,.01}{
   x,e:=checkMeshAfterWeld(donor,epsilon)
   if e!=nil{return result,fmt.Errorf("element %s tolerance %g: %w",id,epsilon,e)}
   item.Candidate=append(item.Candidate,x)
  }
  result.Meshes=append(result.Meshes,item)
 }
 sort.Slice(result.Meshes,func(i,j int)bool{return result.Meshes[i].SourceFJ<result.Meshes[j].SourceFJ})
 return result,nil
}
func emitSeams(table,archive string)error{
 r,e:=investigateSeams(table,archive);if e!=nil{return e}
 b,e:=json.Marshal(r);if e!=nil{return e}
 fmt.Println("R036_SEAM_WELD_RECEIPT",string(b))
 return nil
}
