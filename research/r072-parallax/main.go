package main
// R072: original source-only pinhole geometry counterexample to R070's
// 2D similarity assumption. A static near/far subject can appear moving
// because camera translation induces depth-dependent parallax.
// Ground truth comes from immutable source-world scene parameters, not VLM.
import(
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
type Vec3 struct{X,Y,Z float64}
type Camera struct{X,Y,Yaw float64}
type Scene struct{
 Green,Blue,Yellow,Red Vec3
 First,Second Camera
 RedMotionX float64
 SubjectVisible2 bool
}
type Observed struct{
 Schema,SourceSHA,Frame1SHA,Frame2SHA,Lane,Expected,Status,Direction,Reason,Scope string
 WorldDX,WorldDY,CameraScale,CameraRotationRad,AnchorResidualPx float64
}
type Receipt struct{
 Schema,SourceSHA,Lane,Status,SourceTruth,ObservedDirection,ObservedStatus,Reason,FirstSHA,SecondSHA string
 WorldDeltaX,SubjectDepth,ReferenceDepth float64
 Scope string
}
func sourceScene(lane string)(Scene,error){
 s:=Scene{
  Green:Vec3{-1.7,-1.1,4},Blue:Vec3{1.7,-1.1,4},Yellow:Vec3{-1.7,1.2,4},Red:Vec3{0.2,0.2,4},
  First:Camera{0,0,0},Second:Camera{0.4,0,0},SubjectVisible2:true,
 }
 switch lane{
 case "coplanar-pan":
 case "coplanar-world-right":s.RedMotionX=0.6
 case "coplanar-world-left":s.RedMotionX=-0.6
 case "parallax-near-still":s.Red.Z=2
 case "parallax-far-still":s.Red.Z=8
 case "mixed-reference-depths":s.Green.Z=3;s.Blue.Z=5
 case "lost-red":s.SubjectVisible2=false
 case "yaw-projective":s.Second=Camera{0,0,0.22}
 default:return Scene{},errors.New("LANE_UNSUPPORTED")
 }
 return s,nil
}
func projected(p Vec3,c Camera)(float64,float64,error){
 dx,dy:=p.X-c.X,p.Y-c.Y
 cs,sn:=math.Cos(c.Yaw),math.Sin(c.Yaw)
 x:=cs*dx-sn*p.Z
 z:=sn*dx+cs*p.Z
 if z<=0.1{return 0,0,errors.New("BEHIND_CAMERA")}
 return 160+180*x/z,160+180*dy/z,nil
}
func square(img *image.RGBA,wx,wy float64,c color.RGBA){
 x,y:=int(math.Round(wx)),int(math.Round(wy))
 draw.Draw(img,image.Rect(x-9,y-9,x+9,y+9),&image.Uniform{C:c},image.Point{},draw.Src)
}
func render(path string,s Scene,second bool)error{
 img:=image.NewRGBA(image.Rect(0,0,320,320))
 draw.Draw(img,img.Bounds(),&image.Uniform{C:color.RGBA{245,245,245,255}},image.Point{},draw.Src)
 cam:=s.First
 if second{cam=s.Second}
 pts:=[]Vec3{s.Green,s.Blue,s.Yellow,s.Red}
 if second{pts[3].X+=s.RedMotionX}
 colors:=[]color.RGBA{
  {0,212,0,255},{0,25,225,255},{227,217,0,255},{225,0,0,255},
 }
 for i,p:=range pts{
  if second&&i==3&&!s.SubjectVisible2{continue}
  x,y,err:=projected(p,cam);if err!=nil{return err}
  if x<16||x>304||y<16||y>304{return errors.New("PROJECTION_OUT_OF_FRAME")}
  square(img,x,y,colors[i])
 }
 file,err:=os.Create(path);if err!=nil{return err}
 err=png.Encode(file,img);other:=file.Close();if err!=nil{return err};return other
}
func generate(lane,dir string)error{
 s,err:=sourceScene(lane);if err!=nil{return err}
 if err:=os.MkdirAll(dir,0700);err!=nil{return err}
 if err:=render(filepath.Join(dir,"frame_001.png"),s,false);err!=nil{return err}
 return render(filepath.Join(dir,"frame_002.png"),s,true)
}
func sha(path string)string{
 b,err:=os.ReadFile(path);if err!=nil{return ""}
 x:=sha256.Sum256(b);return hex.EncodeToString(x[:])
}
func expected(lane string)(string,string,error){
 switch lane {
 case "coplanar-pan":return "STILL","SAFE",nil
 case "coplanar-world-right":return "RIGHT","SAFE",nil
 case "coplanar-world-left":return "LEFT","SAFE",nil
 case "parallax-near-still":return "STILL","UNSAFE_2D_FALSE_MOTION_LEFT",nil
 case "parallax-far-still":return "STILL","UNSAFE_2D_FALSE_MOTION_RIGHT",nil
 case "mixed-reference-depths":return "STILL","R070_ABSTAIN",nil
 case "lost-red":return "STILL","R070_ABSTAIN",nil
 case "yaw-projective":return "STILL","R070_ABSTAIN",nil
 default:return "","",errors.New("LANE_UNSUPPORTED")
 }
}
func audit(lane string,obs Observed)(Receipt,error){
 scene,err:=sourceScene(lane);if err!=nil{return Receipt{},err}
 truth,category,err:=expected(lane);if err!=nil{return Receipt{},err}
 r:=Receipt{Schema:"scp.r072.pinhole-parallax-counterexample.v1",SourceSHA:os.Getenv("GITHUB_SHA"),
  Lane:lane,SourceTruth:truth,ObservedDirection:obs.Direction,ObservedStatus:obs.Status,
  WorldDeltaX:scene.RedMotionX,SubjectDepth:scene.Red.Z,ReferenceDepth:scene.Green.Z,
  Scope:"SOURCE_ORIGINAL_3D_PINHOLE_STATIC_REFERENCE_COLOR_MARKERS_ONLY"}
 switch category{
 case "SAFE":
  if obs.Status=="PASS_NARROW_SOURCE_ONLY"&&obs.Direction==truth{
   r.Status="SAFE_COPLANAR_CONTROL";return r,nil
  }
  r.Reason="UNEXPECTED_COPLANAR_FAILURE"
 case "UNSAFE_2D_FALSE_MOTION_LEFT":
  if obs.Status=="PASS_NARROW_SOURCE_ONLY"&&obs.Direction=="LEFT"&&scene.RedMotionX==0{
   r.Status="CONFIRMED_UNSAFE_2D_PARALLAX_FALSE_MOTION";return r,nil
  }
  r.Reason="COUNTEREXAMPLE_NOT_REPRODUCED"
 case "UNSAFE_2D_FALSE_MOTION_RIGHT":
  if obs.Status=="PASS_NARROW_SOURCE_ONLY"&&obs.Direction=="RIGHT"&&scene.RedMotionX==0{
   r.Status="CONFIRMED_UNSAFE_2D_PARALLAX_FALSE_MOTION";return r,nil
  }
  r.Reason="COUNTEREXAMPLE_NOT_REPRODUCED"
 case "R070_ABSTAIN":
  if obs.Status=="UNKNOWN"&&obs.Direction=="UNKNOWN"{
   r.Status="REJECTED_OUT_OF_DOMAIN";r.Reason=obs.Reason;return r,nil
  }
  r.Reason="UNEXPECTED_NON_ABSTENTION"
 }
 r.Status="FAIL_CONTROL";return r,errors.New(r.Reason)
}
func main(){
 lane:=flag.String("lane","","source-only 3D experiment")
 dir:=flag.String("out","","source-original output directory")
 observed:=flag.String("observed","","R070 actual decoded-H264 receipt JSON")
 first:=flag.String("first","","R070 decoded PNG first")
 second:=flag.String("second","","R070 decoded PNG second")
 flag.Parse()
 if *observed==""{
  if *dir==""{fmt.Fprintln(os.Stderr,"MISSING_OUTPUT");os.Exit(12)}
  if err:=generate(*lane,*dir);err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(12)}
  fmt.Println("R072_ORIGINAL_PINHOLE_GENERATED",*lane);return
 }
 raw,err:=os.ReadFile(*observed)
 if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(12)}
 var o Observed
 if err:=json.Unmarshal(raw,&o);err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(12)}
 r,err:=audit(*lane,o)
 r.FirstSHA=sha(*first);r.SecondSHA=sha(*second)
 b,_:=json.Marshal(r);fmt.Println(string(b))
 if err!=nil{os.Exit(12)}
}
