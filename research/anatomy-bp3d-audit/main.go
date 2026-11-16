// R036 BodyParts3D 4.0 source-only metadata and ontology graph audit.
// This does not import geometry, qualify anatomy, or claim every named concept
// has a usable independent mesh. stdlib only, no runtime network accesses.
package main

import (
 "bufio"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "io"
 "os"
 "regexp"
 "sort"
 "strings"
)

type Source struct {
 Kind string `json:"kind"`
 File string `json:"file"`
 SHA256 string `json:"sha256"`
 Rows int `json:"rows"`
}
type Item struct {Concept string; Representation string; Name string}
type Relation struct {Parent string; Child string}
type Table struct {
 Sources []Source `json:"sources"`
 IsA map[string]Item `json:"-"`
 PartOf map[string]Item `json:"-"`
 IsaEdges []Relation `json:"-"`
 PartEdges []Relation `json:"-"`
}
type Report struct {
 Schema string `json:"schema"`
 Status string `json:"status"`
 Sources []Source `json:"sources"`
 ISARows int `json:"isa_rows"`
 PartOfRows int `json:"part_of_rows"`
 ISAUniqueConcepts int `json:"isa_unique_concepts"`
 PartOfUniqueConcepts int `json:"part_of_unique_concepts"`
 SharedConcepts int `json:"shared_concepts"`
 ISAUniqueRepresentations int `json:"isa_unique_representations"`
 PartOfUniqueRepresentations int `json:"part_of_unique_representations"`
 DifferentRepresentationForSharedConcept int `json:"different_representation_for_shared_concept"`
 DifferentNameForSharedConcept int `json:"different_name_for_shared_concept"`
 ISARelationEdges int `json:"isa_relation_edges"`
 PartOfRelationEdges int `json:"part_of_relation_edges"`
 ISARelationNodesWithoutGeometryMap int `json:"isa_relation_nodes_without_geometry_map"`
 PartOfRelationNodesWithoutGeometryMap int `json:"part_of_relation_nodes_without_geometry_map"`
 ISACycles int `json:"isa_cycles"`
 PartOfCycles int `json:"part_of_cycles"`
 ImportantSourceConcepts map[string][]string `json:"important_source_concepts"`
 Caveats []string `json:"caveats"`
}
var fma=regexp.MustCompile(`^FMA[0-9]+$`)
var bp=regexp.MustCompile(`^BP[0-9]+$`)
func hash(path string)(string,error){
 f,e:=os.Open(path);if e!=nil{return "",e};defer f.Close()
 h:=sha256.New();_,e=io.Copy(h,f)
 return hex.EncodeToString(h.Sum(nil)),e
}
func readRows(path string,width int,cb func([]string)error)(int,error){
 f,e:=os.Open(path);if e!=nil{return 0,e};defer f.Close()
 sc:=bufio.NewScanner(f);sc.Buffer(make([]byte,1024),2*1024*1024)
 count:=0;line:=0
 for sc.Scan(){
  line++
  v:=strings.Split(strings.TrimSuffix(sc.Text(),"\r"),"\t")
  if line==1{
   if width==3 && strings.Join(v,"|")!="concept id|representation id|en"{return 0,fmt.Errorf("%s: unexpected source header %q",path,sc.Text())}
   if width==4 && strings.Join(v,"|")!="parent id|parent name|child id|child name"{return 0,fmt.Errorf("%s: unexpected source header %q",path,sc.Text())}
   continue
  }
  if len(v)!=width{return 0,fmt.Errorf("%s:%d expected %d TSV columns, got %d",path,line,width,len(v))}
  if e=cb(v);e!=nil{return 0,fmt.Errorf("%s:%d: %w",path,line,e)}
  count++
 }
 if e=sc.Err();e!=nil{return 0,e}
 if line==0||count==0{return 0,fmt.Errorf("%s: empty source table",path)}
 return count,nil
}
func parseItems(path string)(map[string]Item,int,error){
 items:=make(map[string]Item)
 n,err:=readRows(path,3,func(v []string)error{
  if !fma.MatchString(v[0])||!bp.MatchString(v[1])||strings.TrimSpace(v[2])==""{
   return fmt.Errorf("invalid concept, representation or name")
  }
  item:=Item{v[0],v[1],v[2]}
  if old,exists:=items[v[0]];exists && old!=item{
   return fmt.Errorf("conflicting concept duplicate %s",v[0])
  }
  items[v[0]]=item
  return nil
 })
 return items,n,err
}
func parseEdges(path string)([]Relation,int,error){
 edges:=[]Relation{}
 seen:=make(map[string]bool)
 n,err:=readRows(path,4,func(v []string)error{
  if !fma.MatchString(v[0])||!fma.MatchString(v[2])||v[0]==v[2]||
    strings.TrimSpace(v[1])==""||strings.TrimSpace(v[3])==""{
   return errors.New("invalid parent/child edge")
  }
  id:=v[0]+":"+v[2]
  if seen[id]{return fmt.Errorf("duplicate edge %s",id)}
  seen[id]=true
  edges=append(edges,Relation{v[0],v[2]})
  return nil
 })
 return edges,n,err
}
func graphMetrics(items map[string]Item,relations []Relation)(int,int){
 nodes:=map[string]bool{};edges:=map[string][]string{}
 for _,r:=range relations{
  nodes[r.Parent]=true;nodes[r.Child]=true
  edges[r.Parent]=append(edges[r.Parent],r.Child)
 }
 for k:=range edges{sort.Strings(edges[k])}
 orphan:=0
 for k:=range nodes{if _,ok:=items[k];!ok{orphan++}}
 // Back edges in a DFS identify source relation cycles. Do not flatten the
 // ISA and PART-OF DAGs; different relation semantics must remain distinct.
 state:=map[string]byte{}
 cycles:=0
 var visit func(string)
 visit=func(node string){
  state[node]=1
  for _,c:=range edges[node]{
   if state[c]==1{cycles++}else if state[c]==0{visit(c)}
  }
  state[node]=2
 }
 ids:=make([]string,0,len(nodes))
 for k:=range nodes{ids=append(ids,k)}
 sort.Strings(ids)
 for _,k:=range ids{if state[k]==0{visit(k)}}
 return orphan,cycles
}
func uniqueReps(items map[string]Item)int{
 ids:=map[string]bool{}
 for _,v:=range items{ids[v.Representation]=true}
 return len(ids)
}
var anchorNames=[]string{
 "skin","femur","tibia","rib","sternum","diaphragm","heart",
 "left lung","right lung","lung","trachea","esophagus","liver",
 "kidney","brain","spinal cord","larynx","tongue","eye","uterus","prostate",
}
func anchors(isa,part map[string]Item)map[string][]string{
 lookup:=map[string][]string{}
 for _,name:=range anchorNames{
  ids:=map[string]bool{}
  for _,items:=range []map[string]Item{isa,part}{
   for k,v:=range items{if strings.EqualFold(v.Name,name){ids[k]=true}}
  }
  out:=[]string{}
  for k:=range ids{out=append(out,k)}
  sort.Strings(out);lookup[name]=out
 }
 return lookup
}
func audit(paths []string)(Report,error){
 r:=Report{Schema:"scp.r036.bp3d.metadata-v1",
  Status:"SOURCE_METADATA_INSPECTED_NOT_GEOMETRY_QUALIFIED",
  ImportantSourceConcepts:map[string][]string{},
  Caveats:[]string{"FMA concept != distinct mesh; no 3D OBJ admitted or evaluated",
   "ISA subclass relations and PART-OF containment must not be conflated",
   "Reference anatomy is not an MPFB skeleton/mesh, physics or registered subject",
   "Incomplete and absent source relationships are observed, not silently invented",
   "Some systems and phenotype variants may be absent from both source tables"}}
 if len(paths)!=4{return r,errors.New("require exactly four official source TSV paths")}
 for _,path:=range paths{
  h,e:=hash(path);if e!=nil{return r,e}
  r.Sources=append(r.Sources,Source{File:strings.TrimPrefix(path,"./"),SHA256:h})
 }
 a,n,e:=parseItems(paths[0]);if e!=nil{return r,e}
 r.ISARows=n;r.Sources[0].Rows=n;r.Sources[0].Kind="isa_parts"
 b,n,e:=parseItems(paths[1]);if e!=nil{return r,e}
 r.PartOfRows=n;r.Sources[1].Rows=n;r.Sources[1].Kind="partof_parts"
 i,n,e:=parseEdges(paths[2]);if e!=nil{return r,e}
 r.ISARelationEdges=n;r.Sources[2].Rows=n;r.Sources[2].Kind="isa_relations"
 p,n,e:=parseEdges(paths[3]);if e!=nil{return r,e}
 r.PartOfRelationEdges=n;r.Sources[3].Rows=n;r.Sources[3].Kind="partof_relations"
 r.ISAUniqueConcepts=len(a);r.PartOfUniqueConcepts=len(b)
 r.ISAUniqueRepresentations=uniqueReps(a);r.PartOfUniqueRepresentations=uniqueReps(b)
 for k,av:=range a{if bv,ok:=b[k];ok{
  r.SharedConcepts++
  if av.Representation!=bv.Representation{r.DifferentRepresentationForSharedConcept++}
  if av.Name!=bv.Name{r.DifferentNameForSharedConcept++}
 }}
 r.ISARelationNodesWithoutGeometryMap,r.ISACycles=graphMetrics(a,i)
 r.PartOfRelationNodesWithoutGeometryMap,r.PartOfCycles=graphMetrics(b,p)
 r.ImportantSourceConcepts=anchors(a,b)
 if r.ISACycles>0||r.PartOfCycles>0{r.Status="HOLD_SOURCE_ONTOLOGY_CYCLES"}
 return r,nil
}
func main(){
 d:=flag.String("dir",".","directory with only 4 source TSVs")
 flag.Parse()
 names:=[]string{"isa_parts_list_e.txt","partof_parts_list_e.txt","isa_inclusion_relation_list.txt","partof_inclusion_relation_list.txt"}
 paths:=[]string{}
 for _,name:=range names{paths=append(paths,*d+"/"+name)}
 r,e:=audit(paths)
 if e!=nil{fmt.Fprintln(os.Stderr,"R036_BP3D_FAIL",e);os.Exit(2)}
 output,e:=json.Marshal(r);if e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(2)}
 fmt.Println("R036_BP3D_RECEIPT",string(output))
 if r.Status!="SOURCE_METADATA_INSPECTED_NOT_GEOMETRY_QUALIFIED"{os.Exit(3)}
}
