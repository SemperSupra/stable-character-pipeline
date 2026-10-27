package main

// Three independent, offline public CPU qualification lanes.
// No pretrained inference, external downloads, private data, or GPU.
import (
  "crypto/sha256"
  "encoding/json"
  "errors"
  "flag"
  "fmt"
  "math"
  "os"
  "sort"
  "strings"
)

type Registry struct {
  Schema string `json:"schema"`
  ResearchLane string `json:"research_lane"`
  FetchWeights bool `json:"fetch_weights"`
  FetchSourceMedia bool `json:"fetch_source_media"`
  ExecuteModelInference bool `json:"execute_model_inference"`
  AllowPrivateInputs bool `json:"allow_private_inputs"`
  AllowPaidCompute bool `json:"allow_paid_compute"`
  Candidates []Candidate `json:"candidates"`
}
type Candidate struct {
  ID string `json:"id"`
  Capability string `json:"capability"`
  Upstream string `json:"upstream"`
  CodeLicense string `json:"code_license"`
  WeightsTerms string `json:"weights_terms"`
  WeightsAccess string `json:"weights_access"`
  ExternalAssets []string `json:"external_assets"`
  SourceMediaRights string `json:"source_media_rights"`
  TargetRigRights string `json:"target_rig_rights"`
  ActualInferenceStatus string `json:"actual_inference_status"`
}
type AdapterContract struct {
  Model string `json:"model"`
  Capability string `json:"capability"`
  RequiredInputs []string `json:"required_inputs"`
  OutputKind string `json:"output_kind"`
  RequiresExistingRig bool `json:"requires_existing_rig"`
  SourceRights string `json:"source_rights"`
  ModelWeightsRights string `json:"model_weights_rights"`
  DestinationRigRights string `json:"destination_rig_rights"`
  Tested string `json:"tested"`
}
type Receipt struct {
  Schema string `json:"schema"`
  Lane string `json:"lane"`
  Status string `json:"status"`
  RegistrySHA256 string `json:"registry_sha256"`
  SourceOnly bool `json:"source_only"`
  ActualModelInferences int `json:"actual_model_inferences"`
  WeightsDownloaded int `json:"weights_downloaded"`
  GPURuns int `json:"gpu_runs"`
  Candidates int `json:"candidates,omitempty"`
  Contracts []AdapterContract `json:"contracts,omitempty"`
  Synthetic *SkinReport `json:"synthetic,omitempty"`
  NextGate string `json:"next_gate"`
}
func validRegistry(r Registry) error {
  if r.Schema!="stable-character/r4-upstream-admission/1" || r.ResearchLane!="PUBLIC_CPU_SOURCE_METADATA_ONLY"{
    return errors.New("wrong source-only registry schema")
  }
  if r.FetchWeights || r.FetchSourceMedia || r.ExecuteModelInference || r.AllowPrivateInputs || r.AllowPaidCompute{
    return errors.New("public CPU must not download media/weights, run models, private assets or paid compute")
  }
  if len(r.Candidates)!=5{return errors.New("expected exactly five reviewed source candidates")}
  seen:=map[string]bool{}
  for _,c:=range r.Candidates{
    if seen[c.ID] || c.ID=="" || c.Capability=="" || c.SourceMediaRights!="PER_FILE_REVIEW" ||
      c.TargetRigRights=="" || c.WeightsAccess=="" || c.WeightsTerms=="" || c.CodeLicense=="" ||
      !strings.HasPrefix(c.Upstream,"https://github.com/") || c.ActualInferenceStatus!="NOT_TESTED"{
      return fmt.Errorf("unadmitted rights or model status for %q",c.ID)
    }
    if len(c.ExternalAssets)==0{return fmt.Errorf("unreviewed input asset dependencies for %s",c.ID)}
    seen[c.ID]=true
  }
  for _,id:=range []string{"unirig","skintokens","mocapanything-v2","sam-3d-body","motion2mixamorig"}{
    if !seen[id]{return fmt.Errorf("missing reviewed candidate %s",id)}
  }
  return nil
}
func contracts(r Registry)([]AdapterContract,error){
  if err:=validRegistry(r);err!=nil{return nil,err}
  result:=make([]AdapterContract,0,len(r.Candidates))
  for _,c:=range r.Candidates{
    x:=AdapterContract{
      Model:c.ID, Capability:c.Capability,
      SourceRights:c.SourceMediaRights, ModelWeightsRights:c.WeightsTerms,
      DestinationRigRights:c.TargetRigRights,
      Tested:"CONTRACT_ONLY_NO_MODEL_INFERENCE",
    }
    switch c.Capability{
    case "MESH_TO_SKELETON_AND_WEIGHTS":
      x.RequiredInputs=[]string{"RIGHTS_ADMITTED_MESH"}
      x.OutputKind="MODEL_ESTIMATED_SKELETON_AND_SKIN_WEIGHTS"
    case "VIDEO_AND_REFERENCE_RIG_TO_MOTION":
      x.RequiredInputs=[]string{"RIGHTS_ADMITTED_VIDEO","RIGHTS_ADMITTED_REFERENCE_RIG"}
      x.RequiresExistingRig=true
      x.OutputKind="MODEL_ESTIMATED_JOINT_MOTION"
    case "PHOTO_TO_MODEL_ESTIMATED_BODY_MESH":
      x.RequiredInputs=[]string{"RIGHTS_ADMITTED_PHOTO"}
      x.OutputKind="MODEL_ESTIMATED_BODY_MESH"
    case "PHOTO_OR_VIDEO_TO_EXISTING_RIG_MOTION":
      x.RequiredInputs=[]string{"RIGHTS_ADMITTED_PHOTO_OR_VIDEO","RIGHTS_ADMITTED_REFERENCE_RIG"}
      x.RequiresExistingRig=true
      x.OutputKind="MODEL_ESTIMATED_EXISTING_RIG_MOTION"
    default: return nil,fmt.Errorf("unsupported new capability %q",c.Capability)
    }
    result=append(result,x)
  }
  sort.Slice(result,func(i,j int)bool{return result[i].Model<result[j].Model})
  return result,nil
}
type AdapterRequest struct{
  HasMediaRights bool
  HasWeightRights bool
  HasDestinationRigRights bool
  MediaKind string
  ReferenceRig bool
  ClaimTrue3D bool
  ClaimIdentityRecovered bool
  AutoDownload bool
}
// Tests only the typed adapter preflight, never admits a model-run.
func validateAdapter(c AdapterContract, req AdapterRequest)error{
  if req.AutoDownload||req.ClaimTrue3D||req.ClaimIdentityRecovered{
    return errors.New("unsubstantiated model execution, depth or identity claim")
  }
  if !req.HasMediaRights||!req.HasWeightRights||!req.HasDestinationRigRights{
    return errors.New("media, weights and destination rig rights require independent admission")
  }
  if c.RequiresExistingRig && !req.ReferenceRig{return errors.New("missing reference rig")}
  switch c.OutputKind{
  case "MODEL_ESTIMATED_SKELETON_AND_SKIN_WEIGHTS":
    if req.MediaKind!="mesh"{return errors.New("mesh input required")}
  case "MODEL_ESTIMATED_JOINT_MOTION":
    if req.MediaKind!="video"{return errors.New("video input required")}
  case "MODEL_ESTIMATED_BODY_MESH":
    if req.MediaKind!="photo"{return errors.New("photo input required")}
  case "MODEL_ESTIMATED_EXISTING_RIG_MOTION":
    if req.MediaKind!="photo"&&req.MediaKind!="video"{return errors.New("photo or video input required")}
  default:return errors.New("unadmitted target/output contract")
  }
  return nil // contract shape is valid, not model-execution authorization
}

type Joint struct{Parent int; Rest [3]float64}
type Vertex struct{Pos [3]float64; IDs [2]int; W [2]float64}
type Pose struct{TimeMS int; Delta [][3]float64; Visible []bool}
type Rig struct{Joints []Joint; Vertices []Vertex; Frames []Pose}
type SkinReport struct{
  Classification string `json:"classification"`
  JointCount int `json:"joint_count"`
  VertexCount int `json:"vertex_count"`
  Frames int `json:"frames"`
  SourceClockMS []int `json:"source_clock_ms"`
  MaxVertexDisplacement float64 `json:"max_vertex_displacement_arbitrary_units"`
  ActualBlenderImport bool `json:"actual_blender_import"`
  Metric3DRecovered bool `json:"metric_3d_recovered"`
}
func finite(v float64)bool{return !math.IsNaN(v)&&!math.IsInf(v,0)}
func validateRig(r Rig)error{
  n:=len(r.Joints)
  if n<2||n>64||len(r.Vertices)==0||len(r.Vertices)>1024||len(r.Frames)<2||len(r.Frames)>30{
    return errors.New("fixture topology or sample count out of bounds")
  }
  roots:=0
  for i,j:=range r.Joints{
    if j.Parent==-1{roots++}else if j.Parent<0||j.Parent>=n||j.Parent==i{
      return errors.New("invalid joint parent")
    }
    for _,v:=range j.Rest{if !finite(v){return errors.New("nonfinite joint rest")}}
    seen:=map[int]bool{}
    x:=i
    for x>=0{
      if seen[x]{return errors.New("joint cycle")}
      seen[x]=true
      x=r.Joints[x].Parent
    }
  }
  if roots!=1{return errors.New("synthetic fixture needs exactly one root")}
  for _,v:=range r.Vertices{
    for _,x:=range v.Pos{if !finite(x){return errors.New("nonfinite vertex")}}
    if math.Abs(v.W[0]+v.W[1]-1)>1e-7 || v.W[0]<0||v.W[1]<0 || !finite(v.W[0])||!finite(v.W[1]){
      return errors.New("skin weights not normalized")
    }
    for k,j:=range v.IDs{if j<0||j>=n || (v.W[k]>0&&j>=n){return errors.New("vertex joint reference out of bounds")}}
  }
  for i,p:=range r.Frames{
    if p.TimeMS!=i*1000{return errors.New("noncontiguous source clock or invented interpolation")}
    if len(p.Delta)!=n||len(p.Visible)!=n{return errors.New("missing pose/joint visibility values")}
    for j:=0;j<n;j++{
      if !p.Visible[j]{return errors.New("missing joint observations cannot be silently interpolated")}
      for _,v:=range p.Delta[j]{if !finite(v){return errors.New("nonfinite joint motion")}}
    }
  }
  return nil
}
func world(r Rig, at int, usePose bool)([][3]float64,error){
  if err:=validateRig(r);err!=nil{return nil,err}
  out:=make([][3]float64,len(r.Joints))
  done:=make([]bool,len(out))
  var eval func(int)[3]float64
  eval=func(j int)[3]float64{
    if done[j]{return out[j]}
    x:=r.Joints[j].Rest
    if usePose{for k:=0;k<3;k++{x[k]+=r.Frames[at].Delta[j][k]}}
    if p:=r.Joints[j].Parent;p>=0{
      base:=eval(p)
      for k:=0;k<3;k++{x[k]+=base[k]}
    }
    out[j]=x
    done[j]=true
    return x
  }
  for j:=range out{eval(j)}
  return out,nil
}
func deform(r Rig,at int)([][3]float64,error){
  if err:=validateRig(r);err!=nil{return nil,err}
  if at<0||at>=len(r.Frames){return nil,errors.New("requested sample out of bounds")}
  bind,_:=world(r,0,false)
  now,_:=world(r,at,true)
  out:=make([][3]float64,len(r.Vertices))
  for k,v:=range r.Vertices{
    for a:=0;a<2;a++{
      j:=v.IDs[a]
      for dim:=0;dim<3;dim++{out[k][dim]+=v.W[a]*(v.Pos[dim]+now[j][dim]-bind[j][dim])}
    }
  }
  return out,nil
}
func syntheticFixture()Rig{
  r:=Rig{
    Joints:[]Joint{
      {Parent:-1,Rest:[3]float64{0,0,0}},
      {Parent:0,Rest:[3]float64{1,0,0}},
      {Parent:1,Rest:[3]float64{.6,.3,0}},
    },
    Vertices:[]Vertex{
      {Pos:[3]float64{0,0,0},IDs:[2]int{0,1},W:[2]float64{1,0}},
      {Pos:[3]float64{.8,0,0},IDs:[2]int{0,1},W:[2]float64{.25,.75}},
      {Pos:[3]float64{1.5,.3,0},IDs:[2]int{1,2},W:[2]float64{.4,.6}},
    },
  }
  for i:=0;i<3;i++{
    r.Frames=append(r.Frames,Pose{
      TimeMS:i*1000,
      Delta:[][3]float64{{0,0,0},{0,.1*float64(i),0},{.05*float64(i),0,0}},
      Visible:[]bool{true,true,true},
    })
  }
  return r
}
func syntheticReceipt()(SkinReport,error){
  r:=syntheticFixture()
  if err:=validateRig(r);err!=nil{return SkinReport{},err}
  first,_:=deform(r,0)
  last,_:=deform(r,len(r.Frames)-1)
  maxDisp:=0.0
  for i:=range first{
    var sum float64
    for k:=0;k<3;k++{d:=last[i][k]-first[i][k];sum+=d*d}
    maxDisp=math.Max(maxDisp,math.Sqrt(sum))
  }
  if maxDisp<.01{return SkinReport{},errors.New("synthetic skin does not deform")}
  receipt:=SkinReport{
    Classification:"SYNTHETIC_CPU_TRANSLATION_SKIN_NOT_BLENDER_OR_MODEL",
    JointCount:len(r.Joints),VertexCount:len(r.Vertices),Frames:len(r.Frames),
    MaxVertexDisplacement:maxDisp,
  }
  for _,f:=range r.Frames{receipt.SourceClockMS=append(receipt.SourceClockMS,f.TimeMS)}
  return receipt,nil
}
func execute(lane string,input []byte)(Receipt,error){
  var r Registry
  if err:=json.Unmarshal(input,&r);err!=nil{return Receipt{},err}
  if err:=validRegistry(r);err!=nil{return Receipt{},err}
  h:=sha256.Sum256(input)
  out:=Receipt{
    Schema:"stable-character/r4-parallel-lane/1",Lane:lane,
    Status:"PASS_SOURCE_ONLY_NO_MODEL_INFERENCE",RegistrySHA256:fmt.Sprintf("%x",h),
    SourceOnly:true,ActualModelInferences:0,WeightsDownloaded:0,GPURuns:0,
    NextGate:"PER_FILE_WEIGHT_RIGHTS_UPSTREAM_SOURCE_SHA_AND_SEPARATE_MODEL_EXECUTION_ADMISSION",
  }
  switch lane{
  case "rights":
    out.Candidates=len(r.Candidates)
  case "adapters":
    adapters,err:=contracts(r);if err!=nil{return Receipt{},err}
    out.Candidates=len(adapters)
    out.Contracts=adapters
  case "synthetic":
    rig,err:=syntheticReceipt();if err!=nil{return Receipt{},err}
    out.Synthetic=&rig
  default:
    return Receipt{},fmt.Errorf("unadmitted parallel lane %q",lane)
  }
  return out,nil
}
func main(){
  lane:=flag.String("lane","","rights/adapters/synthetic public-source-only lane")
  manifest:=flag.String("manifest","qualification/r4_admission/candidates.json","reviewed public-source registry")
  out:=flag.String("out","r4-lane-receipt.json","unique per-lane JSON")
  flag.Parse()
  b,err:=os.ReadFile(*manifest)
  if err!=nil{fmt.Fprintln(os.Stderr,"R4_LANE_FAIL:",err);os.Exit(4)}
  r,err:=execute(*lane,b)
  if err!=nil{fmt.Fprintln(os.Stderr,"R4_LANE_FAIL:",err);os.Exit(4)}
  b,err=json.MarshalIndent(r,"","  ")
  if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(4)}
  if err:=os.WriteFile(*out,append(b,10),0644);err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(4)}
  fmt.Println(string(b))
}
