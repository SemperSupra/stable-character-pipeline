// Package framecustody makes inter-atlas source units, axes and
// transformations explicit. It never infers anatomy from bounding boxes.
package framecustody
import(
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "math"
 "sort"
)
const Schema="scp.anatomy.frames.v1"
type Point struct{X float64 `json:"x"`;Y float64 `json:"y"`;Z float64 `json:"z"`}
type Frame struct{
 ID string `json:"id"`
 Dataset string `json:"dataset"`
 Version string `json:"version"`
 SourceSHA256 string `json:"source_sha256"`
 Units string `json:"units"`
 UnitEvidenceSHA256 string `json:"unit_evidence_sha256"`
 Axes string `json:"axes"`
 AxisEvidenceSHA256 string `json:"axis_evidence_sha256"`
 Laterality string `json:"laterality"`
}
type Edge struct{
 From string `json:"from"`
 To string `json:"to"`
 Kind string `json:"kind"`
 Matrix [4][4]float64 `json:"matrix"`
 Review string `json:"review"`
 SourceEvidenceSHA256 string `json:"source_evidence_sha256"`
 LandmarkEvidenceSHA256 string `json:"landmark_evidence_sha256"`
}
type Graph struct{
 Schema string `json:"schema"`
 Frames []Frame `json:"frames"`
 Edges []Edge `json:"edges"`
}
type Receipt struct{
 Schema string `json:"schema"`
 Status string `json:"status"`
 From string `json:"from"`
 To string `json:"to"`
 Path []string `json:"path"`
 Matrix [4][4]float64 `json:"matrix"`
 ProvenanceDigest string `json:"provenance_digest"`
 Reason string `json:"reason"`
}
func finite(x float64)bool{return !math.IsInf(x,0)&&!math.IsNaN(x)}
func sha(s string)bool{
 if len(s)!=64{return false}
 for _,r:=range s{if !(r>='0'&&r<='9'||r>='a'&&r<='f'){return false}}
 return true
}
func identity()[4][4]float64{
 return [4][4]float64{{1,0,0,0},{0,1,0,0},{0,0,1,0},{0,0,0,1}}
}
func product(a,b [4][4]float64)[4][4]float64{
 var c [4][4]float64
 for i:=0;i<4;i++{for j:=0;j<4;j++{for k:=0;k<4;k++{c[i][j]+=a[i][k]*b[k][j]}}}
 return c
}
func Apply(m [4][4]float64,p Point)Point{
 return Point{
 X:m[0][0]*p.X+m[0][1]*p.Y+m[0][2]*p.Z+m[0][3],
 Y:m[1][0]*p.X+m[1][1]*p.Y+m[1][2]*p.Z+m[1][3],
 Z:m[2][0]*p.X+m[2][1]*p.Y+m[2][2]*p.Z+m[2][3],
 }
}
func determinant(m [4][4]float64)float64{
 return m[0][0]*(m[1][1]*m[2][2]-m[1][2]*m[2][1])-
 m[0][1]*(m[1][0]*m[2][2]-m[1][2]*m[2][0])+
 m[0][2]*(m[1][0]*m[2][1]-m[1][1]*m[2][0])
}
func uniformScale(m [4][4]float64)(float64,error){
 for i:=0;i<4;i++{for j:=0;j<4;j++{if !finite(m[i][j]){return 0,errors.New("NONFINITE_TRANSFORM")}}}
 if math.Abs(m[3][0])+math.Abs(m[3][1])+math.Abs(m[3][2])+math.Abs(m[3][3]-1)>1e-10{
  return 0,errors.New("NON_AFFINE_TRANSFORM")
 }
 cols:=[3]Point{
 {X:m[0][0],Y:m[1][0],Z:m[2][0]},
 {X:m[0][1],Y:m[1][1],Z:m[2][1]},
 {X:m[0][2],Y:m[1][2],Z:m[2][2]},
 }
 length:=func(p Point)float64{return math.Sqrt(p.X*p.X+p.Y*p.Y+p.Z*p.Z)}
 dot:=func(a,b Point)float64{return a.X*b.X+a.Y*b.Y+a.Z*b.Z}
 scale:=(length(cols[0])+length(cols[1])+length(cols[2]))/3
 if scale<.0001||scale>10000{return 0,errors.New("INVALID_UNIT_SCALE")}
 for _,c:=range cols{if math.Abs(length(c)-scale)>scale*1e-6{return 0,errors.New("NONUNIFORM_SCALE")}}
 for i:=0;i<3;i++{for j:=i+1;j<3;j++{if math.Abs(dot(cols[i],cols[j]))>scale*scale*1e-6{
  return 0,errors.New("SHEARED_AXIS_BASIS")
 }}}
 if determinant(m)<=0{return 0,errors.New("MIRRORED_COORDINATE_FRAME")}
 if math.Abs(determinant(m)-scale*scale*scale)>scale*scale*scale*1e-6{
  return 0,errors.New("INVALID_BASIS_DETERMINANT")
 }
 return scale,nil
}
func unitFactor(from,to string)(float64,error){
 switch from{
 case "mm":
  if to=="mm"{return 1,nil}
  if to=="m"{return .001,nil}
 case "m":
  if to=="mm"{return 1000,nil}
  if to=="m"{return 1,nil}
 }
 return 0,errors.New("UNKNOWN_OR_UNREVIEWED_SOURCE_UNITS")
}
func knownFrame(f Frame)error{
 if f.ID==""||f.Dataset==""||f.Version==""||!sha(f.SourceSHA256){return errors.New("FRAME_SOURCE_IDENTITY_MISSING")}
 if f.Units!="m"&&f.Units!="mm"{return errors.New("FRAME_UNITS_UNKNOWN")}
 if !sha(f.UnitEvidenceSHA256)||!sha(f.AxisEvidenceSHA256){return errors.New("FRAME_UNIT_OR_AXIS_EVIDENCE_MISSING")}
 if f.Axes!="Z_UP"&&f.Axes!="Y_UP"{return errors.New("UNVERIFIED_OR_UNSUPPORTED_AXIS_MODEL")}
 if f.Laterality!="X_POS_LEFT"&&f.Laterality!="X_POS_RIGHT"{return errors.New("LATERALITY_CONVENTION_UNVERIFIED")}
 return nil
}
func Validate(g Graph)error{
 if g.Schema!=Schema||len(g.Frames)<2||len(g.Frames)>64||len(g.Edges)>128{
  return errors.New("INVALID_FRAME_GRAPH_SCHEMA_OR_SIZE")
 }
 frame:=map[string]Frame{}
 for _,f:=range g.Frames{
  if e:=knownFrame(f);e!=nil{return e}
  if _,ok:=frame[f.ID];ok{return errors.New("DUPLICATE_FRAME_ID")}
  frame[f.ID]=f
 }
 edges:=map[string]bool{}
 for _,e:=range g.Edges{
  a,okA:=frame[e.From];b,okB:=frame[e.To]
  if !okA||!okB||e.From==e.To{return errors.New("UNKNOWN_OR_SELF_TRANSFORM")}
  key:=e.From+"|"+e.To
  if edges[key]{return errors.New("DUPLICATE_TRANSFORM")}
  edges[key]=true
  if !sha(e.SourceEvidenceSHA256){return errors.New("MISSING_TRANSFORM_SOURCE_EVIDENCE")}
  s,err:=uniformScale(e.Matrix);if err!=nil{return err}
  expected,err:=unitFactor(a.Units,b.Units);if err!=nil{return err}
  switch e.Kind{
  case "UNIT_AXIS_CONVERSION":
   if e.Review!="SOURCE_VERIFIED"{return errors.New("UNIT_AXIS_CONVERSION_UNREVIEWED")}
   if math.Abs(s-expected)>1e-8*expected{return errors.New("UNIT_CONVERSION_MISMATCH")}
  case "SAME_ATLAS_REFERENCE":
   if a.Dataset!=b.Dataset||a.Version!=b.Version||e.Review!="SOURCE_VERIFIED"{
    return errors.New("CROSS_ATLAS_CANNOT_CLAIM_SAME_REFERENCE")
   }
   if math.Abs(s-expected)>1e-8*expected{return errors.New("SAME_ATLAS_UNIT_MISMATCH")}
  case "CROSS_ATLAS_REGISTRATION":
   if e.Review!="SOURCE_VERIFIED"||!sha(e.LandmarkEvidenceSHA256){
    return errors.New("CROSS_ATLAS_LANDMARK_REGISTRATION_NOT_REVIEWED")
   }
  default:
   return errors.New("UNKNOWN_TRANSFORM_KIND")
  }
  // No unsupported flip of native anatomical left/right conventions.
  // A changing convention is allowed only through an explicitly source-backed
  // registration with independent landmark validation, not a unit converter.
  if a.Laterality!=b.Laterality&&e.Kind!="CROSS_ATLAS_REGISTRATION"{
   return errors.New("LATERALITY_CONVENTION_CHANGED_SILENTLY")
  }
 }
 return nil
}
func Resolve(g Graph,from,to string)(Receipt,error){
 receipt:=Receipt{Schema:Schema,Status:"HOLD_NO_VALID_SOURCE_FRAME_PATH",From:from,To:to,Path:[]string{},Reason:"All transforms are geometrical/provenance candidates, not medical anatomical registration"}
 if e:=Validate(g);e!=nil{return receipt,e}
 if from==to||from==""||to==""{return receipt,errors.New("INVALID_SOURCE_DESTINATION")}
 found:=map[string]bool{}
 for _,f:=range g.Frames{found[f.ID]=true}
 if !found[from]||!found[to]{return receipt,errors.New("UNKNOWN_FRAME")}
 adj:=map[string][]Edge{}
 for _,e:=range g.Edges{adj[e.From]=append(adj[e.From],e)}
 for k:=range adj{sort.Slice(adj[k],func(i,j int)bool{return adj[k][i].To<adj[k][j].To})}
 type State struct{node string;path []string;mat [4][4]float64}
 queue:=[]State{{node:from,path:[]string{from},mat:identity()}}
 solutions:=[]State{}
 for len(queue)>0{
  state:=queue[0];queue=queue[1:]
  if state.node==to{solutions=append(solutions,state);continue}
  if len(state.path)>=len(g.Frames){continue}
  for _,edge:=range adj[state.node]{
   cycle:=false
   for _,old:=range state.path{if old==edge.To{cycle=true}}
   if cycle{continue}
   next:=State{node:edge.To,path:append(append([]string{},state.path...),edge.To),mat:product(edge.Matrix,state.mat)}
   queue=append(queue,next)
   if len(queue)>10000{return receipt,errors.New("FRAME_GRAPH_PATH_EXPLOSION")}
  }
 }
 if len(solutions)==0{return receipt,errors.New("MISSING_VERIFIED_FRAME_PATH")}
 if len(solutions)>1{return receipt,errors.New("AMBIGUOUS_MULTIPLE_TRANSFORM_PATHS")}
 receipt.Status="PROVENANCE_GATED_COORDINATE_TRANSFORM_ONLY"
 receipt.Matrix=solutions[0].mat
 receipt.Path=solutions[0].path
 raw,_:=json.Marshal(struct{Graph Graph;Path []string}{g,receipt.Path})
 h:=sha256.Sum256(raw)
 receipt.ProvenanceDigest=hex.EncodeToString(h[:])
 return receipt,nil
}
