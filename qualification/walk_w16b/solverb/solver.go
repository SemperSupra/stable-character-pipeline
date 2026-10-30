package solverb

// Self-authored 3D two-segment pole-vector IK and quaternion geometry.
// Reference concepts: Ozz IKTwoBoneJob, glTF XYZW rotation, three.js CCDIK.
// No external source/code copied. No real-person data or anatomical claims.
import (
 "errors"
 "math"
)
const eps=1e-10
type V [3]float64
type Q [4]float64 // normalized XYZW by public glTF convention
func finite(x float64)bool{return !math.IsNaN(x)&&!math.IsInf(x,0)}
func (a V) Add(b V)V{return V{a[0]+b[0],a[1]+b[1],a[2]+b[2]}}
func (a V) Sub(b V)V{return V{a[0]-b[0],a[1]-b[1],a[2]-b[2]}}
func (a V) Mul(n float64)V{return V{a[0]*n,a[1]*n,a[2]*n}}
func dot(a,b V)float64{return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]}
func cross(a,b V)V{return V{a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]}}
func norm(a V)float64{return math.Sqrt(dot(a,a))}
func unit(a V)(V,error){n:=norm(a);if !finite(n)||n<eps{return V{},errors.New("ZERO_OR_NONFINITE_VECTOR")};return a.Mul(1/n),nil}
func quatBetween(from,to V)(Q,error){
 u,e:=unit(from);if e!=nil{return Q{},e}
 v,e:=unit(to);if e!=nil{return Q{},e}
 c:=math.Max(-1,math.Min(1,dot(u,v)))
 if c>1-1e-12{return Q{0,0,0,1},nil}
 if c< -1+1e-12{
  // Deterministically select axis least aligned with from.
  basis:=V{1,0,0};if math.Abs(u[0])>.9{basis=V{0,0,1}}
  axis,e:=unit(cross(u,basis));if e!=nil{return Q{},e}
  return Q{axis[0],axis[1],axis[2],0},nil
 }
 axis:=cross(u,v)
 q:=Q{axis[0],axis[1],axis[2],1+c}
 n:=math.Sqrt(q[0]*q[0]+q[1]*q[1]+q[2]*q[2]+q[3]*q[3])
 for i:=range q{q[i]/=n}
 return q,nil
}
func rotate(q Q,v V)V{
 // q * vector * conjugate using XYZW; 2*cross(qv,cross(qv,v)+w*v).
 xyz:=V{q[0],q[1],q[2]}
 t:=cross(xyz,v).Mul(2)
 return v.Add(t.Mul(q[3])).Add(cross(xyz,t))
}
func qnormalize(q Q)(Q,error){
 n:=0.0;for _,x:=range q{if !finite(x){return Q{},errors.New("NONFINITE_QUATERNION")};n+=x*x}
 if n<eps{return Q{},errors.New("ZERO_QUATERNION")}
 n=math.Sqrt(n)
 for i:=range q{q[i]/=n}
 return q,nil
}
func qangular(a,b Q)(float64,error){
 qa,e:=qnormalize(a);if e!=nil{return 0,e}
 qb,e:=qnormalize(b);if e!=nil{return 0,e}
 dotq:=0.0;for i:=range qa{dotq+=qa[i]*qb[i]}
 return 2*math.Acos(math.Min(1,math.Abs(dotq))),nil
}
type Input struct{
 Schema string `json:"schema"`
 Rights string `json:"source_rights"`
 Profile string `json:"profile"`
 Hip V `json:"hip"`
 Ankle V `json:"ankle"`
 Pole V `json:"pole"`
 Thigh float64 `json:"thigh"`
 Shin float64 `json:"shin"`
}
type Result struct{
 Schema string `json:"schema"`
 Profile string `json:"profile"`
 Status string `json:"status"`
 Hip V `json:"hip"`
 Knee V `json:"knee"`
 Ankle V `json:"ankle"`
 UpperLocalQuat Q `json:"upper_quat_xyzw"`
 LowerLocalQuat Q `json:"lower_quat_xyzw"`
 PoleUnit V `json:"pole_unit"`
 FKUpperError float64 `json:"upper_fk_error"`
 FKLowerError float64 `json:"lower_fk_error"`
 LengthError float64 `json:"length_residual"`
 Reachable bool `json:"reachable"`
 Scope string `json:"scope"`
}
func solve(i Input)(Result,error){
 if i.Schema!="scp.walk_3d_ik_synthetic.v1"||i.Rights!="ORIGINAL_PROGRAMMATIC_PROCEDURAL_ONLY"||!(i.Profile=="forward"||i.Profile=="outward"){return Result{},errors.New("INVALID_SOURCE_OR_PROFILE")}
 if !finite(i.Thigh)||!finite(i.Shin)||i.Thigh<=0||i.Shin<=0{return Result{},errors.New("INVALID_SEGMENTS")}
 delta:=i.Ankle.Sub(i.Hip);distance:=norm(delta)
 if !finite(distance)||distance<=math.Abs(i.Thigh-i.Shin)+1e-8||distance>=i.Thigh+i.Shin-1e-8{return Result{},errors.New("UNREACHABLE_IK")}
 axis,e:=unit(delta);if e!=nil{return Result{},e}
 poleProjection:=i.Pole.Sub(axis.Mul(dot(i.Pole,axis)))
 pole,e:=unit(poleProjection);if e!=nil{return Result{},errors.New("DEGENERATE_POLE")}
 along:=(i.Thigh*i.Thigh-i.Shin*i.Shin+distance*distance)/(2*distance)
 perpendicular:=math.Sqrt(math.Max(0,i.Thigh*i.Thigh-along*along))
 knee:=i.Hip.Add(axis.Mul(along)).Add(pole.Mul(perpendicular))
 upper:=knee.Sub(i.Hip);lower:=i.Ankle.Sub(knee)
 qu,e:=quatBetween(V{0,-1,0},upper);if e!=nil{return Result{},e}
 ql,e:=quatBetween(V{0,-1,0},lower);if e!=nil{return Result{},e}
 upperFK:=rotate(qu,V{0,-i.Thigh,0})
 lowerFK:=rotate(ql,V{0,-i.Shin,0})
 ue:=norm(upperFK.Sub(upper));le:=norm(lowerFK.Sub(lower))
 resid:=math.Max(math.Abs(norm(upper)-i.Thigh),math.Abs(norm(lower)-i.Shin))
 if ue>1e-9||le>1e-9||resid>1e-9{return Result{},errors.New("QUATERNION_FK_OR_SEGMENT_MISMATCH")}
 return Result{Schema:"scp.walk_3d_ik_result.v1",Profile:i.Profile,Status:"PASS_ORIGINAL_3D_POLE_IK_QUATERNION",Hip:i.Hip,Knee:knee,Ankle:i.Ankle,UpperLocalQuat:qu,LowerLocalQuat:ql,PoleUnit:pole,FKUpperError:ue,FKLowerError:le,LengthError:resid,Reachable:true,Scope:"UNCALIBRATED_SELF_AUTHORED_3D_IK_NOT_PRIVATE_NOT_SKIN"},nil
}
func canonicalInput(profile string)Input{
 pole:=V{0,0,1};if profile=="outward"{pole=V{1,0,0}}
 return Input{Schema:"scp.walk_3d_ik_synthetic.v1",Rights:"ORIGINAL_PROGRAMMATIC_PROCEDURAL_ONLY",Profile:profile,Hip:V{0,1.3,0},Ankle:V{.20,.14,.08},Pole:pole,Thigh:.70,Shin:.60}
}
func Solve(i Input)(Result,error){return solve(i)}
