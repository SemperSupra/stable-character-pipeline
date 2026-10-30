// W2C: source-clean fail-closed evidence aggregator, never a human quality PASS.
// JSON schema is intentionally distinct from any model-generated review.
package main

import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "os"
 "regexp"
 "strings"
)

type Input struct {
 Native []byte
 L1 []byte
 L2 []byte
 L3 []byte
 W2A []byte
 W2B []byte
 Target string
}
type Decision struct {
 Schema string `json:"schema"`
 Status string `json:"status"`
 ImageQuality string `json:"image_quality"`
 HumanAnatomy string `json:"human_anatomy"`
 Publication string `json:"publication"`
 Target string `json:"target"`
 VideoSHA256 string `json:"video_sha256,omitempty"`
 Reasons []string `json:"reasons"`
 Receipts map[string]string `json:"receipt_sha256"`
}
var hexdigest=regexp.MustCompile(`^[a-f0-9]{64}$`)
func readMap(b []byte) (map[string]any,error) {
 if len(b)>4*1024*1024 {return nil,errors.New("RECEIPT_TOO_LARGE")}
 var v map[string]any
 if err:=json.Unmarshal(b,&v);err!=nil{return nil,err}
 if v==nil {return nil,errors.New("EMPTY_RECEIPT")}
 return v,nil
}
func field(m map[string]any,k string) string {s,_:=m[k].(string);return s}
func truth(m map[string]any,k string) bool {v,_:=m[k].(bool);return v}
func checkSHA(s string) bool {return hexdigest.MatchString(s)}
func judge(in Input) Decision {
 d:=Decision{Schema:"scp.visualqa.w2c_decision.v1",Status:"UNKNOWN",
  ImageQuality:"UNKNOWN",HumanAnatomy:"UNKNOWN_UNQUALIFIED",
  Publication:"HELD_NO_AUTOMATIC_RELEASE",Target:in.Target,
  Reasons:[]string{},Receipts:map[string]string{}}
 fails,unknown:=[]string{},[]string{}
 if in.Target!="synthetic_research"&&in.Target!="full_human"{
  fails=append(fails,"INVALID_TARGET")
 }
 data:=map[string][]byte{"native":in.Native,"l1":in.L1,"l2":in.L2,
                         "l3":in.L3,"w2a":in.W2A,"w2b":in.W2B}
 parsed:=map[string]map[string]any{}
 for _,k:=range []string{"native","l1","l2","l3","w2a","w2b"} {
  b:=data[k]
  if len(b)==0 {unknown=append(unknown,"MISSING_"+strings.ToUpper(k));continue}
  sum:=sha256.Sum256(b);d.Receipts[k]=hex.EncodeToString(sum[:])
  m,err:=readMap(b)
  if err!=nil {fails=append(fails,"CORRUPT_"+strings.ToUpper(k));continue}
  parsed[k]=m
 }
 native,ok:=parsed["native"]
 if !ok {unknown=append(unknown,"NATIVE_SOURCE_UNVERIFIED")} else {
  d.VideoSHA256=field(native,"video_sha256")
  if field(native,"source_rights")!="ORIGINAL_SELF_AUTHORED_SYNTHETIC" ||
     !checkSHA(d.VideoSHA256)||!checkSHA(field(native,"blend_sha256")) {
    fails=append(fails,"NATIVE_RIGHTS_OR_SOURCE_HASH_INVALID")
  }
 }
 if m,ok:=parsed["l1"];ok {
  if field(m,"schema")!="scp.visualqa.l1_video.v1" || field(m,"source_sha256")!=d.VideoSHA256 {
   fails=append(fails,"L1_CONTRACT_OR_VIDEO_MISMATCH")
  } else {
   switch field(m,"status") {
   case "FAIL": fails=append(fails,"RENDERED_PIXEL_QA_FAILURE");d.ImageQuality="FAIL"
   case "PASS_L1_VIDEO_ONLY": d.ImageQuality="PASS_L1_VIDEO_ONLY"
   default: unknown=append(unknown,"L1_NOT_ADJUDICATED")
   }
  }
 }
 if m,ok:=parsed["l2"];ok {
  if field(m,"schema")!="scp.visualqa.l2_knee_result.v1"||
    field(m,"source_sha256")!=field(native,"blend_sha256")||
    !truth(m,"verified_source_bytes"){
   fails=append(fails,"L2_RIG_SOURCE_NOT_VERIFIED")
  } else {
   switch field(m,"status"){
   case "FAIL":fails=append(fails,"RIG_GEOMETRY_FAILURE")
   case "PASS_L2_REST_POLE_GEOMETRY_ONLY": // source-pole, not human anatomy
   case "UNKNOWN":unknown=append(unknown,"L2_SOURCE_POLE_UNKNOWN")
   default:fails=append(fails,"L2_UNRECOGNIZED_STATUS")
   }
  }
 }
 if m,ok:=parsed["l3"];ok {
  if field(m,"schema")!="scp.visualqa.l3_pixel_inferred_pose_research.v1"||
     field(m,"video_sha256")!=d.VideoSHA256{
   fails=append(fails,"L3_VIDEO_MODEL_PROVENANCE_MISMATCH")
  } else {
   switch field(m,"status"){
   case "UNKNOWN_NO_MODEL_POSE_DETECTION":unknown=append(unknown,"L3_NO_POSE_DETECTION")
   case "OBSERVED_UNQUALIFIED":unknown=append(unknown,"L3_MODEL_NOT_ANATOMICAL_ORACLE")
   default:fails=append(fails,"L3_UNRECOGNIZED_STATUS")
   }
  }
 }
 if m,ok:=parsed["w2a"];ok {
  if field(m,"schema")!="scp.visualqa.w2a_temporal_research.v1"||
     field(m,"video_sha256")!=d.VideoSHA256||
     field(m,"status")!="OBSERVED_RESEARCH_ONLY"{
   fails=append(fails,"W2A_SOURCE_OR_STATUS_MISMATCH")
  }
 }
 if m,ok:=parsed["w2b"];ok {
  if field(m,"schema")!="scp.visualqa.w2b_image_geometry.v1"||
     field(m,"video_sha256")!=d.VideoSHA256{
   fails=append(fails,"W2B_SOURCE_OR_STATUS_MISMATCH")
  } else if field(m,"status")!="OBSERVED_UNQUALIFIED"&&field(m,"status")!="UNKNOWN_MISSING_FOREGROUND"{
   fails=append(fails,"W2B_UNKNOWN_CAMERA_PIXEL_STATE")
  } else if field(m,"status")=="UNKNOWN_MISSING_FOREGROUND"{
   unknown=append(unknown,"W2B_NO_IMAGE_FOREGROUND")
  }
 }
 // An unqualified model, no approved human rig semantics and missing future
 // independent human anatomy evidence mean human quality must never PASS.
 unknown=append(unknown,"NO_APPROVED_HUMAN_ANATOMY_OR_FULL_BODY_VISUAL_ORACLE")
 if len(fails)>0 {
  d.Status="FAIL";d.Reasons=append(d.Reasons,fails...)
  d.Reasons=append(d.Reasons,unknown...)
 } else {
  d.Status="UNKNOWN";d.Reasons=append(d.Reasons,unknown...)
 }
 return d
}
func main(){
 target:=flag.String("target","synthetic_research","synthetic_research or full_human")
 paths:=map[string]*string{}
 for _,k:=range []string{"native","l1","l2","l3","w2a","w2b"}{
  paths[k]=flag.String(k,"","source JSON receipt (optional except native)")
 }
 output:=flag.String("out","","decision JSON output path")
 flag.Parse()
 if *output=="" {fmt.Fprintln(os.Stderr,"required --out");os.Exit(3)}
 fields:=map[string][]byte{}
 for k,v:=range paths {
  if *v=="" {continue}
  b,err:=os.ReadFile(*v)
  if err!=nil {fmt.Fprintln(os.Stderr,"UNREADABLE_"+k,err);os.Exit(3)}
  fields[k]=b
 }
 d:=judge(Input{Target:*target,Native:fields["native"],L1:fields["l1"],
  L2:fields["l2"],L3:fields["l3"],W2A:fields["w2a"],W2B:fields["w2b"]})
 b,_:=json.MarshalIndent(d,"","  ");b=append(b,'\n')
 if err:=os.WriteFile(*output,b,0600);err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(3)}
 fmt.Println(string(b))
 if d.Status=="FAIL" {os.Exit(2)}
 os.Exit(3) // UNKNOWN is NOT a quality pass.
}
