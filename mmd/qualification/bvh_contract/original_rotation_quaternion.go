package bvh

// Original-authored synthetic BVH rotation-order qualification and explicit
// 60Hz-to-30Hz quaternion sample-loss projection. SOURCE-LOCAL math only:
// not a physical MMD/PMX retarget, Blender pose, or human ROM model.
import (
	"errors"
	"math"
	"strings"
)

type QuaternionXYZW [4]float64

type OriginalSyntheticRotationKey struct {
	Name string
	SourceFrame int
	TargetFrame int
	Parent int
	LocalXYZW QuaternionXYZW
	WorldXYZW QuaternionXYZW
}

type OriginalSyntheticRotationLoss struct {
	Schema string
	SourceFPS int
	TargetFPS int
	SourceFrames int
	TargetFrames int
	SourceFrameOne string
	Keyframes []OriginalSyntheticRotationKey
	HumanROM string
	PhysicalRetarget string
	ProtectedR009 string
}

func qUnit(q QuaternionXYZW) (QuaternionXYZW,error) {
	n:=0.
	for _,x:=range q { if math.IsNaN(x)||math.IsInf(x,0){return q,errors.New("NONFINITE_SOURCE_ROTATION")};n+=x*x }
	if n<1e-12{return q,errors.New("DEGENERATE_QUATERNION")}
	n=math.Sqrt(n)
	for i:=range q {q[i]/=n}
	return q,nil
}
func qMul(a,b QuaternionXYZW) QuaternionXYZW {
	return QuaternionXYZW{
		a[3]*b[0]+a[0]*b[3]+a[1]*b[2]-a[2]*b[1],
		a[3]*b[1]-a[0]*b[2]+a[1]*b[3]+a[2]*b[0],
		a[3]*b[2]+a[0]*b[1]-a[1]*b[0]+a[2]*b[3],
		a[3]*b[3]-a[0]*b[0]-a[1]*b[1]-a[2]*b[2],
	}
}
func qAxis(axis byte,deg float64)(QuaternionXYZW,error){
	if math.IsNaN(deg)||math.IsInf(deg,0)||math.Abs(deg)>36000{return QuaternionXYZW{},errors.New("NONFINITE_OR_EXCESSIVE_SOURCE_DEGREES")}
	s,c:=math.Sincos(deg*math.Pi/360.)
	switch axis {
	case 'X':return QuaternionXYZW{s,0,0,c},nil
	case 'Y':return QuaternionXYZW{0,s,0,c},nil
	case 'Z':return QuaternionXYZW{0,0,s,c},nil
	default:return QuaternionXYZW{},errors.New("UNKNOWN_ROTATION_AXIS")
	}
}
func QRotate(q QuaternionXYZW,v Vec3)(Vec3,error){
	q,e:=qUnit(q);if e!=nil{return Vec3{},e}
	p:=QuaternionXYZW{v[0],v[1],v[2],0}
	inv:=QuaternionXYZW{-q[0],-q[1],-q[2],q[3]}
	res:=qMul(qMul(q,p),inv)
	return Vec3{res[0],res[1],res[2]},nil
}

// SourceRotations applies rotations strictly in the ordered BVH channel list.
// Position channels do not participate in local rotation; world orientation
// composes the exact parent chain. No human or anatomical semantics asserted.
func (m *Motion) SourceRotations(frame int)([]OriginalSyntheticRotationKey,error){
	if m==nil||m.Rights!="ORIGINAL_SELF_AUTHORED_SYNTHETIC"||len(m.SourceSHA256)!=64||m.MeterPerUnit<=0 {
		return nil,errors.New("UNADMITTED_OR_BAD_SOURCE_ROTATIONS")
	}
	if frame<0||frame>=len(m.Frames){return nil,errors.New("SOURCE_ROTATION_CLOCK_OUT_OF_BOUNDS")}
	local:=make([]QuaternionXYZW,len(m.Joints))
	world:=make([]QuaternionXYZW,len(m.Joints))
	result:=make([]OriginalSyntheticRotationKey,len(m.Joints))
	cursor:=0
	for i,j:=range m.Joints{
		if j.Name==""||len(j.Channels)<3{return nil,errors.New("SOURCE_JOINT_CHANNELS_MISSING")}
		q:=QuaternionXYZW{0,0,0,1}
		for _,ch:=range j.Channels{
			if cursor>=len(m.Frames[frame]){return nil,errors.New("SOURCE_CHANNEL_SHORT")}
			angle:=m.Frames[frame][cursor];cursor++
			if math.IsNaN(angle)||math.IsInf(angle,0){return nil,errors.New("NONFINITE_SOURCE_CHANNEL")}
			if strings.HasSuffix(ch,"rotation"){
				axis,e:=qAxis(ch[0],angle);if e!=nil{return nil,e}
				q=qMul(q,axis)
			}else if !strings.HasSuffix(ch,"position"){return nil,errors.New("UNKNOWN_SOURCE_CHANNEL")}
		}
		var e error
		local[i],e=qUnit(q);if e!=nil{return nil,e}
		if j.Parent<0{
			if i!=0{return nil,errors.New("UNEXPECTED_EXTRA_ROOT")}
			world[i]=local[i]
		}else{
			if j.Parent>=i{return nil,errors.New("SOURCE_HIERARCHY_ORDER_INVALID")}
			world[i],e=qUnit(qMul(world[j.Parent],local[i]));if e!=nil{return nil,e}
		}
		result[i]=OriginalSyntheticRotationKey{Name:j.Name,SourceFrame:frame,
			Parent:j.Parent,LocalXYZW:local[i],WorldXYZW:world[i]}
	}
	if cursor!=len(m.Frames[frame]){return nil,errors.New("SOURCE_CHANNEL_SURPLUS")}
	return result,nil
}

// SourceSynthetic60To30 intentionally loses the middle source frame. Explicit
// loss prevents false complete-3-source-frame motion-transport claims.
func (m *Motion) SourceSynthetic60To30() (OriginalSyntheticRotationLoss,error){
	result:=OriginalSyntheticRotationLoss{
		Schema:"scp.r009.public-original-bvh-ordered-quaternion-loss.v1",
		SourceFPS:60,TargetFPS:30,TargetFrames:2,
		SourceFrameOne:"DROPPED_30FPS_RESAMPLE_NOT_INTERPOLATED",
		HumanROM:"UNKNOWN",PhysicalRetarget:"NOT_RUN_SOURCE_QUATERNIONS_ONLY",
		ProtectedR009:"HELD_NOT_ACCEPTED",
	}
	if m==nil{return result,errors.New("NIL_SOURCE_MOTION")}
	result.SourceFrames=len(m.Frames)
	if m.Rights!="ORIGINAL_SELF_AUTHORED_SYNTHETIC"||len(m.Frames)!=3||len(m.Joints)!=3{
		return result,errors.New("UNSUPPORTED_OR_UNADMITTED_ROTATION_PROJECTION")
	}
	for target,src:=range []int{0,2}{
		keys,e:=m.SourceRotations(src);if e!=nil{return result,e}
		for _,key:=range keys{
			key.TargetFrame=target
			result.Keyframes=append(result.Keyframes,key)
		}
	}
	return result,nil
}
