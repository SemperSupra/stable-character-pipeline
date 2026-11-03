// Original public-only BVH -> explicit world-space per-frame bridge input.
// Runs against the immutable #249 upstream Go parser, not a substitute parser.
package main
import (
 "crypto/sha256";"encoding/json";"flag";"fmt";"math";"math/big";"os"
 bvh "example.org/scp/bvhcontract"
)
func main(){
 source:=flag.String("source","","original authored BVH A")
 out:=flag.String("out","","new JSON"); flag.Parse()
 fail:=func(err any){fmt.Fprintln(os.Stderr,"BVH_EXPORT_FAIL_CLOSED:",err);os.Exit(2)}
 if *source==""||*out==""||len(flag.Args())!=0{fail("missing names")}
 raw,e:=os.ReadFile(*source);if e!=nil{fail(e)}
 hash:=fmt.Sprintf("%x",sha256.Sum256(raw))
 if hash!="ab3a0d712c9c4f21fba0cf0698568dd5f88f1b959cf8aae28173c6435153d760"{fail("BVH_UNAPPROVED_FIXTURE_SHA")}
 m,e:=bvh.Parse(raw,"ORIGINAL_SELF_AUTHORED_SYNTHETIC",1.0);if e!=nil{fail(e)}
 if len(m.Frames)!=3||len(m.Joints)!=3{fail("BVH_UNEXPECTED_FRAMES_OR_JOINTS")}
 rat,ok:=new(big.Rat).SetString(m.FrameTimeSeconds);if !ok{fail("BVH_BAD_RATIONAL")}
 t,_:=rat.Float64()
 if math.Abs(t-1.0/60.0)>1e-12{fail("UNSUPPORTED_60_HZ_FIXTURE")}
 rows:=make([]any,3)
 for i:=0;i<3;i++{joints,err:=m.Evaluate(i);if err!=nil{fail(err)}
   rows[i]=map[string]any{"frame":i,"world_joints":joints}}
 report:=map[string]any{"schema":"scp.r009.original-bvh-full-frame-fk.v1",
  "rights":"ORIGINAL_SELF_AUTHORED_SYNTHETIC","source_sha256":hash,
  "frame_time_exact_decimal_rational":m.FrameTimeSeconds,
  "source_time_60hz_approximation_tolerance_seconds":1e-12,
  "meters_per_unit":1.0,"frames":rows,"source_frames":3,
  "source_joints":[]string{"Hips","Knee","Foot"},
  "human_source":"NOT_ADMITTED","R009":"HELD_NOT_ACCEPTED"}
 data,e:=json.MarshalIndent(report,"","  ");if e!=nil{fail(e)}
 f,e:=os.OpenFile(*out,os.O_WRONLY|os.O_CREATE|os.O_EXCL,0600);if e!=nil{fail(e)}
 _,e=f.Write(append(data,'\n'));if e!=nil{f.Close();os.Remove(*out);fail(e)}
 if e=f.Close();e!=nil{fail(e)}
 fmt.Printf("BVH_ALL_THREE_ORIGINAL_FK_PASS source=%s\n",hash)
}
