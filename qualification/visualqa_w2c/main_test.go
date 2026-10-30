package main
import ("encoding/json";"reflect";"testing")
func bytes(m map[string]any) []byte {b,e:=json.Marshal(m);if e!=nil {panic(e)};return b}
const vsha="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
const bsha="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
func baseline() Input {
 n:=bytes(map[string]any{"source_rights":"ORIGINAL_SELF_AUTHORED_SYNTHETIC",
  "video_sha256":vsha,"blend_sha256":bsha})
 l1:=bytes(map[string]any{"schema":"scp.visualqa.l1_video.v1","status":"PASS_L1_VIDEO_ONLY","source_sha256":vsha})
 l2:=bytes(map[string]any{"schema":"scp.visualqa.l2_knee_result.v1","status":"PASS_L2_REST_POLE_GEOMETRY_ONLY",
  "source_sha256":bsha,"verified_source_bytes":true})
 l3:=bytes(map[string]any{"schema":"scp.visualqa.l3_pixel_inferred_pose_research.v1",
  "status":"OBSERVED_UNQUALIFIED","video_sha256":vsha})
 w2a:=bytes(map[string]any{"schema":"scp.visualqa.w2a_temporal_research.v1",
  "status":"OBSERVED_RESEARCH_ONLY","video_sha256":vsha})
 w2b:=bytes(map[string]any{"schema":"scp.visualqa.w2b_image_geometry.v1",
  "status":"OBSERVED_UNQUALIFIED","video_sha256":vsha})
 return Input{Native:n,L1:l1,L2:l2,L3:l3,W2A:w2a,W2B:w2b,Target:"synthetic_research"}
}
func has(xs []string,s string) bool {for _,x:=range xs{if x==s{return true}};return false}
func TestResearchSuccessStillNotHumanAcceptance(t *testing.T) {
 in:=baseline();d:=judge(in)
 if d.Status!="UNKNOWN"||d.HumanAnatomy!="UNKNOWN_UNQUALIFIED"||
 d.Publication!="HELD_NO_AUTOMATIC_RELEASE" {t.Fatalf("%+v",d)}
}
func TestNoDataAbstains(t *testing.T) {
 d:=judge(Input{Target:"synthetic_research"})
 if d.Status!="UNKNOWN"||!has(d.Reasons,"MISSING_L1")||!has(d.Reasons,"MISSING_NATIVE"){t.Fatalf("%+v",d)}
}
func TestVideoActualPixelFailureOverridesRigPass(t *testing.T) {
 in:=baseline()
 in.L1=bytes(map[string]any{"schema":"scp.visualqa.l1_video.v1","status":"FAIL","source_sha256":vsha})
 d:=judge(in)
 if d.Status!="FAIL"||d.ImageQuality!="FAIL"||!has(d.Reasons,"RENDERED_PIXEL_QA_FAILURE") {t.Fatalf("%+v",d)}
}
func TestRigFailureHasVeto(t *testing.T){
 in:=baseline()
 in.L2=bytes(map[string]any{"schema":"scp.visualqa.l2_knee_result.v1","status":"FAIL",
 "source_sha256":bsha,"verified_source_bytes":true})
 if d:=judge(in);d.Status!="FAIL"||!has(d.Reasons,"RIG_GEOMETRY_FAILURE"){t.Fatalf("%+v",d)}
}
func TestForgeryDetected(t *testing.T) {
 in:=baseline()
 in.L3=bytes(map[string]any{"schema":"scp.visualqa.l3_pixel_inferred_pose_research.v1",
 "status":"OBSERVED_UNQUALIFIED","video_sha256":bsha})
 if d:=judge(in);d.Status!="FAIL"||!has(d.Reasons,"L3_VIDEO_MODEL_PROVENANCE_MISMATCH"){t.Fatalf("%+v",d)}
}
func TestNoHumanModelDetectionStillUnknown(t *testing.T) {
 in:=baseline();in.Target="full_human"
 in.L3=bytes(map[string]any{"schema":"scp.visualqa.l3_pixel_inferred_pose_research.v1",
  "status":"UNKNOWN_NO_MODEL_POSE_DETECTION","video_sha256":vsha})
 d:=judge(in)
 if d.Status!="UNKNOWN"||!has(d.Reasons,"L3_NO_POSE_DETECTION"){t.Fatalf("%+v",d)}
}
func TestUnsafeRightsFail(t *testing.T){
 in:=baseline()
 in.Native=bytes(map[string]any{"source_rights":"UNLICENSED","video_sha256":vsha,"blend_sha256":bsha})
 if d:=judge(in);d.Status!="FAIL" {t.Fatalf("%+v",d)}
}
func TestDeterminismAndNoVisualOrCPEPromotion(t *testing.T){
 in:=baseline();first:=judge(in)
 for i:=0;i<10;i++ {other:=judge(in);if !reflect.DeepEqual(first,other){t.Fatalf("non-deterministic: %+v vs %+v",first,other)}}
 if first.Status=="PASS"||first.Publication=="APPROVED"{t.Fatal("unsafe promotion")}
}
