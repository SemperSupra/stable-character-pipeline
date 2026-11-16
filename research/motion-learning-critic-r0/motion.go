// Package motion tests paired conversion on two mathematically generated planar rigs.
// It does not represent a real MakeHuman rig, video critic, or human-motion license.
package motion

import (
 "errors"
 "math"
)
type Rig struct{ Upper,Lower float64 }
type Pose struct{ Hip,Knee float64 }
type Vec struct{ X,Y float64 }
type Sample struct{ Source,Target Pose; Foot Vec; Family int }
type Metrics struct{ Count int `json:"count"`; MeanFootErrorM float64 `json:"mean_foot_error_m"`; MaxFootErrorM float64 `json:"max_foot_error_m"` }

func (r Rig) Check()error { if math.IsNaN(r.Upper)||math.IsInf(r.Upper,0)||math.IsNaN(r.Lower)||math.IsInf(r.Lower,0)||r.Upper<=0||r.Lower<=0{return errors.New("invalid rig")};return nil}
func FK(r Rig,p Pose)(Vec,error){if e:=r.Check();e!=nil{return Vec{},e};if math.IsNaN(p.Hip)||math.IsInf(p.Hip,0)||math.IsNaN(p.Knee)||math.IsInf(p.Knee,0){return Vec{},errors.New("nonfinite pose")};return Vec{r.Upper*math.Sin(p.Hip)+r.Lower*math.Sin(p.Hip+p.Knee),-r.Upper*math.Cos(p.Hip)-r.Lower*math.Cos(p.Hip+p.Knee)},nil}
func IK(r Rig,p Vec)(Pose,error){if e:=r.Check();e!=nil{return Pose{},e};if math.IsNaN(p.X)||math.IsNaN(p.Y)||math.IsInf(p.X,0)||math.IsInf(p.Y,0){return Pose{},errors.New("nonfinite target")};c:=(p.X*p.X+p.Y*p.Y-r.Upper*r.Upper-r.Lower*r.Lower)/(2*r.Upper*r.Lower);if c < -1-1e-10||c > 1+1e-10{return Pose{},errors.New("unreachable target")};c=math.Max(-1,math.Min(1,c));k:=math.Acos(c);h:=math.Atan2(p.X,-p.Y)-math.Atan2(r.Lower*math.Sin(k),r.Upper+r.Lower*math.Cos(k));return Pose{h,k},nil}
func Dataset(src,dst Rig,families,frames int)([]Sample,error){if frames<2||families<1{return nil,errors.New("invalid count")};o:=make([]Sample,0,families*frames);for f:=0;f<families;f++{phase:=0.37*float64(f);for t:=0;t<frames;t++{u:=2*math.Pi*float64(t)/float64(frames-1);s:=Pose{.23*math.Sin(u+phase)+.14*math.Cos(2*u+phase/2),.69+.19*math.Sin(u+.7*phase)+.04*math.Cos(3*u+phase)};v,e:=FK(src,s);if e!=nil{return nil,e};target,e:=IK(dst,v);if e!=nil{return nil,e};o=append(o,Sample{s,target,v,f})}};return o,nil}
func features(p Pose,d int)[]float64{if d==1{return []float64{1,p.Hip,p.Knee}};return []float64{1,p.Hip,p.Knee,p.Hip*p.Knee,p.Knee*p.Knee,p.Hip*p.Hip}}
type Regression struct{ Degree int; A,B []float64 }
func Train(samples []Sample,d int)(Regression,error){if d!=1&&d!=2{return Regression{},errors.New("bad degree")};if len(samples)<6{return Regression{},errors.New("insufficient data")};n:=len(features(samples[0].Source,d));xtx:=make([][]float64,n);for i:=range xtx{xtx[i]=make([]float64,n)};ya:=make([]float64,n);yb:=make([]float64,n);for _,s:=range samples{x:=features(s.Source,d);for i:=range x{ya[i]+=x[i]*s.Target.Hip;yb[i]+=x[i]*s.Target.Knee;for j:=range x{xtx[i][j]+=x[i]*x[j]}}};for i:=range xtx{xtx[i][i]+=1e-8};a,e:=solve(xtx,ya);if e!=nil{return Regression{},e};b,e:=solve(xtx,yb);if e!=nil{return Regression{},e};return Regression{d,a,b},nil}
func solve(src [][]float64,y []float64)([]float64,error){n:=len(y);a:=make([][]float64,n);for i:=0;i<n;i++{a[i]=append(append([]float64{},src[i]...),y[i])};for k:=0;k<n;k++{pivot:=k;for i:=k+1;i<n;i++{if math.Abs(a[i][k])>math.Abs(a[pivot][k]){pivot=i}};if math.Abs(a[pivot][k])<1e-14{return nil,errors.New("singular")};a[k],a[pivot]=a[pivot],a[k];z:=a[k][k];for j:=k;j<=n;j++{a[k][j]/=z};for i:=0;i<n;i++{if i==k{continue};z=a[i][k];for j:=k;j<=n;j++{a[i][j]-=z*a[k][j]}}};o:=make([]float64,n);for i:=range o{o[i]=a[i][n]};return o,nil}
func (m Regression)Predict(p Pose)(Pose,error){x:=features(p,m.Degree);if len(x)!=len(m.A)||len(x)!=len(m.B){return Pose{},errors.New("invalid model")};o:=Pose{};for i:=range x{o.Hip+=x[i]*m.A[i];o.Knee+=x[i]*m.B[i]};if math.IsNaN(o.Hip)||math.IsNaN(o.Knee){return Pose{},errors.New("nan")};return o,nil}
func Evaluate(samples []Sample,r Rig,predict func(Pose)(Pose,error))(Metrics,error){m:=Metrics{Count:len(samples)};if m.Count==0{return m,errors.New("empty test")};for _,s:=range samples{q,e:=predict(s.Source);if e!=nil{return m,e};v,e:=FK(r,q);if e!=nil{return m,e};d:=math.Hypot(v.X-s.Foot.X,v.Y-s.Foot.Y);m.MeanFootErrorM+=d;m.MaxFootErrorM=math.Max(m.MaxFootErrorM,d)};m.MeanFootErrorM/=float64(m.Count);return m,nil}
type Finding struct{ Status,Kind,ModelID string; StartFrame,EndFrame int; Confidence float64 }
func Adjudicate(m Metrics,limit float64,f Finding)string{if m.Count<1||math.IsNaN(m.MeanFootErrorM)||math.IsInf(m.MeanFootErrorM,0)||math.IsNaN(m.MaxFootErrorM)||math.IsInf(m.MaxFootErrorM,0)||limit<=0{return "REJECT_INVALID_METRIC"};if m.MaxFootErrorM>limit{return "HARD_GEOMETRY_FAIL"};if f.Status!="OBSERVED"||f.ModelID==""||math.IsNaN(f.Confidence)||math.IsInf(f.Confidence,0)||f.Confidence<0||f.Confidence>1||f.StartFrame<0||f.EndFrame<f.StartFrame{return "CRITIC_UNVERIFIED"};if f.Kind=="defect"{return "REVIEW_CORRECTION"};return "NUMERIC_PASS_VISUAL_UNQUALIFIED"}
