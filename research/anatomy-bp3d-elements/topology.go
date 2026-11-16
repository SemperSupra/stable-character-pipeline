// R036 source-safe topology and FMA-to-FJ composite set qualification.
// A closed edge-pairing test does NOT establish watertightness, volume truth
// or anatomical correctness. Coordinates retain unqualified source units.
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
 "os"
 "path"
 "sort"
 "strconv"
 "strings"
)
const compositeSchema="scp.anatomy.bp3d.composite_topology.v1"
type Edge struct{A,B int}
type MeshTopology struct{
 ElementID string `json:"element_id"`
 SourceSHA256 string `json:"source_sha256"`
 Vertices int `json:"vertices"`
 Faces int `json:"faces"`
 Edges int `json:"undirected_edges"`
 BoundaryEdges int `json:"boundary_edges"`
 NonmanifoldEdges int `json:"nonmanifold_edges"`
 OrientedEdgeConflicts int `json:"oriented_edge_conflicts"`
 DegenerateFaces int `json:"degenerate_faces"`
 IsolatedVertices int `json:"isolated_vertices"`
 ConnectedVertexComponents int `json:"connected_vertex_components"`
 ClosedEdgePairing bool `json:"closed_edge_pairing_candidate"`
 Status string `json:"status"`
}
type CompositeGroup struct{
 ConceptID string `json:"concept_id"`
 Name string `json:"name"`
 AtomicElements int `json:"atomic_elements"`
 Sampled []MeshTopology `json:"sampled"`
}
type SharedAtoms struct{
 FirstConcept string `json:"first_concept"`
 SecondConcept string `json:"second_concept"`
 Shared int `json:"shared_atomic_element_ids"`
 Intersection []string `json:"shared_element_examples"`
}
type CompositeReport struct{
 Schema string `json:"schema"`
 Status string `json:"status"`
 SourceTableSHA256 string `json:"source_table_sha256"`
 SourceArchiveSHA256 string `json:"source_archive_sha256"`
 Groups []CompositeGroup `json:"groups"`
 Overlap []SharedAtoms `json:"overlap"`
 Inspected int `json:"inspected_atomic_meshes"`
 ClosedEdgePairingCandidates int `json:"closed_edge_pairing_candidates"`
 OpenOrNonmanifold int `json:"open_or_nonmanifold_components"`
 SourceCoordinateUnits string `json:"source_coordinate_units"`
 Caveats []string `json:"caveats"`
}
type dsu struct{parent,rank []int}
func newDSU(n int)*dsu{
 d:=&dsu{parent:make([]int,n),rank:make([]int,n)}
 for i:=range d.parent{d.parent[i]=i}
 return d
}
func (d *dsu)find(n int)int{
 if d.parent[n]!=n{d.parent[n]=d.find(d.parent[n])};return d.parent[n]
}
func (d *dsu)union(a,b int){
 a,b=d.find(a),d.find(b)
 if a==b{return}
 if d.rank[a]<d.rank[b]{a,b=b,a}
 d.parent[b]=a
 if d.rank[a]==d.rank[b]{d.rank[a]++}
}
func faceVertexIndex(token string,vertexCount int)(int,error){
 s:=strings.Split(token,"/")[0]
 v,e:=strconv.Atoi(s)
 if e!=nil||v==0||v>vertexCount||v < -vertexCount{return 0,errors.New("invalid OBJ vertex index")}
 if v<0{return vertexCount+v,nil}
 return v-1,nil
}
func scanTopology(reader io.Reader, maxBytes int64,element string)(MeshTopology,error){
 m:=MeshTopology{ElementID:element,Status:"UNKNOWN_TOPOLOGY"}
 src:=io.LimitReader(reader,maxBytes+1)
 digest:=sha256.New()
 scanner:=bufio.NewScanner(io.TeeReader(src,digest))
 scanner.Buffer(make([]byte,1024),1024*1024)
 edges:=map[Edge]int{}
 orientations:=map[Edge]int{}
 touched:=map[int]bool{}
 components:=newDSU(0)
 byteCount:=int64(0)
 for scanner.Scan(){
  raw:=scanner.Bytes()
  byteCount+=int64(len(raw))+1
  if byteCount>maxBytes{return m,errors.New("OBJ exceeds bounded source decompression")}
  v:=strings.Fields(string(raw))
  if len(v)==0{continue}
  switch v[0]{
  case "v":
   if len(v)<4{return m,errors.New("invalid vertex")}
   for i:=1;i<=3;i++{
    coord,e:=strconv.ParseFloat(v[i],64)
    if e!=nil||math.IsNaN(coord)||math.IsInf(coord,0){return m,errors.New("invalid/nonfinite original geometry")}
   }
   m.Vertices++
  case "f":
   if len(v)<4{return m,errors.New("degenerate source polygon")}
   ids:=make([]int,0,len(v)-1)
   seen:=map[int]bool{}
   for _,token:=range v[1:]{
    idx,e:=faceVertexIndex(token,m.Vertices)
    if e!=nil{return m,e}
    ids=append(ids,idx)
    if seen[idx]{m.DegenerateFaces++}
    seen[idx]=true;touched[idx]=true
   }
   for i:=0;i<len(ids);i++{
    a,b:=ids[i],ids[(i+1)%len(ids)]
    if a==b{m.DegenerateFaces++;continue}
    edge:=Edge{a,b};sign:=1
    if a>b{edge=Edge{b,a};sign=-1}
    edges[edge]++
    orientations[edge]+=sign
   }
   m.Faces++
  }
 }
 if e:=scanner.Err();e!=nil{return m,e}
 if m.Vertices<4||m.Faces<2{return m,errors.New("no usable original 3D component")}
 m.Edges=len(edges)
 for _,n:=range edges{
  if n==1{m.BoundaryEdges++}
  if n>2{m.NonmanifoldEdges++}
 }
 for edge,n:=range edges{
  if n==2&&orientations[edge]!=0{m.OrientedEdgeConflicts++}
 }
 components=newDSU(m.Vertices)
 for edge:=range edges{components.union(edge.A,edge.B)}
 cc:=map[int]bool{}
 for v:=range touched{cc[components.find(v)]=true}
 m.ConnectedVertexComponents=len(cc)
 m.IsolatedVertices=m.Vertices-len(touched)
 m.ClosedEdgePairing=m.BoundaryEdges==0&&m.NonmanifoldEdges==0&&
  m.OrientedEdgeConflicts==0&&m.DegenerateFaces==0&&m.IsolatedVertices==0
 if m.ClosedEdgePairing{m.Status="EDGE_PAIRED_CLOSEDNESS_CANDIDATE_NOT_VOLUME_TRUTH"}else{
  m.Status="HOLD_OPEN_NONMANIFOLD_OR_INCONSISTENT_ORIENTATION"
 }
 m.SourceSHA256=hex.EncodeToString(digest.Sum(nil))
 return m,nil
}
func intersect(a,b []Element)[]string{
 aa:=map[string]bool{}
 for _,x:=range a{aa[x.ID]=true}
 out:=[]string{}
 for _,x:=range b{if aa[x.ID]{out=append(out,x.ID)}}
 sort.Strings(out)
 return out
}
func inspectComposites(table,archive string)(CompositeReport,error){
 r:=CompositeReport{Schema:compositeSchema,Status:"SOURCE_COMPONENT_TOPOLOGY_NOT_ANATOMY_QUALIFIED",
  SourceCoordinateUnits:"UNKNOWN_UNTIL_DOCUMENTED",Groups:[]CompositeGroup{},Overlap:[]SharedAtoms{},
  Caveats:[]string{
   "Surface edge pair closure is insufficient to establish volumetric manifold, signed tissue volume or real organ anatomy",
   "Atomic source FJ mesh identity, FMA compound concept and BP source view representation ID are different entities",
   "Distinct compound organs may share FJ atomic components; do not assert mutually exclusive occupancy",
   "No physical unit, patient morph, source atlas reference frame or registered MPFB correspondence is admitted",
   "Human structure names, sexes and source atlas variants require separate semantic and rights review",
  }}
 var err error
 r.SourceTableSHA256,_,err=digestFile(table);if err!=nil{return r,err}
 r.SourceArchiveSHA256,_,err=digestFile(archive);if err!=nil{return r,err}
 if r.SourceTableSHA256!="3f5f6df1028eb122b30de77c711597b6bb8e5541658e5985859fd228adbf88ea"||
    r.SourceArchiveSHA256!="9fbc713fffeee924a5a657d9813d84d7eb957bded63adb854931dd5e3eb61c97"{
  return r,errors.New("SOURCE_VERSION_SHA_NOT_PINNED")
 }
 mapping,_,_,err:=readElements(table);if err!=nil{return r,err}
 z,e:=zip.OpenReader(archive);if e!=nil{return r,e};defer z.Close()
 byID:=map[string]*zip.File{}
 for _,f:=range z.File{
  if strings.Contains(f.Name,"..")||strings.Contains(f.Name,"\\")||strings.HasPrefix(f.Name,"/"){
   return r,errors.New("INVALID_ZIP_MEMBER_NAME")
  }
  name:=strings.TrimSuffix(strings.ToUpper(path.Base(f.Name)),".OBJ")
  if fj.MatchString(name){if byID[name]!=nil{return r,errors.New("DUPLICATE_ATOMIC_MESH")};byID[name]=f}
 }
 if len(byID)!=1258{return r,fmt.Errorf("expected exactly 1258 atomic source OBJ members, saw %d",len(byID))}
 picks:=[]Target{
  {ConceptID:"FMA7088",Name:"heart"},
  {ConceptID:"FMA7310",Name:"left lung"},
  {ConceptID:"FMA7309",Name:"right lung"},
  {ConceptID:"FMA13295",Name:"diaphragm"},
  {ConceptID:"FMA7197",Name:"liver"},
 }
 selected:=map[string]bool{}
 for _,t:=range picks{
  ids:=mapping[t.ConceptID]
  g:=CompositeGroup{ConceptID:t.ConceptID,Name:t.Name,AtomicElements:len(ids),Sampled:[]MeshTopology{}}
  for _,e:=range ids{
   if len(g.Sampled)>=2||r.Inspected>=10{break}
   if selected[e.ID]{continue}
   f:=byID[e.ID]
   if f==nil{continue}
   if f.UncompressedSize64>6*1024*1024{continue}
   handle,err:=f.Open();if err!=nil{return r,err}
   topo,scanErr:=scanTopology(handle,6*1024*1024,e.ID)
   closeErr:=handle.Close()
   if scanErr!=nil{return r,scanErr}
   if closeErr!=nil{return r,closeErr}
   selected[e.ID]=true
   g.Sampled=append(g.Sampled,topo)
   r.Inspected++
   if topo.ClosedEdgePairing{r.ClosedEdgePairingCandidates++}else{r.OpenOrNonmanifold++}
  }
  r.Groups=append(r.Groups,g)
 }
 for i,a:=range picks{
  for _,b:=range picks[i+1:]{
   shared:=intersect(mapping[a.ConceptID],mapping[b.ConceptID])
   if len(shared)==0{continue}
   item:=SharedAtoms{FirstConcept:a.ConceptID,SecondConcept:b.ConceptID,Shared:len(shared)}
   if len(shared)>5{item.Intersection=shared[:5]}else{item.Intersection=shared}
   r.Overlap=append(r.Overlap,item)
  }
 }
 if r.Inspected==0{return r,errors.New("NO_BOUNDED_SOURCE_TOPOLOGY_SAMPLES")}
 return r,nil
}
func emitTopology(table,archive string)error{
 r,e:=inspectComposites(table,archive)
 if e!=nil{return e}
 data,e:=json.Marshal(r);if e!=nil{return e}
 fmt.Println("R036_COMPOSITE_TOPOLOGY_RECEIPT",string(data))
 return nil
}
