// Package landmarks qualifies paired, lateralized anatomical fiducial contracts.
// It does not perform human landmark detection, biological fitting, or medical QA.
package landmarks

import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "math"
 "sort"
 "strings"
)

const Schema="scp.anatomy.registration.landmarks.v1"
type Point struct{ X float64 `json:"x_m"`;Y float64 `json:"y_m"`;Z float64 `json:"z_m"` }
type Pair struct{
 ID string `json:"id"`
 Source Point `json:"source"`
 Target Point `json:"target"`
 SourceUncertaintyM float64 `json:"source_uncertainty_m"`
 TargetUncertaintyM float64 `json:"target_uncertainty_m"`
 SourceEvidence string `json:"source_evidence"`
 TargetEvidence string `json:"target_evidence"`
}
type Pack struct{
 Schema string `json:"schema"`
 SourceAtlas string `json:"source_atlas"`
 SourceSHA256 string `json:"source_sha256"`
 TargetCharacter string `json:"target_character"`
 TargetSHA256 string `json:"target_sha256"`
 SourceFrame string `json:"source_frame"`
 TargetFrame string `json:"target_frame"`
 Units string `json:"units"`
 Transform [4][4]float64 `json:"source_to_target_4x4"`
 Pairs []Pair `json:"fiducials"`
}
type LandmarkError struct{ID string `json:"id"`; DistanceM float64 `json:"distance_m"`;SigmaMultiple float64 `json:"sigma_multiple"`}
type Receipt struct{
 Schema string `json:"schema"`
 Status string `json:"status"`
 SourceAtlas string `json:"source_atlas"`
 TargetCharacter string `json:"target_character"`
 SourceSHA256 string `json:"source_sha256"`
 TargetSHA256 string `json:"target_sha256"`
 FiducialCount int `json:"fiducial_count"`
 MaxResidualM float64 `json:"max_residual_m"`
 P95ResidualM float64 `json:"p95_residual_m"`
 MaxSigmaMultiple float64 `json:"max_sigma_multiple"`
 ProperDeterminant float64 `json:"proper_determinant"`
 UniformScale float64 `json:"uniform_scale"`
 LateralityConsistency bool `json:"laterality_consistency"`
 AnteriorPosteriorConsistency bool `json:"anterior_posterior_consistency"`
 Errors []LandmarkError `json:"errors"`
 Missing []string `json:"missing"`
 Caveat string `json:"caveat"`
}
var required=[]string{
 "clavicle_left","clavicle_right","iliac_crest_left","iliac_crest_right",
 "sternal_notch","spinous_t7","head_top","sacrum",
}
func finite(x float64)bool{return !math.IsNaN(x)&&!math.IsInf(x,0)}
func pointFinite(p Point)bool{return finite(p.X)&&finite(p.Y)&&finite(p.Z)}
func sub(a,b Point)Point{return Point{a.X-b.X,a.Y-b.Y,a.Z-b.Z}}
func dot(a,b Point)float64{return a.X*b.X+a.Y*b.Y+a.Z*b.Z}
func norm(p Point)float64{return math.Sqrt(dot(p,p))}
func cross(a,b Point)Point{return Point{a.Y*b.Z-a.Z*b.Y,a.Z*b.X-a.X*b.Z,a.X*b.Y-a.Y*b.X}}
func matDet(m [4][4]float64)float64{
 a,b,c:=Point{m[0][0],m[1][0],m[2][0]},Point{m[0][1],m[1][1],m[2][1]},Point{m[0][2],m[1][2],m[2][2]}
 return dot(a,cross(b,c))
}
func apply(m [4][4]float64,p Point)Point{return Point{
 m[0][0]*p.X+m[0][1]*p.Y+m[0][2]*p.Z+m[0][3],
 m[1][0]*p.X+m[1][1]*p.Y+m[1][2]*p.Z+m[1][3],
 m[2][0]*p.X+m[2][1]*p.Y+m[2][2]*p.Z+m[2][3],
}}
func sha(s string)bool{
 if len(s)!=64{return false}
 for _,c:=range s{if !strings.ContainsRune("0123456789abcdef",c){return false}}
 return true
}
func matrixValid(m [4][4]float64)(float64,float64,error){
 for i:=range m{for _,v:=range m[i]{if !finite(v){return 0,0,errors.New("NONFINITE_TRANSFORM")}}}
 if math.Abs(m[3][0])+math.Abs(m[3][1])+math.Abs(m[3][2])+math.Abs(m[3][3]-1)>1e-8{return 0,0,errors.New("INVALID_HOMOGENEOUS_MATRIX")}
 cols:=[3]Point{{m[0][0],m[1][0],m[2][0]},{m[0][1],m[1][1],m[2][1]},{m[0][2],m[1][2],m[2][2]}}
 lengths:=[3]float64{norm(cols[0]),norm(cols[1]),norm(cols[2])}
 scale:=(lengths[0]+lengths[1]+lengths[2])/3
 if scale<0.05||scale>20{return 0,0,errors.New("UNREASONABLE_OR_ZERO_SCALE")}
 for _,n:=range lengths{if math.Abs(n-scale)>scale*1e-5{return 0,0,errors.New("NONUNIFORM_SCALE_OR_SHEAR")}}
 for i:=0;i<3;i++{for j:=i+1;j<3;j++{if math.Abs(dot(cols[i],cols[j]))>scale*scale*1e-5{return 0,0,errors.New("SHEAR_OR_NONORTHOGONAL")}}}
 determinant:=matDet(m)
 if determinant<=0{return 0,0,errors.New("REFLECTION_NOT_A_PROPER_ANATOMICAL_FRAME")}
 if math.Abs(determinant-scale*scale*scale)>scale*scale*scale*1e-5{return 0,0,errors.New("DETERMINANT_INCONSISTENT_WITH_SCALE")}
 return determinant,scale,nil
}
func find(m map[string]Pair,id string) Pair{return m[id]}
func pairDirection(m map[string]Pair,l,r string,fromSource bool)Point{
 left,right:=find(m,l),find(m,r)
 if fromSource{return sub(left.Source,right.Source)}
 return sub(left.Target,right.Target)
}
func sideConsistent(m map[string]Pair,tx [4][4]float64)bool{
 for _,pair:=range [][2]string{{"clavicle_left","clavicle_right"},{"iliac_crest_left","iliac_crest_right"}}{
  src:=pairDirection(m,pair[0],pair[1],true)
  target:=pairDirection(m,pair[0],pair[1],false)
  if norm(src)<.05||norm(target)<.05{return false}
  transformed:=sub(apply(tx,Point{src.X,src.Y,src.Z}),apply(tx,Point{}))
  if dot(transformed,target)/(norm(transformed)*norm(target))<0.5{return false}
 }
 return true
}
func anteriorConsistent(m map[string]Pair,tx [4][4]float64)bool{
 a,b:=m["sternal_notch"],m["spinous_t7"]
 src:=sub(a.Source,b.Source)
 target:=sub(a.Target,b.Target)
 if norm(src)<.03||norm(target)<.03{return false}
 transformed:=sub(apply(tx,src),apply(tx,Point{}))
 return dot(transformed,target)/(norm(transformed)*norm(target))>=0.5
}
func noncoplanar(m map[string]Pair,source bool)bool{
 pick:=func(id string)Point{p:=m[id];if source{return p.Source};return p.Target}
 root:=pick("sacrum")
 a:=sub(pick("clavicle_left"),root)
 b:=sub(pick("clavicle_right"),root)
 c:=sub(pick("sternal_notch"),root)
 return math.Abs(dot(a,cross(b,c)))>1e-5
}
func Evaluate(pack Pack)(Receipt,error){
 r:=Receipt{Schema:Schema,Status:"HOLD_MISSING_OR_INVALID_FIDUCIALS",
  SourceAtlas:pack.SourceAtlas,TargetCharacter:pack.TargetCharacter,
  SourceSHA256:pack.SourceSHA256,TargetSHA256:pack.TargetSHA256,
  FiducialCount:len(pack.Pairs),Errors:[]LandmarkError{},Missing:[]string{},
  Caveat:"Landmark geometry and provenance only. No automatic medical, physical, visual or anatomical registration acceptance."}
 if pack.Schema!=Schema||pack.SourceAtlas==""||pack.TargetCharacter==""||
 !sha(pack.SourceSHA256)||!sha(pack.TargetSHA256)||
 pack.SourceFrame==""||pack.TargetFrame==""||pack.Units!="m"{
  return r,errors.New("INVALID_SOURCE_PROVENANCE_OR_FRAME")
 }
 det,scale,err:=matrixValid(pack.Transform)
 if err!=nil{return r,err}
 r.ProperDeterminant=det;r.UniformScale=scale
 byID:=map[string]Pair{}
 for _,p:=range pack.Pairs{
  if p.ID==""||!pointFinite(p.Source)||!pointFinite(p.Target)||
    !finite(p.SourceUncertaintyM)||!finite(p.TargetUncertaintyM)||
    p.SourceUncertaintyM<=0||p.TargetUncertaintyM<=0||
    p.SourceUncertaintyM>.20||p.TargetUncertaintyM>.20||
    !sha(p.SourceEvidence)||!sha(p.TargetEvidence){
   return r,errors.New("INVALID_LANDMARK_OR_UNCERTAINTY_PROVENANCE")
  }
  if _,ok:=byID[p.ID];ok{return r,errors.New("DUPLICATE_LANDMARK_ID")}
  byID[p.ID]=p
 }
 for _,id:=range required{if _,ok:=byID[id];!ok{r.Missing=append(r.Missing,id)}}
 if len(r.Missing)>0{return r,nil}
 if !noncoplanar(byID,true)||!noncoplanar(byID,false){return r,errors.New("DEGENERATE_OR_COPLANAR_FIDUCIALS")}
 r.LateralityConsistency=sideConsistent(byID,pack.Transform)
 r.AnteriorPosteriorConsistency=anteriorConsistent(byID,pack.Transform)
 if !r.LateralityConsistency||!r.AnteriorPosteriorConsistency{return r,errors.New("LATERALITY_OR_ANTERIOR_MISMATCH")}
 errorsList:=[]float64{}
 sigmaMax:=0.0
 for _,p:=range pack.Pairs{
  residual:=norm(sub(apply(pack.Transform,p.Source),p.Target))
  uncertainty:=math.Hypot(scale*p.SourceUncertaintyM,p.TargetUncertaintyM)
  sig:=residual/uncertainty
  r.Errors=append(r.Errors,LandmarkError{p.ID,residual,sig})
  errorsList=append(errorsList,residual)
  if sig>sigmaMax{sigmaMax=sig}
 }
 sort.Float64s(errorsList)
 r.MaxResidualM=errorsList[len(errorsList)-1]
 r.P95ResidualM=errorsList[int(math.Ceil(float64(len(errorsList))*.95))-1]
 r.MaxSigmaMultiple=sigmaMax
 if r.P95ResidualM>.02||sigmaMax>3{
  r.Status="HOLD_LANDMARK_GEOMETRY_RESIDUAL"
 }else{
  r.Status="MECHANICAL_CORRESPONDENCE_ONLY_INDEPENDENT_ANATOMY_REVIEW_REQUIRED"
 }
 return r,nil
}
func Fingerprint(pack Pack)(string,error){
 if _,e:=Evaluate(pack);e!=nil{return "",e}
 data,err:=json.Marshal(pack);if err!=nil{return "",err}
 hash:=sha256.Sum256(data)
 return hex.EncodeToString(hash[:]),nil
}
