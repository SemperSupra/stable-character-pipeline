// Package diaphragm provides non-destructive synthetic mesh-interface diagnostics.
// It never removes source faces or asserts whether an interface is anatomical.
package diaphragm

import (
 "fmt"
 "sort"
)

type Face struct { A, B, C int }
type Edge struct { A, B int }
type OppositePair struct { First, Second int }
type Report struct {
 OppositePairs []OppositePair
 FourFaceEdges []Edge
 OtherNonmanifoldEdges []Edge
 TotalFaces int
}

func edge(a,b int) Edge { if b<a { a,b=b,a }; return Edge{a,b} }
func cyclic(f Face) [3]int {
 candidates := [][3]int{{f.A,f.B,f.C},{f.B,f.C,f.A},{f.C,f.A,f.B}}
 sort.Slice(candidates,func(i,j int)bool {
  for k:=0;k<3;k++ { if candidates[i][k]!=candidates[j][k] {return candidates[i][k]<candidates[j][k]} };return false
 })
 return candidates[0]
}
func reverse(f Face) Face {return Face{f.A,f.C,f.B}}

// Inspect identifies candidates, preserving source face indices.
// Matching opposite winding is deliberately NOT authority to delete either face.
func Inspect(faces []Face) (Report,error) {
 report:=Report{TotalFaces:len(faces)}
 seen:=map[[3]int][]int{}
 incidence:=map[Edge]int{}
 for i,f:=range faces {
  if f.A<0 || f.B<0 || f.C<0 || f.A==f.B || f.B==f.C || f.C==f.A {return Report{},fmt.Errorf("invalid face %d",i)}
  key:=cyclic(f)
  reversed:=cyclic(reverse(f))
  for _,j:=range seen[reversed] { report.OppositePairs=append(report.OppositePairs,OppositePair{j,i}) }
  seen[key]=append(seen[key],i)
  for _,e:=range []Edge{edge(f.A,f.B),edge(f.B,f.C),edge(f.C,f.A)} {incidence[e]++}
 }
 for e,n:=range incidence {
  if n==4 { report.FourFaceEdges=append(report.FourFaceEdges,e) }
  if n>2 && n!=4 { report.OtherNonmanifoldEdges=append(report.OtherNonmanifoldEdges,e) }
 }
 sort.Slice(report.FourFaceEdges,func(i,j int)bool {a,b:=report.FourFaceEdges[i],report.FourFaceEdges[j];if a.A==b.A{return a.B<b.B};return a.A<b.A})
 sort.Slice(report.OtherNonmanifoldEdges,func(i,j int)bool {a,b:=report.OtherNonmanifoldEdges[i],report.OtherNonmanifoldEdges[j];if a.A==b.A{return a.B<b.B};return a.A<b.A})
 return report,nil
}
