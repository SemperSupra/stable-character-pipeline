// Original self-authored BVH quaternion -> corrected VMD v2 binary transport.
// IMPORTANT: source-frame-2 compound Z/X and local position are deliberate
// source-safe synthetic mutations, not real motion or an admitted human rig.
// Compiles alongside immutable #250 Write/Parse with only its CLI main renamed.
package main

import (
	"crypto/sha256"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"math"
	"math/big"
	"os"
	"strings"

	bvh "example.org/scp/bvhcontract"
)

const fixtureSHA = "ab3a0d712c9c4f21fba0cf0698568dd5f88f1b959cf8aae28173c6435153d760"

func failClass(e error) error {
	return fmt.Errorf("ORIGINAL_BVH_ROT_VMD_REJECT:%w",e)
}
func produce(args []string) error {
	f:=flag.NewFlagSet("original-synthetic-ordered-rotation-vmd",flag.ContinueOnError)
	src:=f.String("source","","exact original A BVH")
	out:=f.String("out","","new source-safe VMD binary")
	receipt:=f.String("receipt","","new source-aware JSON receipt")
	fault:=f.String("fault","baseline","test-only adversarial mutation")
	caps:=f.Bool("capabilities",false,"read-only agent source capability")
	if e:=f.Parse(args);e!=nil{return e}
	if *caps{
		fmt.Println("{\"schema\":\"scp.r009.original-bvh-ordered-rotation-vmd.v1\",\"actions\":[\"capabilities\",\"write_original_only\"],\"source\":\"ORIGINAL_SELF_AUTHORED_SYNTHETIC\",\"private_R009\":\"HELD_NOT_ACCEPTED\",\"human_Retarget\":\"NOT_RUN\"}")
		return nil
	}
	if *src==""||*out==""||*receipt==""||*src==*out||*src==*receipt||*out==*receipt||f.NArg()!=0{
		return failClass(errors.New("UNSAFE_OR_MISSING_OUTPUTS"))
	}
	raw,e:=os.ReadFile(*src);if e!=nil{return failClass(e)}
	observedHash:=fmt.Sprintf("%x",sha256.Sum256(raw))
	if *fault=="bad_source"{raw=append(raw,byte(32))}
	if fmt.Sprintf("%x",sha256.Sum256(raw))!=fixtureSHA||observedHash!=fixtureSHA{
		return failClass(errors.New("UNADMITTED_SOURCE_BYTES"))
	}
	m,e:=bvh.Parse(raw,"ORIGINAL_SELF_AUTHORED_SYNTHETIC",1)
	if e!=nil{return failClass(e)}
	if len(m.Frames)!=3||len(m.Joints)!=3||len(m.Frames[2])!=12{
		return failClass(errors.New("UNADMITTED_OR_CHANGED_SOURCE_SHAPE"))
	}
	if strings.Join(m.Joints[0].Channels,",")!="Xposition,Yposition,Zposition,Zrotation,Xrotation,Yrotation"{
		return failClass(errors.New("UNADMITTED_ROOT_CHANNEL_ORDER"))
	}
	t,ok:=new(big.Rat).SetString(m.FrameTimeSeconds)
	if !ok{return failClass(errors.New("CLOCK_NOT_RATIONAL"))}
	dt,_:=t.Float64()
	if *fault=="bad_clock"{dt=1./29.}
	if math.Abs(dt-1./60.)>1e-12{return failClass(errors.New("UNADMITTED_SOURCE_CLOCK"))}
	if *fault=="alias"{m.Joints[1].Name="L_Ankle"}
	if *fault=="short_source"{m.Frames=m.Frames[:2]}
		// Deliberately modify only originally authored in-memory SOURCE frame2:
	// Z90/X90/Y0 -> synthetic noncommutative quaternion [0.5,0.5,0.5,0.5].
	// Never pretend this derived test is the immutable A fixture itself.
	m.Frames[2][3],m.Frames[2][4],m.Frames[2][5]=90,90,0
	if *fault=="bad_axis"{m.Frames[2][3]=math.Inf(1)}
	framebytes,e:=json.Marshal(m.Frames);if e!=nil{return failClass(e)}
	derivedHash:=fmt.Sprintf("%x",sha256.Sum256(framebytes))
	loss,e:=m.SourceSynthetic60To30();if e!=nil{return failClass(e)}
	if *fault=="fake_human"{loss.ProtectedR009="ACCEPTED"}
	if loss.ProtectedR009!="HELD_NOT_ACCEPTED"||loss.HumanROM!="UNKNOWN"||
		loss.PhysicalRetarget!="NOT_RUN_SOURCE_QUATERNIONS_ONLY"||
		loss.SourceFrameOne!="DROPPED_30FPS_RESAMPLE_NOT_INTERPOLATED"{
		return failClass(errors.New("LOSS_RIGHTS_OR_HUMAN_PROMOTION"))
	}
	if len(loss.Keyframes)!=6{return failClass(errors.New("MISSING_SOURCE_QUATERNION_KEYS"))}
	names:=[]string{"Hips","Knee","Foot"}
	keys:=make([]Frame,0,6)
	for _,name:=range names{
		for _,fidx:=range []int{0,1}{
			var key *bvh.OriginalSyntheticRotationKey
			for i:=range loss.Keyframes{
				k:=&loss.Keyframes[i]
				if k.Name==name&&k.TargetFrame==fidx{key=k;break}
			}
			if key==nil{return failClass(errors.New("SOURCE_JOINT_ALIAS_OR_TARGET_CLOCK"))}
			w0,e:=m.Evaluate(0);if e!=nil{return failClass(e)}
			w,e:=m.Evaluate(key.SourceFrame);if e!=nil{return failClass(e)}
			var pos [3]float32
			for j:=0;j<3;j++{
				bone:=0
				for bone<len(names)&&names[bone]!=name{bone++}
				if bone>=len(names){return failClass(errors.New("SOURCE_BONE_NAME_DRIFT"))}
				pos[j]=float32(w[bone].PositionMeters[j]-w0[bone].PositionMeters[j])
			}
			var q [4]float32
			for j:=0;j<4;j++{q[j]=float32(key.LocalXYZW[j])}
			if *fault=="bad_unit"&&name=="Hips"&&fidx==1{q=[4]float32{0,0,0,0}}
			keys=append(keys,Frame{Name:name,Index:uint32(fidx),Position:pos,Rotation:q})
		}
	}
	if len(keys)!=6{return failClass(errors.New("MISSING_VMD_SOURCE_KEYS"))}
	// Compare numerically without assuming exact binary parity after float32 conversion.
	for i,x:=range keys[1].Rotation{
		if math.Abs(float64(x)-.5)>1e-6{return failClass(fmt.Errorf("WRONG_COMPOUND_ROOT_QUATERNION_%d",i))}
	}
	data,e:=Write(keys);if e!=nil{return failClass(e)}
	parsed,e:=Parse(data);if e!=nil{return failClass(e)}
	if len(parsed)!=6||parsed[1].Name!="Hips"||parsed[1].Index!=1{
		return failClass(errors.New("NATIVE_VMD_ROTATION_READER_KEYS"))
	}
	vmdHash:=fmt.Sprintf("%x",sha256.Sum256(data))
	report:=map[string]any{
		"schema":"scp.r009.original-bvh-ordered-rotation-vmd.v1",
		"status":"PASS_ORIGINAL_SYNTHETIC_LOCAL_ROTATION_VMD_BINARY_SOURCE_ONLY",
		"original_a_sha256":fixtureSHA,
		"derived_in_memory_motion_sha256":derivedHash,
		"derived_source_frame2_root_rotation_channels_deg":map[string]int{"Zrotation":90,"Xrotation":90,"Yrotation":0},
		"derived_source_is_original_a_unchanged":false,
		"source_frame_1":"DROPPED_30FPS_RESAMPLE_NOT_INTERPOLATED",
		"source_fps":60,"vmd_fps":30,"source_frames":3,"vmd_frames":2,
		"source_bone_names":names,"vmd_keys":6,"vmd_sha256":vmdHash,
		"root_target_frame1_quat_xyzw":keys[1].Rotation,
		"rotation_mapping":"ORDERED_SOURCE_LOCAL_XYZW_TO_VMD_LOCAL_XYZW_BONE_REST_AXIS_UNKNOWN",
		"real_upstream_MMD_Tools_native":"NOT_RUN",
		"target_rest_axis_and_handedness":"UNKNOWN",
		"human_JCS_ROM":"UNKNOWN","true_ground_contact":"UNKNOWN",
		"rights":"ORIGINAL_SELF_AUTHORED_SYNTHETIC",
		"private_R009":"HELD_NOT_ACCEPTED","CPE":"NOT_PROMOTED",
	}
	jsonData,e:=json.MarshalIndent(report,"","  ");if e!=nil{return failClass(e)}
	if _,e=os.Stat(*out);e==nil{return failClass(errors.New("REFUSE_OVERWRITE_VMD"))}
	if _,e=os.Stat(*receipt);e==nil{return failClass(errors.New("REFUSE_OVERWRITE_RECEIPT"))}
	w,e:=os.OpenFile(*out,os.O_CREATE|os.O_EXCL|os.O_WRONLY,0600);if e!=nil{return failClass(e)}
	if _,e=w.Write(data);e!=nil{_ =w.Close();_ =os.Remove(*out);return failClass(e)}
	if e=w.Close();e!=nil{_ =os.Remove(*out);return failClass(e)}
	j,e:=os.OpenFile(*receipt,os.O_CREATE|os.O_EXCL|os.O_WRONLY,0600)
	if e!=nil{_ =os.Remove(*out);return failClass(e)}
	if _,e=j.Write(append(jsonData,10));e!=nil{_ =j.Close();_ =os.Remove(*receipt);_ =os.Remove(*out);return failClass(e)}
	if e=j.Close();e!=nil{_ =os.Remove(*receipt);_ =os.Remove(*out);return failClass(e)}
	fmt.Println("PASS_ORIGINAL_SYNTHETIC_ORDERED_ROTATION_VMD_SOURCE_ONLY",vmdHash)
	return nil
}
func main(){if e:=produce(os.Args[1:]);e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(2)}}
