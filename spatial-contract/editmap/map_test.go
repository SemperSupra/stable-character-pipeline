package editmap
import(
 "testing"
 "example.invalid/spatial-contract/avsync"
)
func sec(n,d int64) avsync.Seconds{return avsync.Seconds{Numerator:n,Denominator:d}}
func fixture() []Span{
 return []Span{
  {0,2400,0},{4000,5600,2400},{7000,7600,4000},{9600,11000,4600},
 }
}
func vfr()[][]avsync.Seconds{
 return [][]avsync.Seconds{
  {sec(0,48000),sec(400,48000),sec(1100,48000),sec(1800,48000),sec(2400,48000),sec(2500,48000),sec(3900,48000),sec(4600,48000),sec(5400,48000),sec(5800,48000)},
  {sec(0,48000),sec(1000,48000),sec(2100,48000),sec(3100,48000),sec(4250,48000),sec(5100,48000),sec(5800,48000)},
  {sec(0,48000),sec(650,48000),sec(1650,48000),sec(2450,48000),sec(3400,48000),sec(4550,48000),sec(5800,48000)},
 }
}
func TestEditCuesAcrossThreeVFRPatterns(t *testing.T) {
 spans:=fixture()
 cases:=[]struct{source,output int64;kept bool}{
  {48,48,true},{2399,2399,true},{3000,0,false},{4000,2400,true},
  {4200,2600,true},{5500,3900,true},{6000,0,false},
  {7400,4400,true},{8500,0,false},{9800,4800,true},{10999,5999,true},
 }
 for variant,pts:=range vfr(){
  for _,tc:=range cases{
   got,err:=Map(spans,pts,tc.source)
   if err!=nil{t.Fatalf("pattern %d source %d err %v",variant,tc.source,err)}
   if got.Cut==tc.kept{t.Fatalf("cut flag pattern %d %+v",variant,got)}
   if tc.kept{
    if got.DestinationSample!=tc.output{t.Fatalf("sample shift pattern %d %+v wanted %d",variant,got,tc.output)}
    frame,err:=FrameContaining(pts,6000,tc.output)
    if err!=nil||got.DestinationVideoFrame!=frame{
     t.Fatalf("VFR containing frame mismatch pattern %d %+v",variant,got)
    }
   }else if got.DestinationVideoFrame!=-1{t.Fatal("dropped event mapped into video")}
  }
 }
}
func TestRefuseUnqualifiedEdits(t *testing.T){
 bad:=[][]Span{
  {},{{0,0,0}},{{0,2400,1}},{{0,2400,0},{2000,3000,2400}},
  {{0,2400,0},{4000,5600,2500}},{{-1,2400,0}},
  {{0,Bound+1,0}},{{0,2400,0},{4000,3900,2400}},
 }
 for i,spans:=range bad{
  if ValidateSpans(spans)==nil{t.Fatalf("accepted bad edit %d",i)}
 }
 for _,src:=range []int64{-1}{
  if _,_,err:=AtSource(fixture(),src);err==nil{t.Fatal("accepted negative sample")}
 }
}
func TestRefuseVFRDuplicatesReorderGapsOrBadBounds(t *testing.T){
 for _,times:=range [][]avsync.Seconds{
  {},{sec(0,0)},{sec(1,48000)},{sec(0,48000),sec(0,48000)},
  {sec(0,48000),sec(3000,48000),sec(2000,48000)},
  {sec(0,48000),sec(6000,48000)},
  {sec(0,48000),sec(3000,0)},
  {sec(0,48000),sec(3000,-48000)},
  {sec(0,48000),sec(3000,1000001)},
 }{
  if ValidateVFR(times,6000)==nil{t.Fatalf("accepted invalid VFR %+v",times)}
 }
 if _,err:=FrameContaining(vfr()[0],6000,6000);err==nil{t.Fatal("accepted overlong cue")}
}
func TestVFRHalfSamplePrecisionAndRationalEquivalence(t *testing.T){
 pts:=[]avsync.Seconds{sec(0,48000),sec(1,96000),sec(3,96000),sec(5,96000),sec(7,96000)}
 if err:=ValidateVFR(pts,4);err!=nil{t.Fatalf("exact half-sample VFR rejected %v",err)}
 got,err:=FrameContaining(pts,4,0)
 if err!=nil||got!=0{t.Fatalf("exact zero frame %+v %v",got,err)}
 got,err=FrameContaining(pts,4,1)
 if err!=nil||got!=1{t.Fatalf("containing half-frame %+v %v",got,err)}
}
