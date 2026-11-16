// Package anatomy implements a synthetic view-state contract. It does not model human physiology.
package anatomy

import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "math"
 "sort"
)

const Schema = "scp.anatomy.synthetic.v1"

var Systems = []string{"integumentary","skeletal","muscular","nervous","circulatory","respiratory","digestive","urinary","reproductive","lymphatic","endocrine","sensory"}
var Locales = []string{"en","de","th","la"}

type Structure struct {
 ID string `json:"id"`
 ParentID string `json:"parent_id,omitempty"`
 Systems []string `json:"systems"`
 Labels map[string]string `json:"labels"`
}
type Physics struct {
 TimeSeconds float64 `json:"time_seconds"`
 ForceNewtons map[string]float64 `json:"force_newtons"`
}
type View struct {
 Visible map[string]bool `json:"visible"`
 Opacity map[string]float64 `json:"opacity"`
}
type Scene struct {
 Schema string `json:"schema"`
 Units string `json:"units"`
 Revision string `json:"revision"`
 Structures []Structure `json:"structures"`
 Physics Physics `json:"physics"`
 View View `json:"view"`
}
type Result struct {
 Status string `json:"status"`
 Code string `json:"code"`
 Message string `json:"message"`
 Revision string `json:"revision"`
 PhysicsSHA256 string `json:"physics_sha256"`
 VisibleIDs []string `json:"visible_ids"`
}
func invalid(format string,a ...any) error {return fmt.Errorf("INVALID_SCENE: "+format,a...)}
func knownSystem(s string) bool {for _,x:=range Systems{if s==x{return true}};return false}
func Validate(s Scene) error {
 if s.Schema!=Schema{return invalid("schema mismatch")}
 if s.Units!="m"{return invalid("units must be m")}
 if s.Revision==""{return invalid("missing revision")}
 if len(s.Structures)==0{return invalid("missing structures")}
 ids:=make(map[string]Structure,len(s.Structures))
 for _,st:=range s.Structures {
  if st.ID==""{return invalid("empty structure ID")}
  if _,ok:=ids[st.ID];ok{return invalid("duplicate ID %s",st.ID)}
  ids[st.ID]=st
  if len(st.Systems)==0{return invalid("no systems for %s",st.ID)}
  seen:=map[string]bool{}
  for _,system:=range st.Systems{if !knownSystem(system){return invalid("unknown system %s",system)};if seen[system]{return invalid("duplicate system %s",system)};seen[system]=true}
  for _,locale:=range Locales{if st.Labels[locale]==""{return invalid("missing locale %s on %s",locale,st.ID)}}
 }
 roots:=0
 for _,st:=range s.Structures{
  if st.ParentID==""{roots++;continue}
  if st.ParentID==st.ID{return invalid("self parent %s",st.ID)}
  if _,ok:=ids[st.ParentID];!ok{return invalid("orphan parent %s",st.ID)}
 }
 if roots==0{return invalid("no root")}
 color:=map[string]uint8{}
 var visit func(string)error
 visit=func(id string)error{
  if color[id]==1{return invalid("cycle %s",id)}
  if color[id]==2{return nil}
  color[id]=1
  if p:=ids[id].ParentID;p!=""{if e:=visit(p);e!=nil{return e}}
  color[id]=2
  return nil
 }
 for id:=range ids{if e:=visit(id);e!=nil{return e}}
 if math.IsNaN(s.Physics.TimeSeconds)||math.IsInf(s.Physics.TimeSeconds,0)||s.Physics.TimeSeconds<0{return invalid("invalid time")}
 for id,v:=range s.Physics.ForceNewtons{if _,ok:=ids[id];!ok{return invalid("force on unknown %s",id)};if math.IsNaN(v)||math.IsInf(v,0){return invalid("nonfinite force %s",id)}}
 for id:=range s.View.Visible{if _,ok:=ids[id];!ok{return invalid("visibility on unknown %s",id)}}
 for id,v:=range s.View.Opacity{if _,ok:=ids[id];!ok{return invalid("opacity on unknown %s",id)};if math.IsNaN(v)||math.IsInf(v,0)||v<0||v>1{return invalid("invalid opacity %s",id)}}
 return nil
}
func PhysicsDigest(s Scene)(string,error){
 if err:=Validate(s);err!=nil{return "",err}
 // Do not include render visibility or opacity in the immutable simulation fingerprint.
 physical:=struct{Revision string `json:"revision"`;Structures []Structure `json:"structures"`;Physics Physics `json:"physics"`}{s.Revision,s.Structures,s.Physics}
 data,err:=json.Marshal(physical);if err!=nil{return "",err}
 digest:=sha256.Sum256(data);return hex.EncodeToString(digest[:]),nil
}
func VisibleIDs(s Scene)[]string{out:=[]string{};for _,st:=range s.Structures{if s.View.Visible[st.ID]{out=append(out,st.ID)}};sort.Strings(out);return out}
func SetSystemVisibility(s Scene,system string,visible bool)(Scene,Result,error){
 if err:=Validate(s);err!=nil{return s,Result{},err}
 if !knownSystem(system){return s,Result{},fmt.Errorf("UNKNOWN_SYSTEM: %s",system)}
 before,err:=PhysicsDigest(s);if err!=nil{return s,Result{},err}
 bytes,err:=json.Marshal(s);if err!=nil{return s,Result{},err}
 var out Scene;if err=json.Unmarshal(bytes,&out);err!=nil{return s,Result{},err}
 if out.View.Visible==nil{out.View.Visible=map[string]bool{}}
 for _,st:=range out.Structures{for _,member:=range st.Systems{if member==system{out.View.Visible[st.ID]=visible;break}}}
 after,err:=PhysicsDigest(out);if err!=nil{return s,Result{},err}
 if before!=after{return s,Result{},errors.New("PHYSICS_MUTATION")}
 return out,Result{Status:"PASS_NARROW",Code:"RENDER_ONLY",Message:"synthetic view state updated; no physical simulation executed",Revision:s.Revision,PhysicsSHA256:after,VisibleIDs:VisibleIDs(out)},nil
}
func SyntheticScene()Scene{
 mk:=func(id,parent,system,en,de,th,la string)Structure{return Structure{ID:id,ParentID:parent,Systems:[]string{system},Labels:map[string]string{"en":en,"de":de,"th":th,"la":la}}}
 elements:=[]Structure{
  mk("body","","integumentary","body","Körper","ร่างกาย","corpus"),
  mk("skin","body","integumentary","skin","Haut","ผิวหนัง","cutis"),
  mk("femur","body","skeletal","femur","Oberschenkelknochen","กระดูกต้นขา","femur"),
  mk("quadriceps","femur","muscular","quadriceps","Quadrizeps","กล้ามเนื้อต้นขาด้านหน้า","musculus quadriceps femoris"),
  mk("heart","body","circulatory","heart","Herz","หัวใจ","cor"),
  mk("lung","body","respiratory","lung","Lunge","ปอด","pulmo"),
  mk("liver","body","digestive","liver","Leber","ตับ","hepar"),
  mk("kidney","body","urinary","kidney","Niere","ไต","ren"),
  mk("brain","body","nervous","brain","Gehirn","สมอง","encephalon"),
  mk("eye","brain","sensory","eye","Auge","ตา","oculus"),
 }
 return Scene{Schema:Schema,Units:"m",Revision:"synthetic-1",Structures:elements,Physics:Physics{TimeSeconds:1,ForceNewtons:map[string]float64{"femur":42}},View:View{Visible:map[string]bool{"skin":true,"femur":true,"quadriceps":true,"heart":true},Opacity:map[string]float64{"skin":0.3}}}
}
