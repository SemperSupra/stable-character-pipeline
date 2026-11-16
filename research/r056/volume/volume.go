// Package volume implements a bounded synthetic signed-volume and edge-orientation oracle.
// Values are in uncalibrated input coordinate units cubed; never physiological volumes.
package volume

import ("fmt";"math")
type V struct {X,Y,Z float64}
type Face struct {A,B,C int}
type Edge struct {A,B int}
func sub(a,b V)V{return V{a.X-b.X,a.Y-b.Y,a.Z-b.Z}}
func dot(a,b V)float64{return a.X*b.X+a.Y*b.Y+a.Z*b.Z}
func cross(a,b V)V{return V{a.Y*b.Z-a.Z*b.Y,a.Z*b.X-a.X*b.Z,a.X*b.Y-a.Y*b.X}}
func edge(a,b int)Edge{if a>b{return Edge{b,a}};return Edge{a,b}}
func Signed(vertices []V,faces []Face,origin V)(float64,error){
 if len(vertices)==0 ||len(faces)==0{return 0,fmt.Errorf("empty surface")}
 for _,v:=range append(append([]V{},vertices...),origin){if math.IsNaN(v.X)||math.IsInf(v.X,0)||math.IsNaN(v.Y)||math.IsInf(v.Y,0)||math.IsNaN(v.Z)||math.IsInf(v.Z,0){return 0,fmt.Errorf("nonfinite coordinate")}}
 edgeBalance:=map[Edge]int{}
 edgeCount:=map[Edge]int{}
 sum,correction:=0.0,0.0
 for i,f:=range faces {
  if f.A<0||f.B<0||f.C<0||f.A>=len(vertices)||f.B>=len(vertices)||f.C>=len(vertices)||f.A==f.B||f.B==f.C||f.C==f.A{return 0,fmt.Errorf("invalid face %d",i)}
  for _,e:=range [][2]int{{f.A,f.B},{f.B,f.C},{f.C,f.A}}{
   k:=edge(e[0],e[1]);edgeCount[k]++;if e[0]<e[1]{edgeBalance[k]++}else{edgeBalance[k]--}
  }
  a,b,c:=sub(vertices[f.A],origin),sub(vertices[f.B],origin),sub(vertices[f.C],origin)
  term:=dot(a,cross(b,c))/6
  y:=term-correction;t:=sum+y;correction=(t-sum)-y;sum=t
 }
 for k,n:=range edgeCount {if n!=2||edgeBalance[k]!=0{return 0,fmt.Errorf("nonclosed or inconsistent edge %+v: incidence=%d balance=%d",k,n,edgeBalance[k])}}
 if math.IsNaN(sum)||math.IsInf(sum,0){return 0,fmt.Errorf("nonfinite volume")}
 return sum,nil
}
