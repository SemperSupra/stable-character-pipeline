// Package capability provides a typed, truthful interface inventory for the
// same respiratory state used by humans, assistive technology, automation and
// agents. It is a feature declaration, NOT a real human vocal synthesizer.
package capability
import(
 "errors"
 "sort"

 "github.com/SemperSupra/stable-character-pipeline/research/respiratory-vocal/behavior"
 "github.com/SemperSupra/stable-character-pipeline/research/respiratory-vocal/preview"
)
type Mode string
const(
 Preview Mode="synthetic_preview_only"
 ContractOnly Mode="typed_contract_only"
)
type Labels struct{
 EN string `json:"en"`
 DE string `json:"de"`
 TH string `json:"th"`
}
type Entry struct{
 Action behavior.Action `json:"action"`
 Labels Labels `json:"labels"`
 Mode Mode `json:"mode"`
 AvailableSyntheticScenarios []string `json:"available_synthetic_scenarios"`
 CanMakePhysicalVoice bool `json:"can_make_physical_human_voice"`
 CanClaimHumanAnatomy bool `json:"can_claim_real_anatomy"`
 CanClaimBreathability bool `json:"can_claim_breathability_or_medical_safety"`
}
type Catalog struct{
 Schema string `json:"schema"`
 Validity string `json:"validity"`
 Audiences []string `json:"audiences"`
 Locales []string `json:"locales"`
 Entries []Entry `json:"entries"`
}
var displayNames=map[behavior.Action]Labels{
 behavior.QuietBreath:{"Quiet breathing","Ruhiges Atmen","หายใจเบา"},
 behavior.DeepBreath:{"Deep or heavy breathing","Tiefes oder schweres Atmen","หายใจลึกหรือแรง"},
 behavior.Pant:{"Panting","Hecheln","หายใจหอบ"},
 behavior.Sniff:{"Sniff","Schnüffeln","สูดจมูก"},
 behavior.Sigh:{"Sigh","Seufzen","ถอนหายใจ"},
 behavior.Gasp:{"Gasp","Nach Luft schnappen","สูดหายใจเฮือก"},
 behavior.Hum:{"Humming","Summen","ฮัมเพลง"},
 behavior.Sing:{"Singing","Singen","ร้องเพลง"},
 behavior.Cry:{"Crying or sobbing","Weinen oder Schluchzen","ร้องไห้หรือสะอื้น"},
 behavior.Laugh:{"Laughter","Lachen","หัวเราะ"},
 behavior.Scream:{"Scream","Schreien","กรีดร้อง"},
 behavior.LipWhistleAction:{"Whistling with lips","Mit den Lippen pfeifen","ผิวปาก"},
 behavior.Beatbox:{"Beatboxing","Beatboxing","บีตบ็อกซ์"},
 behavior.FlutePlay:{"Blowing across a flute","Flöte anblasen","เป่าขลุ่ย"},
 behavior.ReedPlay:{"Playing a reed instrument","Rohrblattinstrument spielen","เป่าเครื่องเป่าลิ้น"},
 behavior.BlowWhistle:{"Blowing a whistle","In eine Pfeife blasen","เป่านกหวีด"},
 behavior.InflateBalloon:{"Inflating a balloon","Luftballon aufblasen","เป่าลูกโป่ง"},
 behavior.StrawSuction:{"Sucking through a straw","Durch einen Strohhalm saugen","ดูดผ่านหลอด"},
}
// Declared source-state actions: any addition to behavior.Action must trigger
// an explicit catalog and test revision; no implied capability promotion.
var allActions=[]behavior.Action{
 behavior.QuietBreath,behavior.DeepBreath,behavior.Pant,behavior.Sniff,
 behavior.Sigh,behavior.Gasp,behavior.Hum,behavior.Sing,behavior.Cry,
 behavior.Laugh,behavior.Scream,behavior.LipWhistleAction,behavior.Beatbox,
 behavior.FlutePlay,behavior.ReedPlay,behavior.BlowWhistle,
 behavior.InflateBalloon,behavior.StrawSuction,
}
func Build()(Catalog,error){
 out:=Catalog{
  Schema:"respiratory.audience_capabilities.v0",
  Validity:"source_original_synthetic_only_no_real_anatomy_or_instrument",
  Audiences:[]string{"human_including_assistive_technology","automation","agent"},
  Locales:[]string{"en","de","th"},Entries:[]Entry{},
 }
 byAction:=map[behavior.Action][]string{}
 for name,perf:=range preview.Fixtures(){
  if err:=perf.Validate();err!=nil{return Catalog{},err}
  if _,known:=displayNames[perf.Action];!known{return Catalog{},errors.New("preview action absent from interface contract")}
  byAction[perf.Action]=append(byAction[perf.Action],name)
 }
 for _,a:=range allActions{
  labels,ok:=displayNames[a]
  if !ok||labels.EN==""||labels.DE==""||labels.TH==""{return Catalog{},errors.New("missing language label")}
  files:=append([]string{},byAction[a]...)
  sort.Strings(files)
  e:=Entry{Action:a,Labels:labels,Mode:ContractOnly,AvailableSyntheticScenarios:files}
  if len(files)>0{e.Mode=Preview}
  out.Entries=append(out.Entries,e)
 }
 return out,nil
}
func Find(c Catalog,a behavior.Action)(Entry,bool){
 for _,e:=range c.Entries{if e.Action==a{return e,true}}
 return Entry{},false
}
