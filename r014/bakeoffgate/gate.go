// Package bakeoffgate validates source/venue/pose comparability before R014
// experiments. Passing this gate is NOT a motion, geometry or rights grant.
package bakeoffgate

import (
 "bytes"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "strings"
)

const Schema = "r014.mhr_corrective_bakeoff_plan.v1"
const Status = "READY_TO_EXECUTE_RESEARCH_ONLY__NO_QUALITY_OR_RELEASE_PASS"

type Input struct {
 ID string `json:"id"`
 Kind string `json:"kind"`
 SHA256 string `json:"sha256"`
}
// Grants are supplied by an independent trusted registry, never by the candidate
// plan. The registry itself requires human source-rights review.
type Grant struct {
 InputID string
 Kind string
 SHA256 string
 Venue string
 Operation string
 Scope string // PUBLIC_ADMITTED, CONTROLLED_LOCAL or PRIVATE_CLOUD_ADMITTED
 ProofSHA256 string
}
// CrosswalkProof is independent of the candidate plan. It is still only
// registry attestation, not a re-evaluation of the actual mapped skeleton.
type CrosswalkProof struct {
 SHA256 string
 NativeJoints int
 ImportedJoints int
 Verified bool
 ProofSHA256 string
}
// SamplingWitness is a source-hash-bound index transcript obtained from a
// distinct reviewer. Authenticity of source reading and reviewer identity
// must be established OUTSIDE this package.
type SamplingWitness struct {
 ClipID string
 MotionSHA256 string
 PolicySHA256 string
 SourceFrameCount int
 SourceHz int
 TargetHz int
 Indices []int
 ManifestSHA256 string
 Verified bool
 ReviewerProofSHA256 string
}
type Registry struct {
 Grants map[string]Grant
 Crosswalk CrosswalkProof
 Samples map[string]SamplingWitness
}

type Clip struct {
 ID string `json:"id"`
 Frames int `json:"frames"`
 MotionSHA256 string `json:"motion_sha256"`
 ModelSHA256 string `json:"model_sha256"`
 JointMapSHA256 string `json:"joint_map_sha256"`
 TopologyMapSHA256 string `json:"topology_map_sha256"`
 CalibrationSHA256 string `json:"calibration_sha256"`
 RestPoseSHA256 string `json:"rest_pose_sha256"`
 NativeFBXSHA256 string `json:"native_fbx_sha256"`
 CorrectiveActivationSHA256 string `json:"corrective_activation_sha256"`
 CorrectiveShapesSHA256 string `json:"corrective_shapes_sha256"`
 SamplingPolicySHA256 string `json:"sampling_policy_sha256"`
 SourceSampleCount int `json:"source_sample_count"`
 SourceHz int `json:"source_hz"`
 TargetHz int `json:"target_hz"`
 Stride int `json:"source_sample_stride"`
 FirstSourceIndex int `json:"first_source_index_zero_based"`
 LastSourceIndex int `json:"last_source_index_zero_based"`
 SampleManifestSHA256 string `json:"sample_manifest_sha256"`
 SamplingMethod string `json:"sampling_method"`
 LOD int `json:"lod"`
}
type Arm struct {
 ClipID string `json:"clip_id"`
 Engine string `json:"engine"`
 Frames int `json:"frames"`
 MotionSHA256 string `json:"motion_sha256"`
 ModelSHA256 string `json:"model_sha256"`
 JointMapSHA256 string `json:"joint_map_sha256"`
 TopologyMapSHA256 string `json:"topology_map_sha256"`
 CalibrationSHA256 string `json:"calibration_sha256"`
 RestPoseSHA256 string `json:"rest_pose_sha256"`
 NativeFBXSHA256 string `json:"native_fbx_sha256"`
 CorrectiveActivationSHA256 string `json:"corrective_activation_sha256"`
 CorrectiveShapesSHA256 string `json:"corrective_shapes_sha256"`
 SamplingPolicySHA256 string `json:"sampling_policy_sha256"`
 SourceSampleCount int `json:"source_sample_count"`
 SourceHz int `json:"source_hz"`
 TargetHz int `json:"target_hz"`
 Stride int `json:"source_sample_stride"`
 FirstSourceIndex int `json:"first_source_index_zero_based"`
 LastSourceIndex int `json:"last_source_index_zero_based"`
 SampleManifestSHA256 string `json:"sample_manifest_sha256"`
 SamplingMethod string `json:"sampling_method"`
 LOD int `json:"lod"`
 ApplyCorrectives bool `json:"apply_correctives"`
 GroundSnap bool `json:"ground_snap"`
}
type Plan struct {
 Schema string `json:"schema"`
 Venue string `json:"venue"`
 Operation string `json:"operation"`
 Inputs []Input `json:"inputs"`
 NativeJointCount int `json:"native_joint_count"`
 ImportedJointCount int `json:"imported_joint_count"`
 JointMapVerification string `json:"joint_map_verification"`
 Clips []Clip `json:"clips"`
 Arms []Arm `json:"arms"`
 OutputScope string `json:"output_scope"`
 Claim string `json:"claim"`
}
type Verdict struct {
 Schema string `json:"schema"`
 Status string `json:"status"`
 SourceRights string `json:"source_rights"`
 Geometry string `json:"geometry"`
 Motion string `json:"motion"`
 Cinematic string `json:"cinematic"`
 CanonicalCharacterPack string `json:"canonical_character_pack"`
 Holds []string `json:"holds"`
}

func verdict() Verdict {
 return Verdict{Schema:"r014.mhr_bakeoff_admission_diagnostic.v1",
  Status:"REJECT_OR_UNKNOWN",SourceRights:"UNQUALIFIED_UNTIL_INDEPENDENT_SOURCE_REVIEW",
  Geometry:"HOLD_REAL_MHR_FULL_SEQUENCE",Motion:"HOLD_SOURCE_KNEE_ANKLE_CONTACT",
  Cinematic:"HOLD_HUMAN_ANATOMY_AND_VISUAL_REVIEW",
  CanonicalCharacterPack:"HOLD_OWNER_HUMAN_ONLY",
  Holds:[]string{"No donor execution or numeric geometry measurements implied",
   "127-to-126 semantic correspondence requires independent evidence",
   "Source rights are operation-specific; no vendor or model permission inferred",
   "Product D1-D4 and release HOLD"}}
}
func digest(s string) bool {
 if len(s)!=64{return false}
 b,e:=hex.DecodeString(s)
 return e==nil&&len(b)==32
}
// SampleManifestDigest commits the exact declared sample-index transcript
// to the source and policy SHA. This does not authenticate source frames.
func SampleManifestDigest(id,motion,policy string,count,sourceHz,targetHz int,indices []int) string {
 b,_:=json.Marshal(struct {
  ClipID string `json:"clip_id"`
  MotionSHA256 string `json:"motion_sha256"`
  PolicySHA256 string `json:"policy_sha256"`
  SourceFrameCount int `json:"source_frame_count"`
  SourceHz int `json:"source_hz"`
  TargetHz int `json:"target_hz"`
  Indices []int `json:"indices"`
 }{id,motion,policy,count,sourceHz,targetHz,indices})
 sum:=sha256.Sum256(b)
 return hex.EncodeToString(sum[:])
}
func DecodeStrict(data []byte)(Plan,error){
 var p Plan
 dec:=json.NewDecoder(bytes.NewReader(data))
 dec.DisallowUnknownFields()
 if e:=dec.Decode(&p);e!=nil{return p,e}
 var extra any
 if e:=dec.Decode(&extra);e!=io.EOF{return p,errors.New("trailing or concatenated JSON")}
 return p,nil
}
func Validate(p Plan, trusted Registry)(Verdict,error){
 v:=verdict()
 if p.Schema!=Schema{return v,errors.New("unsupported plan schema")}
 if p.Venue!="public_github_actions"&&p.Venue!="controlled_local"&&p.Venue!="private_github_actions"{
  return v,errors.New("unsupported venue")
 }
 if p.Operation!="geometry_evaluation"{return v,errors.New("operation must be explicitly geometry_evaluation")}
 if p.Claim!="DIAGNOSTIC_ONLY"{return v,errors.New("quality/release claim prohibited")}
 if p.OutputScope!="NUMERIC_AGGREGATES_ONLY"{return v,errors.New("source or visual artifact export is not admitted by this gate")}
 if p.NativeJointCount!=127||p.ImportedJointCount!=126||
  p.JointMapVerification!="INDEPENDENTLY_VERIFIED_127_TO_126"{
  return v,errors.New("native-to-imported joint semantics unverified")
 }
 required:=map[string]string{"model":"model_weights","cmu07_01":"motion","cmu07_02":"motion",
  "joint_map":"joint_crosswalk","topology_map":"topology_crosswalk",
  "calibration":"unit_calibration","rest_pose":"rest_pose",
  "native_fbx":"native_fbx","corrective_activation":"corrective_activation_weights",
  "corrective_shapes_lod1":"lod1_corrective_shapes","sampling_policy":"sampling_policy"}
 if len(p.Inputs)!=len(required){return v,errors.New("missing or excess source inputs")}
 inputs:=map[string]Input{}
 for _,in:=range p.Inputs{
  want,ok:=required[in.ID]
  if !ok||in.Kind!=want||!digest(in.SHA256){return v,fmt.Errorf("invalid input %q",in.ID)}
  if _,ok:=inputs[in.ID];ok{return v,fmt.Errorf("duplicate input %q",in.ID)}
  inputs[in.ID]=in
  grant,ok:=trusted.Grants[in.ID]
  if !ok||grant.InputID!=in.ID||grant.SHA256!=in.SHA256||
   grant.Kind!=in.Kind||grant.Operation!=p.Operation||
   grant.Venue!=p.Venue||!digest(grant.ProofSHA256){
   return v,fmt.Errorf("independent source/operation/venue admission missing for %q",in.ID)
  }
  if p.Venue=="public_github_actions"&&grant.Scope!="PUBLIC_ADMITTED"{
   return v,fmt.Errorf("protected source %q cannot enter public runner",in.ID)
  }
  if p.Venue=="controlled_local"&&grant.Scope!="PUBLIC_ADMITTED"&&grant.Scope!="CONTROLLED_LOCAL"{
   return v,fmt.Errorf("invalid local scope %q",in.ID)
  }
  if p.Venue=="private_github_actions"&&grant.Scope!="PUBLIC_ADMITTED"&&grant.Scope!="PRIVATE_CLOUD_ADMITTED"{
   return v,fmt.Errorf("protected source %q lacks private-cloud admission",in.ID)
  }
 }
 crosswalk:=trusted.Crosswalk
 if !crosswalk.Verified||crosswalk.SHA256!=inputs["joint_map"].SHA256||
  crosswalk.NativeJoints!=p.NativeJointCount||
  crosswalk.ImportedJoints!=p.ImportedJointCount||
  !digest(crosswalk.ProofSHA256){
  return v,errors.New("independent native-to-imported joint crosswalk admission missing")
 }
 if len(p.Clips)!=2||len(p.Arms)!=8{return v,errors.New("both complete clips and four arms per clip required")}
 expectedFrames:=map[string]int{"CMU07_01":64,"CMU07_02":66}
 clipByID:=map[string]Clip{}
 for _,c:=range p.Clips{
  f,ok:=expectedFrames[c.ID];if !ok||c.Frames!=f{return v,fmt.Errorf("invalid clip identity/frames %q",c.ID)}
  if _,ok:=clipByID[c.ID];ok{return v,fmt.Errorf("duplicate clip %q",c.ID)}
  sourceID:=strings.ToLower(c.ID)
  expectedSourceSamples:=map[string]int{"CMU07_01":316,"CMU07_02":329}
  if c.SourceSampleCount!=expectedSourceSamples[c.ID]||c.SourceHz!=120||
   c.TargetHz!=24||c.Stride!=5||c.FirstSourceIndex!=0||
   c.LastSourceIndex!=((c.SourceSampleCount-1)/c.Stride)*c.Stride||
   c.Frames!=(c.SourceSampleCount-1)/c.Stride+1||
   c.SamplingMethod!="EXACT_INTEGER_STRIDE_NO_INTERPOLATION"||
   c.LOD!=1{
   return v,fmt.Errorf("unproven source timebase, LOD or sample-index schedule for %q",c.ID)
  }
  if c.MotionSHA256!=inputs[sourceID].SHA256||c.ModelSHA256!=inputs["model"].SHA256||
   c.JointMapSHA256!=inputs["joint_map"].SHA256||c.TopologyMapSHA256!=inputs["topology_map"].SHA256||
   c.CalibrationSHA256!=inputs["calibration"].SHA256||c.RestPoseSHA256!=inputs["rest_pose"].SHA256||
   c.NativeFBXSHA256!=inputs["native_fbx"].SHA256||
   c.CorrectiveActivationSHA256!=inputs["corrective_activation"].SHA256||
   c.CorrectiveShapesSHA256!=inputs["corrective_shapes_lod1"].SHA256||
   c.SamplingPolicySHA256!=inputs["sampling_policy"].SHA256{
   return v,fmt.Errorf("unbound source/model/map/calibration/rest for %q",c.ID)
  }
  witness,ok:=trusted.Samples[c.ID]
  if !ok||!witness.Verified||!digest(witness.ReviewerProofSHA256)||
   witness.ClipID!=c.ID||witness.MotionSHA256!=c.MotionSHA256||
   witness.PolicySHA256!=c.SamplingPolicySHA256||
   witness.SourceFrameCount!=c.SourceSampleCount||
   witness.SourceHz!=c.SourceHz||witness.TargetHz!=c.TargetHz||
   len(witness.Indices)!=c.Frames{
   return v,fmt.Errorf("independent exact sample index witness missing for %q",c.ID)
  }
  for i,index:=range witness.Indices{
   if index!=c.FirstSourceIndex+i*c.Stride||index>=c.SourceSampleCount{
    return v,fmt.Errorf("missing, reordered or interpolated source index for %q at frame %d",c.ID,i)
   }
  }
  expectedManifest:=SampleManifestDigest(c.ID,c.MotionSHA256,c.SamplingPolicySHA256,
   c.SourceSampleCount,c.SourceHz,c.TargetHz,witness.Indices)
  if !digest(c.SampleManifestSHA256)||c.SampleManifestSHA256!=expectedManifest||
   witness.ManifestSHA256!=expectedManifest{
   return v,fmt.Errorf("unbound or altered source index manifest for %q",c.ID)
  }
  clipByID[c.ID]=c
 }
 wanted:=map[string]bool{"native_correctives_off":true,"native_correctives_on":true,
  "blender_linear_skinning":true,"blender_preserve_volume":true}
 seen:=map[string]bool{}
 for _,a:=range p.Arms{
  c,ok:=clipByID[a.ClipID]
  if !ok||!wanted[a.Engine]{return v,errors.New("unrecognized clip or comparison engine")}
  key:=a.ClipID+"/"+a.Engine
  if seen[key]{return v,fmt.Errorf("duplicate arm %q",key)}
  seen[key]=true
  if a.Frames!=c.Frames||a.MotionSHA256!=c.MotionSHA256||
   a.ModelSHA256!=c.ModelSHA256||a.JointMapSHA256!=c.JointMapSHA256||
   a.TopologyMapSHA256!=c.TopologyMapSHA256||
   a.CalibrationSHA256!=c.CalibrationSHA256||a.RestPoseSHA256!=c.RestPoseSHA256||
   a.NativeFBXSHA256!=c.NativeFBXSHA256||
   a.CorrectiveActivationSHA256!=c.CorrectiveActivationSHA256||
   a.CorrectiveShapesSHA256!=c.CorrectiveShapesSHA256||
   a.SamplingPolicySHA256!=c.SamplingPolicySHA256||
   a.SampleManifestSHA256!=c.SampleManifestSHA256||
   a.SourceSampleCount!=c.SourceSampleCount||a.SourceHz!=c.SourceHz||
   a.TargetHz!=c.TargetHz||a.Stride!=c.Stride||
   a.FirstSourceIndex!=c.FirstSourceIndex||a.LastSourceIndex!=c.LastSourceIndex||
   a.SamplingMethod!=c.SamplingMethod||a.LOD!=c.LOD{
   return v,fmt.Errorf("comparison mismatch for %q",key)
  }
  if a.GroundSnap{return v,fmt.Errorf("default ground snap confounds comparison %q",key)}
  if a.ApplyCorrectives!=(a.Engine=="native_correctives_on"){
   return v,fmt.Errorf("uncertified correctives switch for %q",key)
  }
 }
 for id:=range clipByID{for name:=range wanted{if !seen[id+"/"+name]{return v,fmt.Errorf("missing %s/%s",id,name)}}}
 v.Status=Status
 v.SourceRights="MATCHED_TRUST_REGISTRY_FOR_PROPOSED_SCOPE_ONLY__NOT_SOURCE_LICENSE_PROOF"
 return v,nil
}
