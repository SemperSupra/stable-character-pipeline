// R066: fail-closed two-object relative motion oracle for original synthetic H.264.
// A single static green fiducial corrects only global camera TRANSLATION, not rotation,
// parallax, zoom, tracking identity, or arbitrary human motion.
package main

import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "image"
 "image/color"
 "image/draw"
 "image/png"
 "math"
 "os"
 "path/filepath"
)

type ColorCenter struct {
 X float64
 Pixels int
}
type Scene struct {
 Red ColorCenter
 Green ColorCenter
 Width int
 Height int
}
type Receipt struct {
 Schema string `json:"schema"`
 SourceSHA string `json:"source_sha"`
 FirstSHA string `json:"first_decoded_sha256"`
 SecondSHA string `json:"second_decoded_sha256"`
 Status string `json:"status"`
 Direction string `json:"direction"`
 Expected string `json:"expected"`
 CameraDelta float64 `json:"camera_dx_px"`
 SubjectDelta float64 `json:"subject_dx_px"`
 RelativeDelta float64 `json:"relative_dx_px"`
 Reason string `json:"reason,omitempty"`
 Scope string `json:"scope"`
}
func decode(path string)(Scene,error){
 f,err:=os.Open(path);if err!=nil{return Scene{},err};defer f.Close()
 img,err:=png.Decode(f);if err!=nil{return Scene{},err}
 b:=img.Bounds()
 var rsum,gsum float64;var rn,gn int
 for y:=b.Min.Y;y<b.Max.Y;y++{
  for x:=b.Min.X;x<b.Max.X;x++{
   rr,gg,bb,aa:=img.At(x,y).RGBA()
   r,g,bl,a:=int(rr>>8),int(gg>>8),int(bb>>8),int(aa>>8)
   if a<200{continue}
   if r>165&&r>g+75&&r>bl+75{rn++;rsum+=float64(x-b.Min.X)}
   if g>150&&g>r+75&&g>bl+75{gn++;gsum+=float64(x-b.Min.X)}
  }
 }
 if rn<120{return Scene{},errors.New("NO_RED_SUBJECT")}
 if gn<120{return Scene{},errors.New("NO_GREEN_FIDUCIAL")}
 return Scene{Red:ColorCenter{rsum/float64(rn),rn},Green:ColorCenter{gsum/float64(gn),gn},Width:b.Dx(),Height:b.Dy()},nil
}
func evaluate(a,b Scene)(direction string,camera,subject,relative float64,err error){
 if a.Width!=b.Width||a.Height!=b.Height{return "UNKNOWN",0,0,0,errors.New("DIMENSION_MISMATCH")}
 if a.Red.Pixels<120||b.Red.Pixels<120{return "UNKNOWN",0,0,0,errors.New("NO_RED_SUBJECT")}
 if a.Green.Pixels<120||b.Green.Pixels<120{return "UNKNOWN",0,0,0,errors.New("NO_GREEN_FIDUCIAL")}
 for _,ratio:=range []float64{
  float64(b.Red.Pixels)/float64(a.Red.Pixels),
  float64(b.Green.Pixels)/float64(a.Green.Pixels),
 } {
  if ratio<0.85||ratio>1.15{return "UNKNOWN",0,0,0,errors.New("AREA_OR_VISIBILITY_DRIFT")}
 }
 camera=b.Green.X-a.Green.X
 subject=b.Red.X-a.Red.X
 relative=subject-camera
 switch{
 case math.Abs(relative)<=8:return "STILL",camera,subject,relative,nil
 case relative>8:return "RIGHT",camera,subject,relative,nil
 default:return "LEFT",camera,subject,relative,nil
 }
}
func makeFrame(file string,redX,greenX int,redVisible,greenVisible bool)error{
 img:=image.NewRGBA(image.Rect(0,0,224,224))
 draw.Draw(img,img.Bounds(),&image.Uniform{C:color.RGBA{248,248,248,255}},image.Point{},draw.Src)
 if redVisible {
  draw.Draw(img,image.Rect(redX,95,redX+40,135),&image.Uniform{C:color.RGBA{225,0,0,255}},image.Point{},draw.Src)
 }
 if greenVisible {
  draw.Draw(img,image.Rect(greenX,25,greenX+24,49),&image.Uniform{C:color.RGBA{0,218,0,255}},image.Point{},draw.Src)
 }
 f,err:=os.Create(file);if err!=nil{return err}
 err=png.Encode(f,img);closeErr:=f.Close()
 if err!=nil{return err};return closeErr
}
func generate(lane,dir string)error{
 type frame struct{x,ref int;red,green bool}
 first:=frame{90,105,true,true}
 second:=frame{90,105,true,true}
 switch lane{
 case "camera-pan-only":second.x=114;second.ref=129
 case "right-with-opposite-pan":second.x=123;second.ref=83
 case "left-with-opposite-pan":second.x=57;second.ref=127
 case "missing-fiducial":second.green=false
 case "missing-subject":second.red=false
 default:return errors.New("UNSUPPORTED_FIXTURE")
 }
 if err:=os.MkdirAll(dir,0700);err!=nil{return err}
 if err:=makeFrame(filepath.Join(dir,"frame_001.png"),first.x,first.ref,first.red,first.green);err!=nil{return err}
 return makeFrame(filepath.Join(dir,"frame_002.png"),second.x,second.ref,second.red,second.green)
}
func digest(path string)string{
 b,err:=os.ReadFile(path);if err!=nil{return ""}
 h:=sha256.Sum256(b);return hex.EncodeToString(h[:])
}
func main(){
 makeLane:=flag.String("make","","fixture name")
 out:=flag.String("out","","fixture directory")
 first:=flag.String("first","","first actual decoded PNG")
 second:=flag.String("second","","second actual decoded PNG")
 expected:=flag.String("expect","","expected LEFT/RIGHT/STILL/UNKNOWN")
 flag.Parse()
 if *makeLane!=""{
  if *out==""{fmt.Fprintln(os.Stderr,"R066_HOLD missing directory");os.Exit(12)}
  if err:=generate(*makeLane,*out);err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(12)}
  fmt.Println("R066_GENERATED_ORIGINAL_SOURCE_ONLY",*makeLane);return
 }
 if *first==""||*second==""||*expected==""{fmt.Fprintln(os.Stderr,"R066_HOLD missing test inputs");os.Exit(12)}
 r:=Receipt{Schema:"scp.r066.camera-relative-critic.v1",SourceSHA:os.Getenv("GITHUB_SHA"),
  FirstSHA:digest(*first),SecondSHA:digest(*second),Direction:"UNKNOWN",Expected:*expected,
  Status:"UNKNOWN",Scope:"SINGLE_STATIC_GREEN_REFERENCE_AND_RED_SUBJECT_ONLY"}
 a,err1:=decode(*first);b,err2:=decode(*second)
 var err error
 if err1!=nil{err=err1}else if err2!=nil{err=err2}else{
  r.Direction,r.CameraDelta,r.SubjectDelta,r.RelativeDelta,err=evaluate(a,b)
 }
 switch{
 case err!=nil:r.Reason=err.Error()
 case r.Direction==*expected:r.Status="PASS_NARROW_SOURCE_ONLY"
 default:r.Status="FAIL_WRONG_DIRECTION";r.Reason="DIRECTION_MISMATCH"
 }
 msg,_:=json.Marshal(r);fmt.Println(string(msg))
 if r.Status!="PASS_NARROW_SOURCE_ONLY"{os.Exit(12)}
}
