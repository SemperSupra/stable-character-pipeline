// R036 nondestructive duplicate-face *candidate* on original FJ3131.
// Never mutate the source or quietly throw away tiny disconnected components.
package main

import(
 "archive/zip"
 "encoding/json"
 "errors"
 "fmt"
 "path"
 "sort"
 "strings"
)
type FaceDedup struct{
 Schema string `json:"schema"`
 Status string `json:"status"`
 SourceMemberSHA256 string `json:"source_member_sha256"`
 OriginalFaces int `json:"original_faces"`
 CandidateFaces int `json:"candidate_faces"`
 ExactSameWindingDuplicates int `json:"exact_same_winding_face_records_removed_from_candidate"`
 ReverseWindingCoincident int `json:"reverse_winding_coincident_source_faces_retained"`
 RemovedOriginalFaceIndices []int `json:"derived_candidate_excluded_original_face_indices"`
 BeforeNonmanifoldEdges int `json:"before_nonmanifold_edges"`
 AfterNonmanifoldEdges int `json:"after_nonmanifold_edges"`
 BeforeBoundaryEdges int `json:"before_boundary_edges"`
 AfterBoundaryEdges int `json:"after_boundary_edges"`
 BeforeComponents int `json:"before_vertex_components"`
 AfterComponents int `json:"after_vertex_components"`
 MainComponentVertices int `json:"main_component_vertices"`
 OtherComponentVertices int `json:"other_components_vertices"`
 OtherComponents int `json:"other_components"`
 OriginalMeshImmutable bool `json:"original_mesh_immutable"`
 Caveats []string `json:"caveats"`
}
func minLexRotation(poly []int)[]int{
 if len(poly)==0{return []int{}}
 best:=0
 for i:=1;i<len(poly);i++{
  for offset:=0;offset<len(poly);offset++{
   a:=poly[(i+offset)%len(poly)]
   b:=poly[(best+offset)%len(poly)]
   if a<b{best=i;break}
   if a>b{break}
  }
 }
 result:=make([]int,len(poly))
 for i:=range poly{result[i]=poly[(best+i)%len(poly)]}
 return result
}
func exactCyclic(poly []int)string{return fmt.Sprint(minLexRotation(poly))}
func reversePoly(poly []int)[]int{
 r:=make([]int,len(poly))
 for i,x:=range poly{r[len(poly)-1-i]=x}
 return r
}
func diagnoseFaceCopies(m meshData)(FaceDedup,error){
 out:=FaceDedup{Schema:"scp.anatomy.bp3d.diaphragm_face_derived.v1",
  Status:"HOLD_UNQUALIFIED_DIAPHRAGM_SOURCE",
  SourceMemberSHA256:m.SourceSHA,
  OriginalFaces:len(m.Faces),
  RemovedOriginalFaceIndices:[]int{},
  OriginalMeshImmutable:true,
  Caveats:[]string{
   "Same-winding cyclic duplicate faces are removed ONLY from a disposable derived topology candidate, not from the original OBJ",
   "Reverse-winding coincident polygons cannot be automatically discarded; they may encode opposing boundaries",
   "No vertex, coordinate, normals, tissue or FMA concept identity is altered in this experiment",
   "Any remaining multi-component geometry is HOLD pending validated source anatomical component membership",
  }}
 if len(m.Vertices)<4||len(m.Faces)<2{return out,errors.New("EMPTY_SOURCE")}
 // Remap exactly coincident coordinates for face identity comparison.
 exact:=map[vertex]int{}
 assign:=make([]int,len(m.Vertices))
 for i,v:=range m.Vertices{
  n,ok:=exact[v]
  if !ok{n=len(exact);exact[v]=n}
  assign[i]=n
 }
 forward:=map[string]int{}
 kept:=make([][]int,0,len(m.Faces))
 reverseSeen:=map[string]bool{}
 for i,face:=range m.Faces{
  poly:=make([]int,len(face))
  for j,sourceID:=range face{
   if sourceID<0||sourceID>=len(assign){return out,errors.New("INVALID_SOURCE_POLYGON_VERTEX")}
   poly[j]=assign[sourceID]
  }
  if len(poly)<3{return out,errors.New("DEGENERATE_SOURCE_POLYGON")}
  forwardKey:=exactCyclic(poly)
  reverseKey:=exactCyclic(reversePoly(poly))
  if _,dupe:=forward[forwardKey];dupe{
   out.ExactSameWindingDuplicates++
   out.RemovedOriginalFaceIndices=append(out.RemovedOriginalFaceIndices,i)
   continue
  }
  if _,reverseExists:=forward[reverseKey];reverseExists{
   if !reverseSeen[forwardKey]{out.ReverseWindingCoincident++}
   reverseSeen[forwardKey]=true
  }
  forward[forwardKey]=i
  // Keep original face index identity in the derived candidate; original
  // meshData and original OBJ binary remain byte-for-byte untouched.
  kept=append(kept,append([]int(nil),face...))
 }
 candidate:=meshData{Vertices:m.Vertices,Faces:kept,SourceSHA:m.SourceSHA}
 out.CandidateFaces=len(kept)
 before,e:=forensic(m);if e!=nil{return out,e}
 after,e:=forensic(candidate);if e!=nil{return out,e}
 out.BeforeNonmanifoldEdges=before.NonmanifoldEdges
 out.AfterNonmanifoldEdges=after.NonmanifoldEdges
 out.BeforeBoundaryEdges=before.BoundaryEdges
 out.AfterBoundaryEdges=after.BoundaryEdges
 out.BeforeComponents=before.VertexConnectedComponentCount
 out.AfterComponents=after.VertexConnectedComponentCount
 if len(after.LargestComponents)>0{
  out.MainComponentVertices=after.LargestComponents[0].VertexCount
  for _,c:=range after.LargestComponents[1:]{
   out.OtherComponentVertices+=c.VertexCount
   out.OtherComponents++
  }
 }
 if out.ExactSameWindingDuplicates==0{
  out.Status="HOLD_NO_EXACT_SAME_WINDING_FACE_DUPLICATES"
 }else if out.ReverseWindingCoincident>0{
  out.Status="HOLD_REVERSED_COINCIDENT_FACE_PAIRS"
 }else if out.AfterNonmanifoldEdges>out.BeforeNonmanifoldEdges||
         out.AfterBoundaryEdges>out.BeforeBoundaryEdges{
  out.Status="HOLD_DERIVED_CANDIDATE_TOPOLOGY_REGRESSION"
 }else if out.AfterComponents!=1||
         out.AfterNonmanifoldEdges!=0||out.AfterBoundaryEdges!=0{
  out.Status="HOLD_DERIVED_DIAPHRAGM_STILL_MULTICOMPONENT_OR_NONMANIFOLD"
 }else{
  out.Status="DERIVED_COMPONENT_TOPOLOGY_CANDIDATE_PHYSICS_HOLD"
 }
 return out,nil
}
func inspectDiaphragmFaceCandidate(table,archive string)(FaceDedup,error){
 out:=FaceDedup{Schema:"scp.anatomy.bp3d.diaphragm_face_derived.v1"}
 th,_,e:=digestFile(table);if e!=nil{return out,e}
 ah,_,e:=digestFile(archive);if e!=nil{return out,e}
 if th!="3f5f6df1028eb122b30de77c711597b6bb8e5541658e5985859fd228adbf88ea"||
 ah!="9fbc713fffeee924a5a657d9813d84d7eb957bded63adb854931dd5e3eb61c97"{
  return out,errors.New("UNVERIFIED_ORIGINAL_BP3D4_SOURCE")
 }
 z,e:=zip.OpenReader(archive);if e!=nil{return out,e};defer z.Close()
 var member *zip.File
 for _,f:=range z.File{
  if strings.HasPrefix(f.Name,"/")||strings.Contains(f.Name,"..")||strings.Contains(f.Name,"\\"){
   return out,errors.New("UNSAFE_ZIP_MEMBER")
  }
  if strings.EqualFold(path.Base(f.Name),"FJ3131.obj"){
   if member!=nil{return out,errors.New("DUPLICATE_SOURCE_COMPONENT")}
   member=f
  }
 }
 if member==nil||member.UncompressedSize64>6*1024*1024{return out,errors.New("SOURCE_COMPONENT_MISSING_OR_OVERSIZED")}
 handle,e:=member.Open();if e!=nil{return out,e}
 m,parseErr:=originalMesh(handle,6*1024*1024)
 closeErr:=handle.Close()
 if parseErr!=nil{return out,parseErr};if closeErr!=nil{return out,closeErr}
 if m.SourceSHA!="2a78d0f155249d4b8348e9656170af4caf2b41778c0e047fc8c1c6890878058b"{
  return out,errors.New("PRIMARY_DIAPHRAGM_COMPONENT_SHA_MISMATCH")
 }
 found,e:=diagnoseFaceCopies(m);if e!=nil{return out,e}
 sort.Ints(found.RemovedOriginalFaceIndices)
 return found,nil
}
func emitDiaphragmFaceCandidate(table,archive string)error{
 r,e:=inspectDiaphragmFaceCandidate(table,archive);if e!=nil{return e}
 b,e:=json.Marshal(r);if e!=nil{return e}
 fmt.Println("R036_DIAPHRAGM_FACE_DERIVED_RECEIPT",string(b))
 return nil
}
