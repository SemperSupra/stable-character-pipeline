// bp3d-elements qualifies element-ID-to-real-OBJ existence from the official 4.0 PART-OF archive.
// No object geometry, medical position, or clinical accuracy is admitted.
package main
import (
 "archive/zip"
 "bufio"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "io"
 "math"
 "os"
 "path"
 "regexp"
 "sort"
 "strconv"
 "strings"
)
const schema="scp.anatomy.bp3d.element_mesh_custody.v1"
type Target struct{ConceptID string `json:"concept_id"`;Name string `json:"name"`}
var targets=[]Target{
 {"FMA7088","heart"},{"FMA7310","left lung"},{"FMA7309","right lung"},
 {"FMA7163","skin"},{"FMA9611","femur"},{"FMA13295","diaphragm"},{"FMA7197","liver"},
}
type Element struct{ID string `json:"id"`;ConceptID string `json:"concept_id"`;SourceLabel string `json:"source_label"`}
type OBJResult struct {
 ElementID string `json:"element_id"`
 ConceptID string `json:"concept_id"`
 SourceLabel string `json:"source_label"`
 MemberName string `json:"member_name"`
 SHA256 string `json:"sha256"`
 UncompressedBytes uint64 `json:"uncompressed_bytes"`
 Vertices int `json:"vertices"`
 Faces int `json:"faces"`
 Bounds [6]float64 `json:"bounds_source_units"`
}
type TargetReport struct{
 ConceptID string `json:"concept_id"`
 TargetName string `json:"target_name"`
 SourceLabel string `json:"source_label"`
 ListedElementCount int `json:"listed_element_count"`
 ArchivePresentCount int `json:"archive_present_count"`
 SkippedOversizeParts int `json:"skipped_oversize_parts"`
 SampledOBJ []OBJResult `json:"sampled_obj"`
 Status string `json:"status"`
}
type Receipt struct{
 Schema string `json:"schema"`
 Status string `json:"status"`
 Release string `json:"release"`
 License string `json:"license"`
 OfficialURL string `json:"official_url"`
 TableSHA256 string `json:"table_sha256"`
 ArchiveSHA256 string `json:"archive_sha256"`
 ArchiveBytes int64 `json:"archive_bytes"`
 ArchiveMembers int `json:"archive_members"`
 ElementRows int `json:"element_rows"`
 UniqueListedElements int `json:"unique_listed_elements"`
 SelectedSamples int `json:"selected_samples"`
 SkippedOversizeParts int `json:"skipped_oversize_parts"`
 Rows []TargetReport `json:"rows"`
 Warnings []string `json:"warnings"`
}
var fj=regexp.MustCompile(`^FJ[0-9]+[A-Za-z0-9]*$`)
var fma=regexp.MustCompile(`^FMA[0-9]+$`)
func digestFile(file string)(string,int64,error){
 f,e:=os.Open(file);if e!=nil{return "",0,e};defer f.Close()
 h:=sha256.New();n,e:=io.Copy(h,f)
 return hex.EncodeToString(h.Sum(nil)),n,e
}
func readElements(file string)(map[string][]Element,int,int,error){
 f,e:=os.Open(file);if e!=nil{return nil,0,0,e};defer f.Close()
 sc:=bufio.NewScanner(f);sc.Buffer(make([]byte,1024),2*1024*1024)
 entries:=map[string][]Element{};seen:=map[string]bool{};line:=0;rows:=0
 for sc.Scan(){
  line++
  cols:=strings.Split(strings.TrimSuffix(sc.Text(),"\r"),"\t")
  if line==1{if strings.Join(cols,"|")!="concept id|name|element file id"{return nil,0,0,fmt.Errorf("unexpected official element TSV header")};continue}
  if len(cols)!=3||!fma.MatchString(cols[0])||strings.TrimSpace(cols[1])==""||!fj.MatchString(cols[2]){
   return nil,0,0,fmt.Errorf("invalid concept/name/element row %d",line)
  }
  key:=cols[0]+"|"+cols[2]
  if seen[key]{return nil,0,0,fmt.Errorf("repeated concept/element edge on line %d",line)}
  seen[key]=true
  entries[cols[0]]=append(entries[cols[0]],Element{ID:cols[2],ConceptID:cols[0],SourceLabel:cols[1]})
  rows++
 }
 if e=sc.Err();e!=nil{return nil,0,0,e}
 if rows==0{return nil,0,0,errors.New("missing element data")}
 all:=map[string]bool{}
 for k:=range entries{sort.Slice(entries[k],func(i,j int)bool{return entries[k][i].ID<entries[k][j].ID});for _,v:=range entries[k]{all[v.ID]=true}}
 return entries,rows,len(all),nil
}
func parseOBJ(reader io.Reader,maxBytes int64)(int,int,[6]float64,string,error){
 bounds:=[6]float64{math.Inf(1),math.Inf(1),math.Inf(1),math.Inf(-1),math.Inf(-1),math.Inf(-1)}
 h:=sha256.New()
 stream:=io.TeeReader(io.LimitReader(reader,maxBytes+1),h)
 sc:=bufio.NewScanner(stream);sc.Buffer(make([]byte,1024),1024*1024)
 vertices,faces,total:=0,0,int64(0)
 for sc.Scan(){
  raw:=sc.Bytes();total+=int64(len(raw))+1
  if total>maxBytes{return 0,0,bounds,"",errors.New("OBJ uncompressed byte cap exceeded")}
  v:=strings.Fields(string(raw))
  if len(v)==0{continue}
  switch v[0]{
  case "v":
   if len(v)<4{return 0,0,bounds,"",errors.New("OBJ malformed vertex")}
   var xyz [3]float64
   for i:=0;i<3;i++{x,e:=strconv.ParseFloat(v[i+1],64);if e!=nil||math.IsInf(x,0)||math.IsNaN(x){return 0,0,bounds,"",errors.New("OBJ non-finite vertex")};xyz[i]=x}
   for i:=0;i<3;i++{if xyz[i]<bounds[i]{bounds[i]=xyz[i]};if xyz[i]>bounds[i+3]{bounds[i+3]=xyz[i]}}
   vertices++
  case "f":
   if len(v)<4{return 0,0,bounds,"",errors.New("OBJ degenerate face")}
   for _,token:=range v[1:]{
    indexStr:=strings.Split(token,"/")[0]
    index,e:=strconv.Atoi(indexStr)
    if e!=nil||index==0||index>vertices||index < -vertices{return 0,0,bounds,"",errors.New("OBJ invalid face index")}
   }
   faces++
  }
 }
 if e:=sc.Err();e!=nil{return 0,0,bounds,"",e}
 if vertices<4||faces<2{return 0,0,bounds,"",errors.New("OBJ no usable mesh")}
 return vertices,faces,bounds,hex.EncodeToString(h.Sum(nil)),nil
}
func inspect(table,archive string)(Receipt,error){
 r:=Receipt{Schema:schema,Status:"HOLD_NO_QUALIFIED_SOURCE_MESH_SAMPLE",Release:"BodyParts3D 4.0 99%-reduced PART-OF",
  License:"CC BY 4.0; BodyParts3D, © The Database Center for Life Science licensed under CC Attribution 4.0 International",
  OfficialURL:"https://dbarchive.biosciencedbc.jp/data/bodyparts3d/20130619/partof_BP3D_4.0_obj_99.zip",
  Rows:[]TargetReport{},Warnings:[]string{
   "Only ATOMIC ELEMENT OBJ files have meshes; compound FMA concepts map to lists of FJ elements",
   "A concept-to-FJ edge or OBJ existence does not prove medical correctness, organ completeness, source coordinate units or character registration",
   "Samples are 99%-polygon-reduced reference surfaces; not physical volumetric tissue meshes",
   "The source 2013 data release and 2025 licensing page must be retained in a per-artifact rights manifest",
  }}
 var e error
 r.TableSHA256,_,e=digestFile(table);if e!=nil{return r,e}
 r.ArchiveSHA256,r.ArchiveBytes,e=digestFile(archive);if e!=nil{return r,e}
 if r.ArchiveBytes<1000000||r.ArchiveBytes>80000000{return r,errors.New("archive bounds outside preflight")}
 elems,rowCount,uniques,e:=readElements(table);if e!=nil{return r,e}
 r.ElementRows=rowCount;r.UniqueListedElements=uniques
 zh,e:=zip.OpenReader(archive);if e!=nil{return r,e};defer zh.Close()
 r.ArchiveMembers=len(zh.File)
 if r.ArchiveMembers==0||r.ArchiveMembers>10000{return r,errors.New("unexpected zip member count")}
 members:=map[string]*zip.File{}
 for _,m:=range zh.File{
  if m.FileInfo().IsDir(){continue}
  if m.Flags&0x1!=0{return r,errors.New("encrypted zip member")}
  if strings.Contains(m.Name,"\\")||strings.Contains(m.Name,"../")||strings.HasPrefix(m.Name,"/")||path.Clean(m.Name)!=m.Name{return r,errors.New("unsafe zip filename")}
  if !strings.HasSuffix(strings.ToLower(m.Name),".obj"){continue}
  id:=strings.TrimSuffix(strings.ToUpper(path.Base(m.Name)),".OBJ")
  if !fj.MatchString(id){continue}
  if old:=members[id];old!=nil{return r,errors.New("duplicate FJ element in same archive")}
  members[id]=m
 }
 if len(members)==0{return r,errors.New("no FJ OBJ files in original official archive")}
 totalSamples:=0
 for _,target:=range targets{
  known:=elems[target.ConceptID]
  row:=TargetReport{ConceptID:target.ConceptID,TargetName:target.Name,
   ListedElementCount:len(known),Status:"UNKNOWN_NO_ELEMENT_OR_ARCHIVE",
   SampledOBJ:[]OBJResult{}}
  maxSamples:=2
  for _,v:=range known{
   if row.SourceLabel==""{row.SourceLabel=v.SourceLabel}
   member:=members[v.ID]
   if member==nil{continue}
   row.ArchivePresentCount++
   if len(row.SampledOBJ)>=maxSamples||totalSamples>=12{continue}
   if member.UncompressedSize64>6*1024*1024{
    row.SkippedOversizeParts++;r.SkippedOversizeParts++
    continue
   }
   reader,e:=member.Open();if e!=nil{return r,e}
   verts,faces,bounds,digest,parseErr:=parseOBJ(reader,6*1024*1024)
   closeErr:=reader.Close()
   if parseErr!=nil{return r,fmt.Errorf("%s: %w",v.ID,parseErr)}
   if closeErr!=nil{return r,closeErr}
   row.SampledOBJ=append(row.SampledOBJ,OBJResult{ElementID:v.ID,ConceptID:v.ConceptID,
    SourceLabel:v.SourceLabel,MemberName:member.Name,SHA256:digest,
    UncompressedBytes:member.UncompressedSize64,Vertices:verts,Faces:faces,Bounds:bounds})
   totalSamples++
  }
  if len(row.SampledOBJ)>0{
   row.Status="SOURCE_ELEMENT_ARCHIVE_PRESENT_NOT_ANATOMY_QUALIFIED"
  }else if row.ArchivePresentCount>0{
   row.Status="HOLD_PRESENT_BUT_NO_BOUNDED_MESH_SAMPLE"
  }else if len(known)>0{
   row.Status="HOLD_ELEMENT_REFERENCES_NOT_FOUND_IN_ARCHIVE"
  }
  r.Rows=append(r.Rows,row)
 }
 r.SelectedSamples=totalSamples
 if totalSamples>0{r.Status="SOURCE_ELEMENT_MESH_BYTES_INSPECTED_NOT_ANATOMY_QUALIFIED"}
 return r,nil
}
func main(){
 table:=flag.String("elements","","official partof_element_parts.txt in scratch")
 archive:=flag.String("archive","","official partof_BP3D_4.0_obj_99.zip in scratch")
 flag.Parse()
 if *table==""||*archive==""{fmt.Fprintln(os.Stderr,"R036_ELEMENT_FAIL missing source paths");os.Exit(2)}
 r,e:=inspect(*table,*archive)
 if e!=nil{fmt.Fprintln(os.Stderr,"R036_ELEMENT_FAIL",e);os.Exit(3)}
 jsonBytes,e:=json.Marshal(r);if e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(3)}
 fmt.Println("R036_ELEMENT_RECEIPT",string(jsonBytes))
 if r.Status!="SOURCE_ELEMENT_MESH_BYTES_INSPECTED_NOT_ANATOMY_QUALIFIED"{os.Exit(4)}
}
