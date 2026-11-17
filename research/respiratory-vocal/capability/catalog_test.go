package capability
import(
 "bytes"
 "encoding/json"
 "strings"
 "testing"
 "unicode/utf8"

 "github.com/SemperSupra/stable-character-pipeline/research/respiratory-vocal/behavior"
 "github.com/SemperSupra/stable-character-pipeline/research/respiratory-vocal/preview"
)
func TestExhaustiveTypedStatusAndThreeAudiences(t *testing.T){
 c,e:=Build();if e!=nil{t.Fatal(e)}
 if c.Schema!="respiratory.audience_capabilities.v0"||len(c.Audiences)!=3||len(c.Locales)!=3||len(c.Entries)!=18{
  t.Fatalf("invalid audience/source registry %+v",c)
 }
 if strings.Join(c.Locales,",")!="en,de,th"{t.Fatal("locale contract changed")}
 seen:=map[behavior.Action]bool{}
 previews:=0;contracts:=0;names:=map[string]bool{}
 for _,entry:=range c.Entries{
  if seen[entry.Action]{t.Fatalf("duplicated action %s",entry.Action)}
  seen[entry.Action]=true
  for _,title:=range []string{entry.Labels.EN,entry.Labels.DE,entry.Labels.TH}{
   if !utf8.ValidString(title)||strings.TrimSpace(title)==""{t.Fatal("missing or invalid EN/DE/TH label")}
  }
  if entry.CanMakePhysicalVoice||entry.CanClaimHumanAnatomy||entry.CanClaimBreathability{
   t.Fatalf("unsupported physical/medical capability advertised for %s",entry.Action)
  }
  switch entry.Mode{
  case Preview:
   previews++
   if len(entry.AvailableSyntheticScenarios)==0{t.Fatal("preview without actual source")}
   for _,n:=range entry.AvailableSyntheticScenarios{
    if names[n]{t.Fatalf("scenario %s advertised twice",n)}
    names[n]=true
    p,ok:=preview.Fixtures()[n]
    if !ok||p.Action!=entry.Action{t.Fatalf("scenario misbound: %s %s",n,entry.Action)}
   }
  case ContractOnly:
   contracts++
   if len(entry.AvailableSyntheticScenarios)!=0{t.Fatalf("unsupported action misleadingly audible: %s",entry.Action)}
  default:t.Fatalf("unsupported status %s",entry.Mode)
  }
 }
 if previews!=15||contracts!=3||len(names)!=17{
  t.Fatalf("wrong support matrix: previews=%d contract-only=%d cases=%d",previews,contracts,len(names))
 }
 for _,a:=range []behavior.Action{behavior.Sniff,behavior.Sigh,behavior.Gasp}{
  x,ok:=Find(c,a)
  if !ok||x.Mode!=ContractOnly{t.Fatalf("unimplemented %s incorrectly advertised as generated audio",a)}
 }
 for _,a:=range []behavior.Action{behavior.QuietBreath,behavior.Hum,behavior.FlutePlay,behavior.InflateBalloon,behavior.StrawSuction}{
  x,ok:=Find(c,a)
  if !ok||x.Mode!=Preview{t.Fatalf("implemented synthetic preview omitted %s",a)}
 }
 if _,ok:=Find(c,"unknown_action");ok{t.Fatal("unknown user capability accidentally enabled")}
}
func TestDeterministicJSONAndExplicitSafetyDisclaimers(t *testing.T){
 a,e:=Build();if e!=nil{t.Fatal(e)}
 b,e:=Build();if e!=nil{t.Fatal(e)}
 left,e:=json.Marshal(a);if e!=nil{t.Fatal(e)}
 right,e:=json.Marshal(b);if e!=nil{t.Fatal(e)}
 if !bytes.Equal(left,right){t.Fatal("source capability JSON was nondeterministic")}
 for _,phrase:=range []string{"source_original_synthetic_only","can_make_physical_human_voice","can_claim_breathability_or_medical_safety","available_synthetic_scenarios","human_including_assistive_technology","automation","agent"}{
  if !bytes.Contains(left,[]byte(phrase)){t.Fatalf("missing machine-readable contract %s",phrase)}
 }
}
