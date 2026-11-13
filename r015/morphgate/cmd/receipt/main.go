package main
import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "fmt"
 "os"
 "strings"
 gate "github.com/SemperSupra/stable-character-pipeline/r015/morphgate"
)
func main(){
 const schema="r015.typed_morphology_consumer_candidate.v1"
 src,macro:=strings.Repeat("a",64),strings.Repeat("b",64)
 spec:=gate.Evidence{Schema:schema,SourceSceneSHA256:src,MacroConfigSHA256:macro,
  ShapePreset:"female",SourceMacroValue:0,MatureAdultAssetDesign:true,
  NativeUnit:"BLENDER_SCENE_UNIT_UNCALIBRATED",
  Measurements:[]gate.Measure{{Region:"arm",Method:"unaligned_bbox_proxy",NativeValue:2}},
  HeldoutStatus:"NOT_TESTED",OODStatus:"NOT_TESTED"}
 trust:=gate.Registry{PinnedMacroConfigSHA256:macro,
  PresetToMacro:map[string]float64{"female":0,"male":1},
  ScaleByID:map[string]gate.TrustedScale{},
  QualifiedRegionMethods:map[string]bool{}}
 r,e:=gate.Validate(spec,trust);if e!=nil {panic(e)}
 data,err:=os.ReadFile("morphgate.go");if err!=nil {panic(err)}
 digest:=sha256.Sum256(data)
 doc:=struct {
  Schema string `json:"schema"`
  Status string `json:"status"`
  GitHubSHA string `json:"github_sha_checkout_may_be_pr_merge_ref"`
  GitHubRunID string `json:"github_run_id"`
  SourceSHA256 string `json:"morphgate_source_sha256"`
  InputClass string `json:"input_class"`
  Diagnostic gate.Result `json:"diagnostic"`
  Limitations []string `json:"limitations"`
 }{Schema:"r015.synthetic_morphology_consumer_negative_receipt.v1",
  Status:"PASS_SYNTHETIC_NEGATIVE_CONTROLS_ONLY",
  GitHubSHA:os.Getenv("GITHUB_SHA"),GitHubRunID:os.Getenv("GITHUB_RUN_ID"),
  SourceSHA256:hex.EncodeToString(digest[:]),InputClass:"synthetic spec only; no person or proprietary assets",
  Diagnostic:r,Limitations:[]string{"Not an actual Blender source measurement", "No verified SI scale, source rights or anatomy", "No CharacterPack or CPE canonical authority"}}
 raw,e:=json.MarshalIndent(doc,"","  ");if e!=nil {panic(e)}
 fmt.Println(string(raw))
}
