// Package asfamc performs a deliberately bounded metadata-only Acclaim ASF/AMC
// qualification. It does not produce forward-kinematic 3D poses or admit rights.
package asfamc

import (
 "bufio"
 "bytes"
 "crypto/sha256"
 "encoding/hex"
 "errors"
 "fmt"
 "math"
 "strconv"
 "strings"
 "unicode"
)

const MaxBytes=1<<20
const Marker="# SCP_ORIGINAL_SYNTHETIC_FIXTURE_V1"

type Bone struct {
 ID int `json:"id"`
 Name string `json:"name"`
 DOF []string `json:"dof"`
 Parent string `json:"parent"`
 LengthSource float64 `json:"length_source"`
}
type Skeleton struct {
 LengthUnit float64 `json:"asf_length_header"`
 Angle string `json:"angle"`
 RootOrder []string `json:"root_order"`
 Bones []Bone `json:"bones"`
}
type Frame struct {
 Number int `json:"number"`
 RootMeters []float64 `json:"root_meters"`
 ObservedChannels int `json:"observed_channels"`
}
type Receipt struct {
 Schema string `json:"schema"`
 Status string `json:"status"`
 Scope string `json:"scope"`
 ASFSHA256 string `json:"asf_sha256"`
 AMCSHA256 string `json:"amc_sha256"`
 SourceID string `json:"source_id"`
 CaptureGroup string `json:"capture_group"`
 Admission string `json:"admission"`
 NativeFrameRate string `json:"native_frame_rate"`
 ObservedTimestamp bool `json:"observed_timestamp"`
 ObservedGroundContact bool `json:"observed_ground_contact"`
 FKConverted bool `json:"fk_converted"`
 ScaleMetersPerSource float64 `json:"cmu_documented_meters_per_source_unit"`
 Skeleton Skeleton `json:"skeleton"`
 Frames []Frame `json:"frames"`
 Unknown []string `json:"unknown"`
}
func digest(b []byte)string{h:=sha256.Sum256(b);return hex.EncodeToString(h[:])}
func lines(raw []byte)([][]string,error){
 if len(raw)==0||len(raw)>MaxBytes||!bytes.Contains(raw,[]byte(Marker)){return nil,errors.New("NOT_ADMITTED: input must be bounded original synthetic fixture")}
 s:=bufio.NewScanner(bytes.NewReader(raw))
 s.Buffer(make([]byte,4096),MaxBytes)
 result:=[][]string{}
 for s.Scan(){
  line:=strings.TrimSpace(s.Text())
  if at:=strings.IndexByte(line,'#');at>=0{line=strings.TrimSpace(line[:at])}
  if line=="" {continue}
  result=append(result,strings.Fields(line))
  if len(result)>10000{return nil,errors.New("too many lines")}
 }
 return result,s.Err()
}
func finiteNumber(raw string)(float64,error){
 v,err:=strconv.ParseFloat(raw,64)
 if err!=nil||math.IsNaN(v)||math.IsInf(v,0){return 0,fmt.Errorf("nonfinite or invalid numeric channel %q",raw)}
 return v,nil
}
func channel(c string)bool{
 switch strings.ToLower(c){
 case "tx","ty","tz","rx","ry","rz":return true
 };return false
}
func order(tokens []string)([]string,error){
 if len(tokens)==0||len(tokens)>6{return nil,errors.New("invalid root/DOF channel count")}
 seen:=map[string]bool{}
 out:=[]string{}
 for _,c:=range tokens{
  c=strings.ToLower(c)
  if !channel(c)||seen[c]{return nil,errors.New("unknown or duplicated channel "+c)}
  seen[c]=true;out=append(out,c)
 }
 return out,nil
}
func ParseASF(raw []byte)(Skeleton,error){
 var out Skeleton
 rows,err:=lines(raw);if err!=nil{return out,err}
 section:="";block:=""; current:=Bone{};hasLength:=false;hasAngle:=false;nameSeen:=map[string]bool{"root":true};ids:=map[int]bool{};edges:=map[string]string{};hasHierarchy:=false;hasRoot:=false
 for _,tokens:=range rows {
  h:=strings.ToLower(tokens[0])
  if strings.HasPrefix(h,":"){section=h;block="";continue}
  switch section {
  case ":units":
   if len(tokens)!=2 {continue}
   if h=="length"{out.LengthUnit,err=finiteNumber(tokens[1]);if err!=nil{return out,err};hasLength=true}
   if h=="angle"{out.Angle=strings.ToLower(tokens[1]);hasAngle=true}
  case ":root":
   if h=="order" {out.RootOrder,err=order(tokens[1:]);if err!=nil{return out,err};hasRoot=true}
  case ":bonedata":
   if h=="begin" {if block!=""{return out,errors.New("nested bone block")};block="bone";current=Bone{DOF:[]string{}};continue}
   if h=="end"{
    if block!="bone"||current.ID<1||current.Name==""||current.LengthSource<=0||nameSeen[current.Name]||ids[current.ID]{return out,errors.New("invalid duplicate or incomplete bone")}
    nameSeen[current.Name]=true;ids[current.ID]=true
    out.Bones=append(out.Bones,current);block="";continue
   }
   if block!="bone"{continue}
   if h=="id" && len(tokens)==2{current.ID,err=strconv.Atoi(tokens[1]);if err!=nil{return out,err}}
   if h=="name" && len(tokens)==2{current.Name=tokens[1]}
   if h=="length" && len(tokens)==2{current.LengthSource,err=finiteNumber(tokens[1]);if err!=nil{return out,err}}
   if h=="dof"{current.DOF,err=order(tokens[1:]);if err!=nil{return out,err}}
  case ":hierarchy":
   if h=="begin" {if block!=""{return out,errors.New("nested hierarchy")};block="hierarchy";hasHierarchy=true;continue}
   if h=="end" {if block!="hierarchy"{return out,errors.New("unbalanced hierarchy")};block="";continue}
   if block!="hierarchy" || len(tokens)<2{continue}
   parent:=tokens[0]
   for _,child:=range tokens[1:] {
    if child=="root"||edges[child]!=""{return out,errors.New("duplicate parent or invalid root child")}
    edges[child]=parent
   }
  }
 }
 if block!=""||!hasLength||!hasAngle||!hasRoot||!hasHierarchy||out.LengthUnit!=.45||out.Angle!="deg"||
 len(out.RootOrder)!=6||len(out.Bones)<1{return out,errors.New("unsupported/ambiguous ASF header, root order or section")}
 // CMU official header 0.45 must be observed; absolute physical
 // conversion is CMU documented, not a general ASF license or oracle.
 for _,b:=range out.Bones {
  p:=edges[b.Name];if p=="" || !nameSeen[p]{return out,fmt.Errorf("bone %q missing/invalid parent",b.Name)}
  walked:=map[string]bool{b.Name:true};for p!="root" {
   if walked[p]||!nameSeen[p]{return out,errors.New("cyclic or dangling hierarchy")}
   walked[p]=true;p=edges[p]
   if p==""{return out,errors.New("unrooted chain")}
  }
 }
 for i:=range out.Bones{out.Bones[i].Parent=edges[out.Bones[i].Name]}
 return out,nil
}
func ParseAMC(raw []byte,s Skeleton)([]Frame,error){
 rows,err:=lines(raw);if err!=nil{return nil,err}
 rootCount:=len(s.RootOrder);joints:=map[string]int{"root":rootCount}; for _,b:=range s.Bones{if len(b.DOF)>0{joints[b.Name]=len(b.DOF)}}
 var out []Frame
 frame:=Frame{}
 seen:=map[string]bool{}
 active:=false
 // Source frame number starts at 1 for these bounded original fixtures;
 // no invented source timebase/fps (AMC has no intrinsic fps).
 finish:=func()error{
  if !active{return nil}
  for k:=range joints{if !seen[k]{return fmt.Errorf("missing fully specified frame %d bone %q",frame.Number,k)}}
  out=append(out,frame);return nil
 }
 header:=false
 for _,tokens:=range rows {
  if strings.HasPrefix(tokens[0],":"){
   if tokens[0]==":degrees"{header=true}
   if tokens[0]!=":fully-specified"&&tokens[0]!=":degrees"{return nil,errors.New("unsupported AMC header")}
   continue
  }
  if len(tokens)==1{
   n,e:=strconv.Atoi(tokens[0]);if e!=nil {return nil,errors.New("unexpected AMC singleton")}
   if !header{return nil,errors.New("missing explicit degrees header")}
   if err:=finish();err!=nil{return nil,err}
   if n<1||(active&&n!=frame.Number+1){return nil,errors.New("nonmonotonic or omitted source frame")}
   frame=Frame{Number:n,RootMeters:[]float64{},ObservedChannels:0}
   seen=map[string]bool{};active=true;continue
  }
  if !active{return nil,errors.New("frame data without frame number")}
  name:=tokens[0]
  count,ok:=joints[name];if !ok||seen[name]||len(tokens)!=count+1{return nil,fmt.Errorf("unknown, duplicate or mis-sized AMC channel %q",name)}
  vals:=make([]float64,count)
  for i,z:=range tokens[1:] {vals[i],err=finiteNumber(z);if err!=nil{return nil,err}}
  if name=="root"{
   frame.RootMeters=make([]float64,3);ntrans:=0
   for i,c:=range s.RootOrder{if c=="tx"||c=="ty"||c=="tz" {
    idx:=map[string]int{"tx":0,"ty":1,"tz":2}[c]
    frame.RootMeters[idx]=vals[i]*((1/.45)*.0254);ntrans++
   }}
   if ntrans!=3{return nil,errors.New("unsupported root translations")}
  }
  frame.ObservedChannels+=len(vals);seen[name]=true
 }
 if err:=finish();err!=nil{return nil,err}
 if len(out)==0{return nil,errors.New("no AMC frames")}
 return out,nil
}
func Qualify(asf,amc []byte,sourceID,captureGroup string)(Receipt,error){
 var empty Receipt
 if sourceID==""||captureGroup==""||
  strings.IndexFunc(sourceID,unicode.IsSpace)>=0||
  strings.IndexFunc(captureGroup,unicode.IsSpace)>=0 {
  return empty,errors.New("missing/ambiguous source id or family group")
 }
 sk,err:=ParseASF(asf);if err!=nil{return empty,err}
 fr,err:=ParseAMC(amc,sk);if err!=nil{return empty,err}
 return Receipt{
  Schema:"scp.motion.asfamc.synthetic-metadata.v1",
  Status:"PASS_SYNTHETIC_STRUCTURE_ONLY",
  Scope:"original synthetic ASF/AMC source-unit/root channels only; no FK, contact, real source, actual FPS, or rights grant",
  ASFSHA256:digest(asf),AMCSHA256:digest(amc),
  SourceID:sourceID,CaptureGroup:captureGroup,Admission:"NOT_ADMITTED",
  NativeFrameRate:"UNKNOWN",ObservedTimestamp:false,ObservedGroundContact:false,FKConverted:false,
  ScaleMetersPerSource:(1/.45)*.0254,Skeleton:sk,Frames:fr,
  Unknown:[]string{"native_fps","world_axis_handedness","joint_fk_3d","ground_contact","physical_ground_plane","rights_for_any_external_capture"},
 },nil
}
type Record struct {
 ID string `json:"id"`
 Group string `json:"capture_group"`
 Split string `json:"split"`
 Family string `json:"derivative_family"`
}
func CheckSplit(records []Record)error{
 seenIDs:=map[string]bool{}; groups:=map[string]string{}; families:=map[string]string{}
 for _,r:=range records{
  if r.ID==""||r.Group==""||r.Family==""||seenIDs[r.ID]{return errors.New("missing/duplicated capture id, group, or ancestry")}
  seenIDs[r.ID]=true
  if r.Split!="train"&&r.Split!="validation"&&r.Split!="test"{return errors.New("unknown split")}
  if v,ok:=groups[r.Group];ok&&v!=r.Split{return fmt.Errorf("capture group %s leaked across splits",r.Group)}
  if v,ok:=families[r.Family];ok&&v!=r.Split{return fmt.Errorf("derivative family %s leaked across splits",r.Family)}
  groups[r.Group]=r.Split;families[r.Family]=r.Split
 }
 if len(records)<1{return errors.New("missing records")}
 return nil
}
