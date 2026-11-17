// R070 fixed-camera 2D three-fiducial similarity geometry, source original.
// Reference A/B solve only scale, rotation, translation. Reference C independently
// falsifies model fit; subject residual is inverse-mapped to the first frame.
// No human reconstruction, depth, nonrigid, parallax or actual-source admission.
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
type Point struct { X float64; Y float64; Count int }
type Frame struct { Red,Green,Blue,Yellow Point; Width,Height int }
type Receipt struct {
 Schema string
 SourceSHA string
 Frame1SHA string
 Frame2SHA string
 Lane string
 Expected string
 Status string
 Direction string
 WorldDX float64
 WorldDY float64
 CameraScale float64
 CameraRotationRad float64
 AnchorResidualPx float64
 Reason string
 Scope string
}
type Pose struct { R,G,B,Y Point; Red,Green,Blue,Yellow bool; CamScale float64 }
const size=320
func basePose()Pose{
 return Pose{
  R:Point{X:165,Y:160}, G:Point{X:65,Y:75},B:Point{X:245,Y:75},Y:Point{X:65,Y:245},
  Red:true,Green:true,Blue:true,Yellow:true,CamScale:1,
 }
}
func camera(p Point,scale,theta,dx,dy float64)Point{
 x,y:=p.X-160,p.Y-160
 c,s:=math.Cos(theta),math.Sin(theta)
 return Point{X:160+dx+scale*(c*x-s*y),Y:160+dy+scale*(s*x+c*y)}
}
func poses(lane string)(Pose,Pose,error){
 first:=basePose()
 next:=basePose()
 scale,theta,dx,dy:=1.0,0.0,0.0,0.0
 switch lane{
 case "translation-only":dx=24;dy=-12
 case "zoom-only":scale=1.15;dx=5;dy=-3
 case "rotation-only":theta=0.12
 case "right-under-zoom":scale=1.10;theta=0.04;next.R.X+=32
 case "left-under-rotation":theta=0.15;next.R.X-=30
 case "corrupted-third-anchor":scale=1.08;next.Y.X+=35
 case "mirror-reflection":
  next.R.X=320-next.R.X;next.G.X=320-next.G.X;next.B.X=320-next.B.X;next.Y.X=320-next.Y.X
  return first,next,nil
 case "lost-third-anchor":next.Yellow=false
 case "lost-subject":next.Red=false
 default:return first,next,errors.New("UNSUPPORTED_LANE")
 }
 next.CamScale=scale
 next.R=camera(next.R,scale,theta,dx,dy)
 next.G=camera(next.G,scale,theta,dx,dy)
 next.B=camera(next.B,scale,theta,dx,dy)
 next.Y=camera(next.Y,scale,theta,dx,dy)
 return first,next,nil
}
func square(img *image.RGBA,p Point,half int,c color.RGBA){
 x,y:=int(math.Round(p.X)),int(math.Round(p.Y))
 b:=image.Rect(x-half,y-half,x+half,y+half)
 draw.Draw(img,b,&image.Uniform{C:c},image.Point{},draw.Src)
}
func save(path string,p Pose)error{
 img:=image.NewRGBA(image.Rect(0,0,size,size))
 draw.Draw(img,img.Bounds(),&image.Uniform{C:color.RGBA{245,245,245,255}},image.Point{},draw.Src)
 marker:=int(math.Round(10*p.CamScale))
 subject:=int(math.Round(13*p.CamScale))
 if p.Green{square(img,p.G,marker,color.RGBA{0,212,0,255})}
 if p.Blue{square(img,p.B,marker,color.RGBA{0,25,225,255})}
 if p.Yellow{square(img,p.Y,marker,color.RGBA{227,217,0,255})}
 if p.Red{square(img,p.R,subject,color.RGBA{225,0,0,255})}
 f,err:=os.Create(path);if err!=nil{return err}
 err=png.Encode(f,img);cerr:=f.Close();if err!=nil{return err};return cerr
}
func generate(lane,dir string)error{
 a,b,err:=poses(lane);if err!=nil{return err}
 if err:=os.MkdirAll(dir,0700);err!=nil{return err}
 if err:=save(filepath.Join(dir,"frame_001.png"),a);err!=nil{return err}
 return save(filepath.Join(dir,"frame_002.png"),b)
}
func readFrame(path string)(Frame,error){
 f,err:=os.Open(path);if err!=nil{return Frame{},err};defer f.Close()
 img,err:=png.Decode(f);if err!=nil{return Frame{},err}
 bounds:=img.Bounds()
 var sumsX,sumsY [4]float64
 var counts [4]int
 for y:=bounds.Min.Y;y<bounds.Max.Y;y++{
  for x:=bounds.Min.X;x<bounds.Max.X;x++{
   rr,gg,bb,aa:=img.At(x,y).RGBA()
   r,g,b,a:=int(rr>>8),int(gg>>8),int(bb>>8),int(aa>>8)
   if a<200{continue}
   index:=-1
   switch{
   case r>165&&r>g+75&&r>b+75:index=0
   case g>155&&g>r+75&&g>b+75:index=1
   case b>165&&b>r+75&&b>g+75:index=2
   case r>155&&g>155&&b<100&&r>g-75&&g>r-75:index=3
   }
   if index>=0{counts[index]++;sumsX[index]+=float64(x-bounds.Min.X);sumsY[index]+=float64(y-bounds.Min.Y)}
  }
 }
 pts:=make([]Point,4)
 for i:=range pts{
  pts[i].Count=counts[i]
  if counts[i]>0{pts[i].X=sumsX[i]/float64(counts[i]);pts[i].Y=sumsY[i]/float64(counts[i])}
 }
 return Frame{Red:pts[0],Green:pts[1],Blue:pts[2],Yellow:pts[3],Width:bounds.Dx(),Height:bounds.Dy()},nil
}
func classify(a,b Frame)(string,float64,float64,float64,float64,float64,error){
 if a.Width!=b.Width||a.Height!=b.Height||a.Width!=size||a.Height!=size{
  return "UNKNOWN",0,0,0,0,0,errors.New("FRAME_DIMENSIONS")
 }
 pairs:=[]struct{n string;p,q Point}{
  {"RED",a.Red,b.Red},{"GREEN",a.Green,b.Green},{"BLUE",a.Blue,b.Blue},{"YELLOW",a.Yellow,b.Yellow},
 }
 for _,c:=range pairs{
  if c.p.Count<100||c.q.Count<100{return "UNKNOWN",0,0,0,0,0,fmt.Errorf("MISSING_%s",c.n)}
 }
 gx,gy:=a.Blue.X-a.Green.X,a.Blue.Y-a.Green.Y
 hx,hy:=b.Blue.X-b.Green.X,b.Blue.Y-b.Green.Y
 denom:=gx*gx+gy*gy
 if denom<1600{return "UNKNOWN",0,0,0,0,0,errors.New("BASELINE_TOO_SHORT")}
 alpha:=(gx*hx+gy*hy)/denom
 beta:=(gx*hy-gy*hx)/denom
 scale:=math.Hypot(alpha,beta)
 theta:=math.Atan2(beta,alpha)
 if scale<0.80||scale>1.25||math.Abs(theta)>0.30{
  return "UNKNOWN",0,0,scale,theta,0,errors.New("SIMILARITY_OUT_OF_DOMAIN")
 }
 predict:=func(x Point)Point{
  u,v:=x.X-a.Green.X,x.Y-a.Green.Y
  return Point{X:b.Green.X+alpha*u-beta*v,Y:b.Green.Y+beta*u+alpha*v}
 }
 expectedC:=predict(a.Yellow)
 residual:=math.Hypot(expectedC.X-b.Yellow.X,expectedC.Y-b.Yellow.Y)
 if residual>3.5{return "UNKNOWN",0,0,scale,theta,residual,errors.New("THIRD_ANCHOR_RESIDUAL")}
 inv:=1.0/(alpha*alpha+beta*beta)
 ux,uy:=b.Red.X-b.Green.X,b.Red.Y-b.Green.Y
 worldX:=a.Green.X+(alpha*ux+beta*uy)*inv
 worldY:=a.Green.Y+(-beta*ux+alpha*uy)*inv
 dx,dy:=worldX-a.Red.X,worldY-a.Red.Y
 direction:="STILL"
 if math.Abs(dx)>6{
  if dx>6{direction="RIGHT"}else{direction="LEFT"}
 }
 return direction,dx,dy,scale,theta,residual,nil
}
func sha(path string)string{
 raw,err:=os.ReadFile(path);if err!=nil{return ""}
 s:=sha256.Sum256(raw);return hex.EncodeToString(s[:])
}
func main(){
 lane:=flag.String("make","","source-only experiment lane")
 folder:=flag.String("out","","new fixture output folder")
 first:=flag.String("first","","decoded frame 1")
 second:=flag.String("second","","decoded frame 2")
 expected:=flag.String("expect","","expected outcome")
 flag.Parse()
 if *lane!=""{
  if *folder==""{fmt.Fprintln(os.Stderr,"MISSING_FOLDER");os.Exit(12)}
  if err:=generate(*lane,*folder);err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(12)}
  fmt.Println("R070_NEW_SOURCE_ORIGINAL_LANE",*lane);return
 }
 r:=Receipt{Schema:"scp.r070.similarity-camera.v1",SourceSHA:os.Getenv("GITHUB_SHA"),
  Frame1SHA:sha(*first),Frame2SHA:sha(*second),Expected:*expected,
  Status:"UNKNOWN",Direction:"UNKNOWN",Scope:"THREE_STATIC_COLORED_FIDUCIALS_2D_SIMILARITY_ONLY"}
 if *first==""||*second==""||*expected==""{r.Reason="MISSING_INPUT"}else{
  a,err:=readFrame(*first)
  if err!=nil{r.Reason=err.Error()}else{
   b,e:=readFrame(*second)
   if e!=nil{r.Reason=e.Error()}else{
    var failure error
    r.Direction,r.WorldDX,r.WorldDY,r.CameraScale,r.CameraRotationRad,r.AnchorResidualPx,failure=classify(a,b)
    if failure!=nil{r.Reason=failure.Error()}else if r.Direction==*expected{r.Status="PASS_NARROW_SOURCE_ONLY"}else{r.Status="FAIL_EXPECTATION";r.Reason="DIRECTION_MISMATCH"}
   }
  }
 }
 data,_:=json.Marshal(r);fmt.Println(string(data))
 if r.Status!="PASS_NARROW_SOURCE_ONLY"{os.Exit(12)}
}
