// W9-A: domain-conditioned admission only; source GT != normative human/animal/robot gait.
package main
import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "fmt"
 "math"
 "os"
)
const rights="ORIGINAL_SELF_AUTHORED_SYNTHETIC"
type Leg struct{ ID string `json:"id"` }
type Frame struct {
 Index int `json:"index"`
 TimeNum int `json:"time_num"`
 TimeDen int `json:"time_den"`
 Legs []Leg `json:"legs"`
}
type Actor struct {ID string `json:"id"`; Frames []Frame `json:"frames"`}
type Source struct{
 Schema string `json:"schema"`
 Rights string `json:"rights"`
 Profile string `json:"profile"`
 FPSNum int `json:"fps_num"`
 FPSDen int `json:"fps_den"`
 Scenario string `json:"scenario"`
 KneePoleBasis string `json:"knee_pole_basis"`
 Actors []Actor `json:"actors"`
}
type Policy struct{
 Schema string `json:"schema"`
 SubjectKind string `json:"subject_kind"`
 Action string `json:"action"`
 Style string `json:"style"`
 NormativeRefIDs []string `json:"normative_ref_ids"`
 NumericLimits map[string]interface{} `json:"numeric_limits"`
 UseSourcePoleAsAnatomicalJCS bool `json:"use_source_pole_as_anatomical_jcs"`
 SourceRigHasAnatomicalUpperBody bool `json:"source_rig_has_anatomical_upper_body"`
}
type Finding struct{
 Code string `json:"code"`
 Status string `json:"status"`
 Scope string `json:"scope"`
}
type Verdict struct{
 Schema string `json:"schema"`
 SourceSHA256 string `json:"source_sha256"`
 SourceRights string `json:"source_rights"`
 SubjectKind string `json:"subject_kind"`
 Action string `json:"action"`
 Eligibility string `json:"eligibility"`
 HumanAnatomicalJCS string `json:"human_anatomical_jcs"`
 NormativeROM string `json:"normative_rom"`
 HumanNaturalGait string `json:"human_natural_gait"`
 AnimalBehavior string `json:"animal_behavior"`
 MechanicalDynamics string `json:"mechanical_dynamics"`
 PhysicalForces string `json:"physical_forces"`
 CleanVideoEvaluation string `json:"clean_video_evaluation"`
 SourceGroundTruthIsNormativeOracle bool `json:"source_ground_truth_is_normative_oracle"`
 ReferenceStatus string `json:"reference_status"`
 Findings []Finding `json:"findings"`
}
func add(v *Verdict,code,status,scope string){
 v.Findings=append(v.Findings,Finding{code,status,scope})
}
func Validate(s Source,p Policy) error{
 if s.Schema!="scp.walk_w7a_original_approach.v1"||s.Rights!=rights||
  s.Scenario!="ORIGINAL_2ACTOR_WORLD_X_APPROACH_NOT_HUMAN_GAIT"||
  s.FPSNum!=12||s.FPSDen!=1||(s.Profile!="forward"&&s.Profile!="outward"){
  return fmt.Errorf("W9A_SOURCE_RIGHTS_CLOCK")
 }
 if len(s.Actors)!=2{return fmt.Errorf("W9A_ACTOR_COVERAGE")}
 for _,a:=range s.Actors{
  if len(a.Frames)!=24||a.ID==""{return fmt.Errorf("W9A_FRAME_COVERAGE")}
  for i,f:=range a.Frames{
   if f.Index!=i||f.TimeNum!=i||f.TimeDen!=12||len(f.Legs)!=2||
    f.Legs[0].ID!="Left"||f.Legs[1].ID!="Right"{
    return fmt.Errorf("W9A_ACTOR_CLOCK_OR_LEG_IDS")
   }
  }
 }
 if p.Schema!="scp.visualqa.w9a_policy.v1"||p.Action!="walking"{
  return fmt.Errorf("W9A_POLICY_ACTION_SCHEMA")
 }
 if p.SubjectKind!="human"&&p.SubjectKind!="animal"&&p.SubjectKind!="mechanical"{
  return fmt.Errorf("W9A_UNKNOWN_SUBJECT_KIND")
 }
 if p.Style!="typical"&&p.Style!="stylized"&&p.Style!="robotic"&&p.Style!="injured"{
  return fmt.Errorf("W9A_UNDECLARED_STYLE_EXCEPTION")
 }
 if p.UseSourcePoleAsAnatomicalJCS{return fmt.Errorf("W9A_CIRCULAR_SOURCE_POLE_AS_JCS")}
 if p.SourceRigHasAnatomicalUpperBody{return fmt.Errorf("W9A_UNSUPPORTED_RIGGED_UPPER_BODY_ASSERTION")}
 if len(p.NumericLimits)>0{return fmt.Errorf("W9A_UNAPPROVED_NUMERIC_LIMIT_CLAIM")}
 if len(p.NormativeRefIDs)!=2||p.NormativeRefIDs[0]!="ISB_2002_JCS_REFERENCE_ONLY"||p.NormativeRefIDs[1]!="NMS_VV_2014_VALIDATION_GUIDANCE_ONLY"{
  return fmt.Errorf("W9A_UNQUALIFIED_REFERENCE_SET")
 }
 if s.KneePoleBasis!="ARTIFICIAL_SAGITTAL_FORWARD_Y_NO_ANATOMICAL_JCS"{
  return fmt.Errorf("W9A_SOURCE_KNEE_POLE_NOT_ADMITTED")
 }
 return nil
}
func Evaluate(s Source,p Policy,sourceHash string) (Verdict,error){
 v:=Verdict{Schema:"scp.visualqa.w9a_normative_admission.v1",SourceSHA256:sourceHash,
  SourceRights:s.Rights,SubjectKind:p.SubjectKind,Action:p.Action,
  Eligibility:"UNKNOWN_NO_INDEPENDENT_FULLBODY_RIG",
  HumanAnatomicalJCS:"UNKNOWN_NOT_MAPPED",
  NormativeROM:"UNKNOWN_NO_APPROVED_INDIVIDUAL_LIMITS",
  HumanNaturalGait:"ABSTAIN_UNQUALIFIED_SOURCE_RIG",
  AnimalBehavior:"ABSTAIN_NOT_ANIMAL_SOURCE",
  MechanicalDynamics:"ABSTAIN_NO_ACTUATOR_AND_LIMITS",
  PhysicalForces:"UNKNOWN_NO_MEASURED_FORCES_OR_MASSES",
  CleanVideoEvaluation:"NOT_RUN_SEPARATE_INDEPENDENT_CLEAN_VIDEO",
  SourceGroundTruthIsNormativeOracle:false,
  ReferenceStatus:"LINK_ONLY_COORDINATE_STANDARD_AND_VV_GUIDANCE_NO_NUMERIC_ROM_LICENSED",
  Findings:[]Finding{}}
 if err:=Validate(s,p);err!=nil{return v,err}
 switch p.SubjectKind{
 case "human":
  v.Eligibility="ABSTAIN_INCOMPLETE_ANATOMICAL_LOWER_UPPER_AXES"
  add(&v,"W9A_SIX_BONE_LOWER_BODY_WITHOUT_AUTHORED_ANATOMICAL_UPPER_JCS","ABSTAIN","fullbody")
  add(&v,"W9A_ARTIFICIAL_KNEE_POLE_NOT_ANATOMICAL_JCS","UNKNOWN","human_jcs")
  add(&v,"W9A_JCS_REFERENCE_DOES_NOT_SUPPLY_ROM_LIMITS","UNKNOWN","normative_rom")
 case "animal":
  v.Eligibility="ABSTAIN_WRONG_TAXON_AND_HOMOLOGY"
  v.HumanNaturalGait="NOT_APPLICABLE_HUMAN"
  v.AnimalBehavior="ABSTAIN_SPECIES_HOMOLOGY_MODEL_NOT_LOADED"
  add(&v,"W9A_HUMAN_JCS_NOT_APPLIED_TO_ANIMAL","ABSTAIN","taxon")
 case "mechanical":
  v.Eligibility="ABSTAIN_NO_ENGINEERING_DOF_OR_LOAD_PROFILE"
  v.HumanNaturalGait="NOT_APPLICABLE_HUMAN"
  v.AnimalBehavior="NOT_APPLICABLE_ANIMAL"
  v.MechanicalDynamics="ABSTAIN_NO_JOINT_ACTUATOR_ENVELOPE"
  add(&v,"W9A_BIOLOGICAL_PRIOR_NOT_APPLIED_TO_MECHANICAL","ABSTAIN","domain")
 }
 if p.Style!="typical"{
  add(&v,"W9A_STYLE_EXCEPTION_DECLARED_NOT_AUTOMATIC_ACCEPTANCE","UNKNOWN","style")
 }
 return v,nil
}
func main(){
 if len(os.Args)!=4{fmt.Fprintln(os.Stderr,"usage: w9a SOURCE.json POLICY.json OUT.json");os.Exit(2)}
 raw,e:=os.ReadFile(os.Args[1]);if e!=nil{panic(e)}
 var s Source
 if e=json.Unmarshal(raw,&s);e!=nil{panic(e)}
 b,e:=os.ReadFile(os.Args[2]);if e!=nil{panic(e)}
 var p Policy
 if e=json.Unmarshal(b,&p);e!=nil{panic(e)}
 sum:=sha256.Sum256(raw);sourceHash:=hex.EncodeToString(sum[:])
 expected:=map[string]string{"forward":"c1ebf84b60bacaf4d1132f88dcfd588c9b94fa1790a3e48f163dfd195e22b449",
 "outward":"ade0dad65d9ef9d9febeaf540ce453841587276888ce03b45f3cc3f6a18346fc"}
 if sourceHash!=expected[s.Profile]{panic("W9A_AUTHENTIC_SOURCE_HASH_CHANGED")}
 v,e:=Evaluate(s,p,sourceHash);if e!=nil{panic(e)}
 out,e:=json.MarshalIndent(v,"","  ");if e!=nil{panic(e)}
 if e=os.WriteFile(os.Args[3],append(out,byte(10)),0644);e!=nil{panic(e)}
 fmt.Println("W9A_NORMATIVE_REFERENCE_GUARD_ONLY",v.SubjectKind,v.Eligibility,v.NormativeROM)
}
