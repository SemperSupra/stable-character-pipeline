// Package jointmap provides a falsifiable source-safe structural contract for
// comparing 127 MHR native joints to 126 imported Blender bones. This does
// NOT prove that one native joint really is omitted in the real asset.
package jointmap

import (
 "bytes"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "math"
)

const Schema = "r014.mhr_jointmap_candidate.v1"
type V3 [3]float64
type Joint struct {
 ID string `json:"id"`
 Parent string `json:"parent"`
 Side string `json:"side"`
 Deforming bool `json:"deforming"`
 RestWorld V3 `json:"rest_world"`
}
type Rig struct {
 SHA256 string `json:"source_sha256"`
 PoseSpace string `json:"pose_space"`
 Joints []Joint `json:"joints"`
}
type Pair struct {
 Native string `json:"native"`
 Blender string `json:"blender"`
}
type Omission struct {
 Native string `json:"native"`
 Explanation string `json:"explanation"`
}
type Alignment struct {
 Rotation [9]float64 `json:"source_to_target_rotation_row_major"`
 Scale float64 `json:"source_to_target_scale"`
 Translation V3 `json:"source_to_target_translation"`
 MaxError float64 `json:"maximum_rest_position_residual"`
}
type Plan struct {
 Schema string `json:"schema"`
 Native Rig `json:"native"`
 Blender Rig `json:"blender"`
 Pairs []Pair `json:"pairs"`
 Omission Omission `json:"omission"`
 Alignment Alignment `json:"alignment"`
 SourceRights string `json:"source_rights"`
}
// Influence is a per-joint LBS metadata summary, never source vertices or weights.
 // The independent extractor must count truly nonzero source weight entries.
type Influence struct {
 JointID string `json:"joint_id"`
 NonzeroVertices int `json:"nonzero_vertices"`
 MaxAbsoluteWeight float64 `json:"max_absolute_weight"`
 SumAbsoluteWeight float64 `json:"sum_absolute_weight"`
}
type LBSWitness struct {
 NativeSHA256 string `json:"native_sha256"`
 LOD int `json:"lod"`
 VertexCount int `json:"vertex_count"`
 Joints []Influence `json:"joints"`
}
type Trust struct {
 NativeSHA256 string
 BlenderSHA256 string
 PairMapSHA256 string
 AlignmentSHA256 string
 AlignmentReviewSHA256 string
 MaxTrustedRestError float64
 OmittedID string
 OmissionReviewSHA256 string
 MapReviewed bool
 LBS LBSWitness
 LBSWitnessSHA256 string
 LBSReviewSHA256 string
}
type Result struct {
 Schema string `json:"schema"`
 Status string `json:"status"`
 Matched int `json:"matched"`
 Native int `json:"native_count"`
 Blender int `json:"blender_count"`
 MaxRestError float64 `json:"maximum_observed_rest_position_residual"`
 ActualNativeRuntime string `json:"actual_native_mhr_runtime"`
 CorrectivesParity string `json:"correctives_parity"`
 MotionQuality string `json:"motion_quality"`
 CanonicalCharacterPack string `json:"canonical_character_pack"`
}
func status() Result {
 return Result{
 Schema:"r014.mhr_jointmap_diagnostic.v1",
 Status:"UNKNOWN_UNQUALIFIED_SOURCE_AND_JOINT_SEMANTICS",
 ActualNativeRuntime:"NOT_RUN",
 CorrectivesParity:"HOLD_NOT_EVALUATED",
 MotionQuality:"HOLD_KNEE_ANKLE_CONTACT_SKIN",
 CanonicalCharacterPack:"HOLD_OWNER_HUMAN_ONLY",
 }
}
func digest(s string)bool{
 if len(s)!=64{return false}
 b,e:=hex.DecodeString(s)
 return e==nil&&len(b)==32
}
func finite(x float64)bool{return !math.IsNaN(x)&&!math.IsInf(x,0)}
func finiteV(v V3)bool{return finite(v[0])&&finite(v[1])&&finite(v[2])}
func DecodeStrict(b []byte)(Plan,error){
 var p Plan
 d:=json.NewDecoder(bytes.NewReader(b))
 d.DisallowUnknownFields()
 if e:=d.Decode(&p);e!=nil{return p,e}
 var tail any
 if e:=d.Decode(&tail);e!=io.EOF{return p,errors.New("trailing records or extra JSON")}
 return p,nil
}
func indexed(r Rig,n int)(map[string]Joint,error){
 if len(r.Joints)!=n{return nil,fmt.Errorf("expected %d source joints, got %d",n,len(r.Joints))}
 j:=map[string]Joint{}
 roots:=0
 for _,x:=range r.Joints{
  if x.ID==""||!finiteV(x.RestWorld){return nil,errors.New("invalid joint ID or nonfinite rest location")}
  if _,yes:=j[x.ID];yes{return nil,fmt.Errorf("duplicate joint %q",x.ID)}
  if x.Side!="left"&&x.Side!="right"&&x.Side!="center"{
   return nil,fmt.Errorf("joint %q lacks explicit side",x.ID)
  }
  if x.ID==x.Parent{return nil,errors.New("joint is its own parent")}
  if x.Parent==""{roots++}
  j[x.ID]=x
 }
 if roots!=1{return nil,fmt.Errorf("expected one root got %d",roots)}
 for id,x:=range j{
  visited:=map[string]bool{id:true}
  parent:=x.Parent
  for parent!=""{
   a,yes:=j[parent]
   if !yes{return nil,fmt.Errorf("missing ancestor %q",parent)}
   if visited[parent]{return nil,fmt.Errorf("cycle involving %q",parent)}
   visited[parent]=true
   if len(visited)>len(j){return nil,errors.New("unbounded ancestry")}
   parent=a.Parent
  }
 }
 return j,nil
}
func determinant(m [9]float64)float64{
 return m[0]*(m[4]*m[8]-m[5]*m[7])-m[1]*(m[3]*m[8]-m[5]*m[6])+m[2]*(m[3]*m[7]-m[4]*m[6])
}
func rotationOK(m [9]float64)bool{
 for _,x:=range m{if !finite(x){return false}}
 for i:=0;i<3;i++{for j:=0;j<3;j++{
  dot:=0.0
  for k:=0;k<3;k++{dot+=m[3*i+k]*m[3*j+k]}
  target:=0.0;if i==j{target=1}
  if math.Abs(dot-target)>1e-7{return false}
 }}
 return math.Abs(determinant(m)-1)<=1e-7
}
func transform(v V3,a Alignment)V3{
 var x V3
 for i:=0;i<3;i++{
  x[i]=a.Translation[i]+a.Scale*(a.Rotation[i*3]*v[0]+a.Rotation[i*3+1]*v[1]+a.Rotation[i*3+2]*v[2])
 }
 return x
}
func distance(a,b V3)float64{
 return math.Sqrt(math.Pow(a[0]-b[0],2)+math.Pow(a[1]-b[1],2)+math.Pow(a[2]-b[2],2))
}
// PairMapDigest binds the exact candidate pairs, omitted-joint reason and
// admitted source snapshot identifiers. It is NOT proof of human review.
func PairMapDigest(p Plan)string{
 b,_:=json.Marshal(struct{
  NativeSHA string `json:"native_sha"`
  BlenderSHA string `json:"blender_sha"`
  Pairs []Pair `json:"pairs"`
  Omission Omission `json:"omission"`
 }{p.Native.SHA256,p.Blender.SHA256,p.Pairs,p.Omission})
 sum:=sha256.Sum256(b)
 return hex.EncodeToString(sum[:])
}
// InfluenceDigest canonically binds the LOD, native-source hash and all
// per-joint source LBS weight summaries. This is a digest, NOT reviewer identity.
func InfluenceDigest(w LBSWitness)string{
 b,_:=json.Marshal(w)
 sum:=sha256.Sum256(b)
 return hex.EncodeToString(sum[:])
}
func validateInfluences(w LBSWitness,t Trust,n map[string]Joint,omittedID string)error{
 if w.NativeSHA256!=t.NativeSHA256||w.LOD!=1||
  w.VertexCount<=0||len(w.Joints)!=127||
  !digest(t.LBSReviewSHA256)||!digest(t.LBSWitnessSHA256)||
  t.LBSWitnessSHA256!=InfluenceDigest(w){
  return errors.New("independent source LOD1 LBS influence proof missing")
 }
 seen:=map[string]bool{}
 for _,entry:=range w.Joints{
  joint,ok:=n[entry.JointID]
  if !ok||seen[entry.JointID]{return fmt.Errorf("duplicate or unknown LBS joint %q",entry.JointID)}
  seen[entry.JointID]=true
  if entry.NonzeroVertices<0||entry.NonzeroVertices>w.VertexCount||
   !finite(entry.MaxAbsoluteWeight)||!finite(entry.SumAbsoluteWeight)||
   entry.MaxAbsoluteWeight<0||entry.MaxAbsoluteWeight>1||
   entry.SumAbsoluteWeight<0||
   entry.SumAbsoluteWeight>float64(entry.NonzeroVertices)+1e-9{
   return fmt.Errorf("invalid LBS weight statistics for %q",entry.JointID)
  }
  if entry.NonzeroVertices==0 {
   if entry.MaxAbsoluteWeight!=0||entry.SumAbsoluteWeight!=0{
    return fmt.Errorf("zero-influence joint %q has nonzero LBS weights",entry.JointID)
   }
  } else if entry.MaxAbsoluteWeight<=0||
    entry.SumAbsoluteWeight<entry.MaxAbsoluteWeight||
    !joint.Deforming{
   return fmt.Errorf("nonzero-LBS joint %q incorrectly classified or bounded",entry.JointID)
  }
  if entry.JointID==omittedID&&entry.NonzeroVertices!=0{
   return errors.New("omitted native joint has positive LBS vertex influence")
  }
 }
 if len(seen)!=len(n){return errors.New("incomplete LBS joint census")}
 return nil
}
// AlignmentDigest binds the exact proposed coordinate calibration to the
// independent review context; this is not an actual native rig proof.
func AlignmentDigest(a Alignment)string{
 b,_:=json.Marshal(a)
 sum:=sha256.Sum256(b)
 return hex.EncodeToString(sum[:])
}
func Validate(p Plan,t Trust)(Result,error){
 r:=status()
 if p.Schema!=Schema{return r,errors.New("unsupported schema")}
 if !digest(p.Native.SHA256)||!digest(p.Blender.SHA256)||
  !digest(t.NativeSHA256)||!digest(t.BlenderSHA256)||
  p.Native.SHA256!=t.NativeSHA256||p.Blender.SHA256!=t.BlenderSHA256{
  return r,errors.New("source-native/imported scene evidence not admitted by independent registry")
 }
 if p.Native.PoseSpace!="MHR_LOCAL_JOINT"||p.Blender.PoseSpace!="BLENDER_IMPORTED_BONE_LOCAL"{
  return r,errors.New("unspecified or mismatched pose-space contract")
 }
 if p.SourceRights!="REVIEW_REQUIRED_NO_PERMISSION_INFERRED"{
  return r,errors.New("source rights cannot be granted by mapping plan")
 }
 if !t.MapReviewed||!digest(t.PairMapSHA256)||t.PairMapSHA256!=PairMapDigest(p)||!digest(t.OmissionReviewSHA256)||
  t.OmittedID!=p.Omission.Native||p.Omission.Explanation==""{
  return r,errors.New("independent mapping/omission review not admitted")
 }
 if !digest(t.AlignmentSHA256)||t.AlignmentSHA256!=AlignmentDigest(p.Alignment)||
  !digest(t.AlignmentReviewSHA256)||!finite(t.MaxTrustedRestError)||
  t.MaxTrustedRestError<=0||p.Alignment.MaxError>t.MaxTrustedRestError{
  return r,errors.New("independently reviewed coordinate calibration or rest threshold missing")
 }
 if !rotationOK(p.Alignment.Rotation)||!finite(p.Alignment.Scale)||
  p.Alignment.Scale<=0||!finiteV(p.Alignment.Translation)||
  !finite(p.Alignment.MaxError)||p.Alignment.MaxError<=0||
  p.Alignment.MaxError>0.01{
  return r,errors.New("nonrigid, reflected or uncalibrated alignment")
 }
 n,e:=indexed(p.Native,127);if e!=nil{return r,e}
 b,e:=indexed(p.Blender,126);if e!=nil{return r,e}
 omitted,ok:=n[p.Omission.Native]
 if !ok||omitted.Deforming{return r,errors.New("omitted source joint absent or flagged deforming")}
 if e:=validateInfluences(t.LBS,t,n,p.Omission.Native);e!=nil{return r,e}
 if len(p.Pairs)!=126{return r,errors.New("not a 126-pair candidate bijection")}
 usedN,usedB:=map[string]bool{},map[string]bool{}
 pairMap:=map[string]string{}
 for _,pair:=range p.Pairs{
  jn,nok:=n[pair.Native];jb,bok:=b[pair.Blender]
  if !nok||!bok||pair.Native==p.Omission.Native||
   usedN[pair.Native]||usedB[pair.Blender]{
   return r,errors.New("duplicate, unmapped, or omitted pair")
  }
  if jn.Side!=jb.Side{return r,fmt.Errorf("side-inconsistent pair %q/%q",pair.Native,pair.Blender)}
  usedN[pair.Native]=true;usedB[pair.Blender]=true;pairMap[pair.Native]=pair.Blender
 }
 if len(usedN)!=126||len(usedB)!=126{return r,errors.New("incomplete pairing")}
 for _,pair:=range p.Pairs{
  jn:=n[pair.Native];jb:=b[pair.Blender]
  parent:=jn.Parent
  if parent==p.Omission.Native{parent=omitted.Parent}
  expected:=""
  if parent!=""{
   var has bool
   expected,has=pairMap[parent]
   if !has{return r,errors.New("unmapped non-omitted ancestor")}
  }
  if jb.Parent!=expected{return r,fmt.Errorf("parent edge mismatch at %q",pair.Native)}
  err:=distance(transform(jn.RestWorld,p.Alignment),jb.RestWorld)
  if !finite(err)||err>p.Alignment.MaxError{
   return r,fmt.Errorf("rest transform residual %.9g at %q exceeds bound",err,pair.Native)
  }
  if err>r.MaxRestError{r.MaxRestError=err}
 }
 r.Native=len(n);r.Blender=len(b);r.Matched=len(usedN)
 r.Status="PASS_SYNTHETIC_STRUCTURAL_ONLY__REAL_RIG_PARITY_UNKNOWN"
 return r,nil
}
