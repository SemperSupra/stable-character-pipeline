package main
// Separate stdlib-only independently authored numerical oracle.
import(
 "encoding/json"
 "fmt"
 "math"
 "os"
 "runtime"
)
type Point struct{ID string `json:"id"`; XYZ [3]float64 `json:"xyz"`; Value float64 `json:"value"`}
type Input struct{Donor string `json:"donor"`;InvalidRejected bool `json:"invalid_rejected"`;Points []Point `json:"points"`}
type Receipt struct{Status string `json:"status"`;OS string `json:"os"`;Arch string `json:"arch"`;Cases int `json:"cases"`;MaxError float64 `json:"max_abs_error"`;Failures []string `json:"failures"`}
func independent(p [3]float64) float64{
 sphere:=math.Sqrt(p[0]*p[0]+p[1]*p[1]+p[2]*p[2])-1
 q:=[3]float64{math.Abs(p[0])-1.4,math.Abs(p[1])-0.25,math.Abs(p[2])-0.25}
 outside:=math.Sqrt(math.Pow(math.Max(q[0],0),2)+math.Pow(math.Max(q[1],0),2)+math.Pow(math.Max(q[2],0),2))
 box:=outside+math.Min(math.Max(q[0],math.Max(q[1],q[2])),0)
 return math.Min(sphere,box)
}
func main(){
 if len(os.Args)!=2{panic("expected JSON argument")}
 f,e:=os.Open(os.Args[1]);if e!=nil{panic(e)};defer f.Close()
 var data Input
 if e=json.NewDecoder(f).Decode(&data);e!=nil{panic(e)}
 r:=Receipt{Status:"PASS",OS:runtime.GOOS,Arch:runtime.GOARCH,Cases:len(data.Points)}
 if data.Donor!="sdfx"{r.Failures=append(r.Failures,"wrong donor")}
 if !data.InvalidRejected{r.Failures=append(r.Failures,"invalid sphere accepted")}
 if len(data.Points)!=12{r.Failures=append(r.Failures,"sample count")}
 for i,p:=range data.Points{
  if p.ID!=fmt.Sprintf("p%02d",i){r.Failures=append(r.Failures,"sample id")}
  if !isFinite(p.Value){r.Failures=append(r.Failures,"nonfinite");continue}
  delta:=math.Abs(p.Value-independent(p.XYZ))
  r.MaxError=math.Max(r.MaxError,delta)
  if delta>1e-11{r.Failures=append(r.Failures,"analytic residual")}
 }
 if len(r.Failures)>0{r.Status="FAIL"}
 enc:=json.NewEncoder(os.Stdout);if e=enc.Encode(r);e!=nil{panic(e)}
 if r.Status!="PASS"{os.Exit(1)}
}
func isFinite(x float64)bool{return !math.IsNaN(x)&&!math.IsInf(x,0)}
