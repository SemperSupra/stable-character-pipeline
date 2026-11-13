// Package shellqa supplies source-safe shell-mesh diagnostics, not acceptance.
package shellqa

import (
 "errors"
 "fmt"
 "math"
)

type Vec3 struct { X,Y,Z float64 }
type Triangle [3]int
type Mesh struct { Vertices []Vec3; Faces []Triangle }

// Count semantics are deliberately diagnostic: a surface alone cannot
// establish volumetric element orientation or absence of self-intersection.
type Receipt struct {
 Schema string `json:"schema"`
 Status string `json:"status"`
 Source string `json:"source"`
 Faces int `json:"faces"`
 Vertices int `json:"vertices"`
 LegacyRestNormalReversals int `json:"rest_normal_reversals_diagnostic_only"`
 SevereAreaCollapses int `json:"area_ratio_below_0_1"`
 MaxAbsoluteEdgeStrain float64 `json:"max_absolute_edge_length_ratio_minus_one"`
 OpposingInteriorHinges int `json:"opposing_interior_hinges_diagnostic_only"`
 ManifoldInteriorEdges int `json:"manifold_interior_edges"`
 BoundaryEdges int `json:"boundary_edges"`
 SelfIntersection string `json:"self_intersection"`
 PoseAnatomy string `json:"pose_anatomy"`
 Calibration string `json:"physical_unit_calibration"`
}

func (p Vec3) sub(q Vec3) Vec3 { return Vec3{p.X-q.X,p.Y-q.Y,p.Z-q.Z} }
func dot(p,q Vec3) float64 { return p.X*q.X+p.Y*q.Y+p.Z*q.Z }
func cross(p,q Vec3) Vec3 { return Vec3{p.Y*q.Z-p.Z*q.Y,p.Z*q.X-p.X*q.Z,p.X*q.Y-p.Y*q.X} }
func length(p Vec3) float64 { return math.Sqrt(dot(p,p)) }
func finite(p Vec3) bool { return !math.IsNaN(p.X)&&!math.IsNaN(p.Y)&&!math.IsNaN(p.Z)&&!math.IsInf(p.X,0)&&!math.IsInf(p.Y,0)&&!math.IsInf(p.Z,0) }
func faceNormal(m Mesh,t Triangle) Vec3 { return cross(m.Vertices[t[1]].sub(m.Vertices[t[0]]),m.Vertices[t[2]].sub(m.Vertices[t[0]])) }
func faceEdges(m Mesh,t Triangle) [3]float64 {
 return [3]float64{length(m.Vertices[t[1]].sub(m.Vertices[t[0]])),length(m.Vertices[t[2]].sub(m.Vertices[t[1]])),length(m.Vertices[t[0]].sub(m.Vertices[t[2]]))}
}
func normalDot(a,b Vec3) float64 {
 d:=length(a)*length(b)
 if d<1e-24 { return 1 } // collapsed faces are recorded separately
 return dot(a,b)/d
}
type edgeKey struct{ A,B int }
type edgeUse struct{ face,from,to int }
func Analyze(rest,posed Mesh) (Receipt,error) {
 r:=Receipt{Schema:"r014.shellqa.synthetic_adversarial.v1",Source:"original synthetic meshes only",
  Status:"PASS_DIAGNOSTICS_ONLY__REAL_MHR_AND_RELEASE_HOLD",
  SelfIntersection:"UNKNOWN_BVH_NOT_EXECUTED",PoseAnatomy:"UNKNOWN_NOT_TESTED",
  Calibration:"UNKNOWN_NO_SI_REFERENCE",Vertices:len(rest.Vertices),Faces:len(rest.Faces)}
 if len(rest.Vertices)<3||len(rest.Vertices)!=len(posed.Vertices)||len(rest.Faces)==0||len(rest.Faces)!=len(posed.Faces) {
  return r,errors.New("mesh topology cardinality changed")
 }
 for i,v:=range rest.Vertices { if !finite(v)||!finite(posed.Vertices[i]) {return r,fmt.Errorf("nonfinite vertex %d",i)} }
 edges:=map[edgeKey][]edgeUse{}
 n0:=make([]Vec3,len(rest.Faces));n1:=make([]Vec3,len(rest.Faces))
 for i,t:=range rest.Faces {
  if t!=posed.Faces[i] {return r,fmt.Errorf("face index/winding changed at %d",i)}
  if t[0]==t[1]||t[1]==t[2]||t[2]==t[0] {return r,fmt.Errorf("duplicate face vertex at %d",i)}
  for _,idx:=range t {if idx<0||idx>=len(rest.Vertices){return r,fmt.Errorf("out-of-range face %d",i)}}
  n0[i],n1[i]=faceNormal(rest,t),faceNormal(posed,t)
  area0,area1:=.5*length(n0[i]),.5*length(n1[i])
  if area0<1e-12 {return r,fmt.Errorf("degenerate reference face %d",i)}
  if area1<.1*area0 {r.SevereAreaCollapses++}
  if dot(n0[i],n1[i])<=0 {r.LegacyRestNormalReversals++}
  a,b:=faceEdges(rest,t),faceEdges(posed,t)
  for j:=0;j<3;j++ {
   if a[j]<1e-12{return r,fmt.Errorf("zero reference edge face %d",i)}
   if s:=math.Abs(b[j]/a[j]-1);s>r.MaxAbsoluteEdgeStrain {r.MaxAbsoluteEdgeStrain=s}
  }
  for j:=0;j<3;j++ {
   from,to:=t[j],t[(j+1)%3]
   k:=edgeKey{from,to};if k.A>k.B {k.A,k.B=k.B,k.A}
   edges[k]=append(edges[k],edgeUse{i,from,to})
  }
 }
 for k,inc:=range edges {
  if len(inc)>2 {return r,fmt.Errorf("nonmanifold edge %v",k)}
  if len(inc)==1 {r.BoundaryEdges++;continue}
  if inc[0].from!=inc[1].to||inc[0].to!=inc[1].from {
   return r,fmt.Errorf("inconsistent winding at edge %v",k)
  }
  r.ManifoldInteriorEdges++
  refCos:=normalDot(n0[inc[0].face],n0[inc[1].face])
  nowCos:=normalDot(n1[inc[0].face],n1[inc[1].face])
  if refCos>=.95&&nowCos<=-.9&&length(n1[inc[0].face])>1e-12&&length(n1[inc[1].face])>1e-12 {
   r.OpposingInteriorHinges++
  }
 }
 return r,nil
}

// Original deterministic two-triangle planar patch with a shared edge.
func Patch() Mesh {
 return Mesh{Vertices:[]Vec3{{0,0,0},{1,0,0},{0,1,0},{1,-1,0}},
  Faces:[]Triangle{{0,1,2},{1,0,3}}}
}
func Clone(m Mesh) Mesh {return Mesh{Vertices:append([]Vec3(nil),m.Vertices...),Faces:append([]Triangle(nil),m.Faces...)}}
func RotateY(m Mesh,degrees float64) Mesh {
 out:=Clone(m);a:=degrees*math.Pi/180;c,s:=math.Cos(a),math.Sin(a)
 for i,v:=range out.Vertices {out.Vertices[i]=Vec3{c*v.X+s*v.Z,v.Y,-s*v.X+c*v.Z}}
 return out
}
func Hinge(m Mesh,degrees float64) Mesh {
 out:=Clone(m);a:=degrees*math.Pi/180;c,s:=math.Cos(a),math.Sin(a)
 v:=out.Vertices[3];out.Vertices[3]=Vec3{v.X,c*v.Y-s*v.Z,s*v.Y+c*v.Z}
 return out
}
