package main
// R073 source-only fail-closed depth and frame-provenance gate. This prototype
// can admit ONLY hard-coded original synthetic coplanar fixtures; general footage,
// camera calibration, subject depth inference and protected characters HOLD.
import(
 "bytes"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "io"
 "math"
 "os"
)
type R070 struct{
 Schema,SourceSHA,Frame1SHA,Frame2SHA,Lane,Expected,Status,Direction,Reason,Scope string
 WorldDX,WorldDY,CameraScale,CameraRotationRad,AnchorResidualPx float64
}
type R072 struct{
 Schema,SourceSHA,Lane,Status,SourceTruth,ObservedDirection,ObservedStatus,Reason,FirstSHA,SecondSHA,Scope string
 WorldDeltaX,SubjectDepth,ReferenceDepth float64
}
type Receipt struct{
 Schema,SourceSHA,Lane,Decision,Reason,Scope string
 FirstSHA,SecondSHA string
}
type Expect struct{ Truth,Class string; WorldDelta,ZRed,ZGreen float64 }
func catalog(lane string)(Expect,error){
 switch lane{
 case "coplanar-pan":return Expect{"STILL","COPLANAR",0,4,4},nil
 case "coplanar-world-right":return Expect{"RIGHT","COPLANAR",0.6,4,4},nil
 case "coplanar-world-left":return Expect{"LEFT","COPLANAR",-0.6,4,4},nil
 case "parallax-near-still":return Expect{"STILL","PARALLAX",0,2,4},nil
 case "parallax-far-still":return Expect{"STILL","PARALLAX",0,8,4},nil
 case "mixed-reference-depths":return Expect{"STILL","NONCOPLANAR_REFERENCE",0,4,3},nil
 case "lost-red":return Expect{"STILL","MISSING_SUBJECT",0,4,4},nil
 case "yaw-projective":return Expect{"STILL","PROJECTIVE_CAMERA",0,4,4},nil
 default:return Expect{},errors.New("UNLISTED_SOURCE_FIXTURE")
 }
}
func strictValue(d *json.Decoder,depth int)error{
 if depth>16{return errors.New("NESTING_LIMIT")}
 tok,err:=d.Token();if err!=nil{return err}
 x,ok:=tok.(json.Delim);if !ok{return nil}
 switch x{
 case '{':
  keys:=map[string]bool{}
  for d.More(){
   tok,err:=d.Token();if err!=nil{return err}
   key,ok:=tok.(string);if !ok{return errors.New("OBJECT_KEY_TYPE")}
   if keys[key]{return errors.New("DUPLICATE_KEY")}
   keys[key]=true
   if err:=strictValue(d,depth+1);err!=nil{return err}
  }
  end,err:=d.Token();if err!=nil{return err}
  if end!=json.Delim('}') {return errors.New("UNTERMINATED_OBJECT")}
 case '[':
  for d.More(){if err:=strictValue(d,depth+1);err!=nil{return err}}
  end,err:=d.Token();if err!=nil{return err}
  if end!=json.Delim(']'){return errors.New("UNTERMINATED_ARRAY")}
 default:return errors.New("INVALID_DELIMITER")
 }
 return nil
}
func readBounded(file string,out any)error{
 f,err:=os.Open(file);if err!=nil{return err};defer f.Close()
 raw,err:=io.ReadAll(io.LimitReader(f,8193));if err!=nil{return err}
 if len(raw)<20||len(raw)>8192{return errors.New("RECEIPT_BYTE_BOUNDS")}
 g:=json.NewDecoder(bytes.NewReader(raw))
 if err:=strictValue(g,0);err!=nil{return err}
 if _,err:=g.Token();err!=io.EOF{return errors.New("RECEIPT_TRAILING_DOCUMENT")}
 d:=json.NewDecoder(bytes.NewReader(raw));d.DisallowUnknownFields()
 if err:=d.Decode(out);err!=nil{return err}
 if _,err:=d.Token();err!=io.EOF{return errors.New("RECEIPT_EXTRA_CONTENT")}
 return nil
}
func fileSHA(path string)string{
 raw,err:=os.ReadFile(path);if err!=nil{return ""}
 h:=sha256.Sum256(raw);return hex.EncodeToString(h[:])
}
func decide(lane,sha,decoded1,decoded2 string,a R070,b R072)Receipt{
 r:=Receipt{Schema:"scp.r073.depth-source-admission.v1",SourceSHA:sha,Lane:lane,
  Decision:"HOLD_UNVERIFIED_EVIDENCE",Scope:"KNOWN_SYNTHETIC_PINHOLE_SCENES_ONLY",
  FirstSHA:decoded1,SecondSHA:decoded2}
 expected,err:=catalog(lane)
 if err!=nil{r.Reason=err.Error();return r}
 if len(sha)!=40||len(decoded1)!=64||len(decoded2)!=64||
    a.Schema!="scp.r070.similarity-camera.v1"||b.Schema!="scp.r072.pinhole-parallax-counterexample.v1"||
    a.SourceSHA!=sha||b.SourceSHA!=sha||b.Lane!=lane||
    a.Frame1SHA!=decoded1||b.FirstSHA!=decoded1||
    a.Frame2SHA!=decoded2||b.SecondSHA!=decoded2||
    a.Direction!=b.ObservedDirection||a.Status!=b.ObservedStatus{
   r.Reason="EXACT_SOURCE_AND_ACTUAL_DECODED_FRAME_BINDING_REQUIRED";return r
 }
 if !finite(b.WorldDeltaX)||!finite(b.SubjectDepth)||!finite(b.ReferenceDepth)||!finite(a.WorldDX)||
    b.SubjectDepth<=0||b.ReferenceDepth<=0||
    math.Abs(b.WorldDeltaX-expected.WorldDelta)>0.00001||
    math.Abs(b.SubjectDepth-expected.ZRed)>0.00001||
    math.Abs(b.ReferenceDepth-expected.ZGreen)>0.00001||
    b.SourceTruth!=expected.Truth{
   r.Reason="WORLD_SOURCE_LEDGER_CONFLICT";return r
 }
 switch expected.Class{
 case "COPLANAR":
  if b.Status!="SAFE_COPLANAR_CONTROL"||a.Status!="PASS_NARROW_SOURCE_ONLY"||a.Direction!=expected.Truth||
     math.Abs(expected.ZRed-expected.ZGreen)>0.01{
   r.Reason="COPLANAR_OR_LABEL_NOT_PROVEN";return r
  }
  r.Decision="ADMIT_SYNTHETIC_COPLANAR_ONLY"
  r.Reason="ORIGINAL_WORLD_SOURCE_AND_DECODED_FRAMES_BOUND"
 case "PARALLAX":
  r.Decision="HOLD_PARALLAX"
  r.Reason="SUBJECT_DEPTH_NOT_EQUAL_STATIC_REFERENCE_DEPTH"
 case "NONCOPLANAR_REFERENCE":
  r.Decision="HOLD_REFERENCE_DEPTH"
  r.Reason="THREE_REFERENCES_NOT_COMMON_DEPTH"
 case "MISSING_SUBJECT":
  r.Decision="HOLD_MISSING_SUBJECT"
  r.Reason="NO_RED_SUBJECT_IN_SECOND_FRAME"
 case "PROJECTIVE_CAMERA":
  r.Decision="HOLD_PROJECTIVE_CAMERA"
  r.Reason="CAMERA_YAW_IS_NOT_2D_SIMILARITY"
 }
 return r
}
func finite(x float64)bool{return !math.IsNaN(x)&&!math.IsInf(x,0)}
func main(){
 lane:=flag.String("lane","","one original fixture")
 source:=flag.String("source-sha","","exact current source commit SHA")
 first:=flag.String("first","","actual decoded PNG 1")
 second:=flag.String("second","","actual decoded PNG 2")
 input070:=flag.String("r070","","original R070 receipt")
 input072:=flag.String("r072","","independent R072 receipt")
 flag.Parse()
 fail:=func(reason string){
  r:=Receipt{Schema:"scp.r073.depth-source-admission.v1",SourceSHA:*source,Lane:*lane,
   Decision:"HOLD_UNVERIFIED_EVIDENCE",Reason:reason,Scope:"KNOWN_SYNTHETIC_PINHOLE_SCENES_ONLY"}
  b,_:=json.Marshal(r);fmt.Println(string(b));os.Exit(12)
 }
 if *first==""||*second==""||*input070==""||*input072==""{fail("MISSING_INPUT")}
 var a R070;var b R072
 if err:=readBounded(*input070,&a);err!=nil{fail("R070_RECEIPT_"+err.Error())}
 if err:=readBounded(*input072,&b);err!=nil{fail("R072_RECEIPT_"+err.Error())}
 r:=decide(*lane,*source,fileSHA(*first),fileSHA(*second),a,b)
 raw,_:=json.Marshal(r);fmt.Println(string(raw))
 if r.Decision!="ADMIT_SYNTHETIC_COPLANAR_ONLY"{os.Exit(12)}
}
