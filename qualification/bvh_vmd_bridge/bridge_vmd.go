// Use the already-qualified #250 Write/Parse implementation, never reimplement VMD bytes.
// Compile this file alongside an immutable copy of the corrected VMD main.go
// with only its CLI entry point renamed for an isolated public Actions test.
package main
import (
 "crypto/sha256";"encoding/json";"errors";"flag";"fmt";"math";"math/big";"os"
)
type input struct {
 Schema string `json:"schema"`
 Rights string `json:"rights"`
 SourceSHA string `json:"source_sha256"`
 Time string `json:"frame_time_exact_decimal_rational"`
 Meter float64 `json:"meters_per_unit"`
 Rows []struct{
  Frame int `json:"frame"`
  World []struct{
   Name string `json:"name"`
   Position [3]float64 `json:"position_meters"`
  } `json:"world_joints"`
 } `json:"frames"`
}
func runBridge(args []string)error{
 f:=flag.NewFlagSet("original-bvh-to-vmd",flag.ContinueOnError)
 source:=f.String("fk","","original source-bound JSON")
 out:=f.String("out","","new authored VMD")
 receipt:=f.String("receipt","","new crosswalk receipt")
 fault:=f.String("fault","baseline","injected test only")
 if err:=f.Parse(args);err!=nil{return err}
 if *source==""||*out==""||*receipt==""||*source==*out||*out==*receipt||f.NArg()!=0{return errors.New("distinct paths required")}
 raw,e:=os.ReadFile(*source);if e!=nil{return e}
 var src input;if e=json.Unmarshal(raw,&src);e!=nil{return e}
 switch *fault {
 case "baseline":
 case "wrong_units":src.Meter=100
 case "wrong_clock":src.Time="1/29"
 case "forged_source":src.SourceSHA="f"+src.SourceSHA[1:]
 case "short_source":src.Rows=src.Rows[:2]
 case "joint_alias":src.Rows[2].World[2].Name="Knee"
 default:return errors.New("unsupported fault")
 }
 if src.Schema!="scp.r009.original-bvh-full-frame-fk.v1"||src.Rights!="ORIGINAL_SELF_AUTHORED_SYNTHETIC"{
  return errors.New("UNKNOWN_OR_UNADMITTED_SOURCE")}
 if src.SourceSHA!="ab3a0d712c9c4f21fba0cf0698568dd5f88f1b959cf8aae28173c6435153d760"{
  return errors.New("SOURCE_HASH_NOT_IN_ADMITTED_ORIGINAL_FIXTURE_SET")}
 if src.Meter!=1||len(src.Rows)!=3{return errors.New("SOURCE_UNIT_OR_FRAME_COUNT_WRONG")}
 clock,ok:=new(big.Rat).SetString(src.Time);if !ok{return errors.New("NO_RATIONAL_CLOCK")}
 dt,_:=clock.Float64();if math.Abs(dt-1./60.)>1e-12{return errors.New("UNSUPPORTED_SOURCE_FPS")}
 names:=[]string{"Hips","Knee","Foot"}
 for i,r:=range src.Rows{
  if r.Frame!=i||len(r.World)!=3{return errors.New("SOURCE_FK_FRAME_OR_JOINT_COUNT")}
  for j,v:=range r.World{
   if v.Name!=names[j]{return errors.New("SOURCE_JOINT_ALIAS_OR_ORDER")}
   for _,x:=range v.Position{if math.IsNaN(x)||math.IsInf(x,0)||math.Abs(x)>10{return errors.New("NONFINITE_OR_UNBOUNDED_SOURCE_POSITION")}}
  }
 }
 // VMD target clock 30 Hz; 0 and 2 at the 60 Hz source endpoints are admitted.
 // Source frame 1 is deliberately dropped and exposed in the loss map.
 keys:=[]Frame{}
 for j,name:=range names{
  for _,idx:=range []int{0,2}{
   var delta [3]float32
   for k:=0;k<3;k++{delta[k]=float32(src.Rows[idx].World[j].Position[k]-src.Rows[0].World[j].Position[k])}
   keys=append(keys,Frame{Name:name,Index:uint32(idx/2),Position:delta,
    Rotation:[4]float32{0,0,0,1}})
  }
 }
 data,e:=Write(keys);if e!=nil{return e}
 parsed,e:=Parse(data);if e!=nil{return e}
 if len(parsed)!=6{return errors.New("NATIVE_VMD_STRUCTURAL_READBACK_WRONG")}
 h:=sha256.Sum256(data)
 report:=map[string]any{
  "schema":"scp.r009.public-bvh-vmd-crosswalk.v1","status":"PASS_SOURCE_SYNTHETIC_EXPLICIT_LOSS_ONLY",
  "bvh_source_sha256":src.SourceSHA,"fk_receipt_sha256":fmt.Sprintf("%x",sha256.Sum256(raw)),
  "vmd_sha256":fmt.Sprintf("%x",h),"vmd_keys":6,"source_frames":3,
  "target_frame_pairs":[][]int{{0,0},{2,1}},"source_frame_1":"DROPPED_30FPS_RESAMPLE",
  "source_frame_time_rational":src.Time,"source_meters_per_unit":src.Meter,
  "target_fps":30,"axis_mapping":"SOURCE_XYZ_TO_TARGET_XYZ_SYNTHETIC_UNVALIDATED_PHYSICAL",
  "human_biomechanics":"UNKNOWN","actual_human_mocap":"NOT_ADMITTED",
  "native_bpy":"NOT_YET_RUN","private_R009":"HELD_NOT_ACCEPTED"}
 r,e:=json.MarshalIndent(report,"","  ");if e!=nil{return e}
 vf,e:=os.OpenFile(*out,os.O_WRONLY|os.O_CREATE|os.O_EXCL,0600);if e!=nil{return e}
 if _,e=vf.Write(data);e!=nil{vf.Close();os.Remove(*out);return e};if e=vf.Close();e!=nil{return e}
 rf,e:=os.OpenFile(*receipt,os.O_WRONLY|os.O_CREATE|os.O_EXCL,0600);if e!=nil{os.Remove(*out);return e}
 if _,e=rf.Write(append(r,'
'));e!=nil{rf.Close();os.Remove(*receipt);os.Remove(*out);return e};return rf.Close()
}
func main(){if err:=runBridge(os.Args[1:]);err!=nil{fmt.Fprintln(os.Stderr,"BVH_VMD_BRIDGE_REJECT:",err);os.Exit(2)}}
