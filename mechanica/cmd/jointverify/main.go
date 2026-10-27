// Command jointverify checks articulated mechanical glTF 2.0 joint tracks.
// Original synthetic public evidence only. No network, media decoding, private rigs
// or mechanical/physical acceptance is implied by a successful result.
package main

import (
 "crypto/sha256"
 "encoding/binary"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "math"
 "os"
 "sort"
)

type joint struct {
 Name, Kind string
 Node int
 Axis [3]float64
 MinDegrees, MaxDegrees float64
}
type manifest struct {
 Schema string
 Tracks int
 DurationSeconds int
 Rigs []struct{Name string;Joints []joint}
}
type accessor struct {
 BufferView int `json:"bufferView"`
 ByteOffset int `json:"byteOffset"`
 ComponentType int `json:"componentType"`
 Count int `json:"count"`
 Type string `json:"type"`
}
type view struct{
 ByteOffset int `json:"byteOffset"`
 ByteLength int `json:"byteLength"`
 ByteStride int `json:"byteStride"`
}
type sampler struct {
 Input int `json:"input"`
 Output int `json:"output"`
 Interpolation string `json:"interpolation"`
}
type channel struct {
 Sampler int `json:"sampler"`
 Target struct{Node int `json:"node"`; Path string `json:"path"`} `json:"target"`
}
type gltf struct {
 Accessors []accessor `json:"accessors"`
 BufferViews []view `json:"bufferViews"`
 Animations []struct{Samplers []sampler `json:"samplers"`; Channels []channel `json:"channels"`} `json:"animations"`
}
type report struct{
 Schema string `json:"schema"`
 Status string `json:"status"`
 GLBSHA256 string `json:"glb_sha256"`
 Joints int `json:"joints"`
 Revolute int `json:"revolute"`
 Continuous int `json:"continuous"`
 Keyframes int `json:"keyframes"`
}
func finite(n float64)bool{return !math.IsNaN(n)&&!math.IsInf(n,0)}

func checkQuaternion(j joint,q [4]float64)error{
 norm:=0.0
 for _,v:=range q{if !finite(v){return errors.New("QUAT_NONFINITE")};norm+=v*v}
 if math.Abs(norm-1)>0.008{return fmt.Errorf("QUAT_NONUNIT:%.8f",norm)}
 axisNorm:=math.Sqrt(j.Axis[0]*j.Axis[0]+j.Axis[1]*j.Axis[1]+j.Axis[2]*j.Axis[2])
 if !finite(axisNorm)||math.Abs(axisNorm-1)>0.001{return errors.New("AXIS_NONUNIT")}
 for _,v:=range []float64{j.MinDegrees,j.MaxDegrees}{if !finite(v){return errors.New("LIMIT_NONFINITE")}}
 if j.MinDegrees>j.MaxDegrees{return errors.New("LIMIT_REVERSED")}
 dot:=q[0]*j.Axis[0]+q[1]*j.Axis[1]+q[2]*j.Axis[2]
 transverse:=(q[0]-dot*j.Axis[0])*(q[0]-dot*j.Axis[0])+
  (q[1]-dot*j.Axis[1])*(q[1]-dot*j.Axis[1])+
  (q[2]-dot*j.Axis[2])*(q[2]-dot*j.Axis[2])
 if transverse>0.0001{return errors.New("ROTATION_AXIS_MISMATCH")}
 if j.Kind=="continuous"{return nil}
 if j.Kind!="revolute"{return errors.New("UNKNOWN_JOINT_KIND")}
 angle:=2*math.Atan2(dot,q[3])*180/math.Pi
 for angle>180{angle-=360}
 for angle< -180{angle+=360}
 if angle<j.MinDegrees-0.1||angle>j.MaxDegrees+0.1 {
  return fmt.Errorf("ANGLE_OUT_OF_LIMIT:%.4f not in [%.2f,%.2f]",angle,j.MinDegrees,j.MaxDegrees)
 }
 return nil
}
func decodeGLB(data []byte)(gltf,[]byte,error){
 var g gltf
 if len(data)<28||binary.LittleEndian.Uint32(data[:4])!=0x46546c67 ||
 binary.LittleEndian.Uint32(data[4:8])!=2 ||
 int(binary.LittleEndian.Uint32(data[8:12]))!=len(data){
  return g,nil,errors.New("INVALID_GLB_HEADER")
 }
 cursor:=12
 var bin []byte
 seenJSON:=false
 for cursor+8<=len(data){
  length:=int(binary.LittleEndian.Uint32(data[cursor:]))
  typ:=binary.LittleEndian.Uint32(data[cursor+4:])
  cursor+=8
  if length<0||length>len(data)-cursor{return g,nil,errors.New("GLB_CHUNK_BOUNDS")}
  contents:=data[cursor:cursor+length]
  if typ==0x4e4f534a{
   if seenJSON{return g,nil,errors.New("DUPLICATE_GLB_JSON")}
   if err:=json.Unmarshal(contents,&g);err!=nil{return g,nil,fmt.Errorf("GLTF_JSON:%w",err)}
   seenJSON=true
  }else if typ==0x004e4942{
   if bin!=nil{return g,nil,errors.New("DUPLICATE_GLB_BIN")}
   bin=contents
  }
  cursor+=length
 }
 if cursor!=len(data)||!seenJSON||bin==nil{return g,nil,errors.New("GLB_MISSING_CHUNKS")}
 return g,bin,nil
}
func values(g gltf,bin []byte,index int,kind string)([]float64,error){
 if index<0||index>=len(g.Accessors){return nil,errors.New("ACCESSOR_INDEX")}
 a:=g.Accessors[index]
 if a.ComponentType!=5126||a.Type!=kind||a.Count<1{return nil,errors.New("ACCESSOR_FORMAT")}
 if a.BufferView<0||a.BufferView>=len(g.BufferViews){return nil,errors.New("BUFFER_VIEW_INDEX")}
 view:=g.BufferViews[a.BufferView]
 count:=1;if kind=="VEC4"{count=4}
 size:=a.Count*count*4
 if view.ByteStride!=0{return nil,errors.New("INTERLEAVED_ACCESSOR_UNSUPPORTED")}
 start:=view.ByteOffset+a.ByteOffset
 if start<view.ByteOffset||a.ByteOffset<0||size>view.ByteLength-a.ByteOffset||
 start<0||size>len(bin)-start{return nil,errors.New("ACCESSOR_BYTE_BOUNDS")}
 out:=make([]float64,a.Count*count)
 for i:=range out{out[i]=float64(math.Float32frombits(binary.LittleEndian.Uint32(bin[start+i*4:])))}
 return out,nil
}
func qualify(m manifest,g gltf,bin []byte) (report,error){
 rep:=report{Schema:"mechanica.joint_limits.v1",Status:"FAIL"}
 if m.Schema!="mechanical.rig.v0"||m.DurationSeconds!=8||m.Tracks!=50{return rep,errors.New("MANIFEST_SCHEMA_OR_TRACK_DRIFT")}
 joints:=map[int]joint{}
 names:=map[string]bool{}
 for _,rig:=range m.Rigs{
  for _,j:=range rig.Joints{
   if _,ok:=joints[j.Node];ok||names[j.Name]||j.Name==""{return rep,errors.New("DUPLICATE_JOINT_NODE_OR_NAME")}
   names[j.Name]=true;joints[j.Node]=j
  }
 }
 if len(joints)!=m.Tracks||len(m.Rigs)!=4{return rep,errors.New("RIG_JOINT_INVENTORY")}
 if len(g.Animations)!=1{return rep,errors.New("ANIMATION_COUNT")}
 animation:=g.Animations[0]
 if len(animation.Channels)!=len(joints){return rep,errors.New("CHANNEL_COUNT")}
 seen:=map[int]bool{}
 for _,c:=range animation.Channels{
  if c.Target.Path!="rotation"{return rep,errors.New("NOT_JOINT_ROTATION")}
  j,ok:=joints[c.Target.Node];if !ok||seen[c.Target.Node]{return rep,errors.New("UNEXPECTED_OR_DUPLICATE_CHANNEL")}
  seen[c.Target.Node]=true
  if c.Sampler<0||c.Sampler>=len(animation.Samplers){return rep,errors.New("SAMPLER_INDEX")}
  s:=animation.Samplers[c.Sampler]
  if s.Interpolation!=""&&s.Interpolation!="LINEAR"{return rep,errors.New("INTERPOLATION_UNSUPPORTED")}
  ts,err:=values(g,bin,s.Input,"SCALAR");if err!=nil{return rep,fmt.Errorf("%s time: %w",j.Name,err)}
  qs,err:=values(g,bin,s.Output,"VEC4");if err!=nil{return rep,fmt.Errorf("%s rotations: %w",j.Name,err)}
  if len(qs)!=4*len(ts){return rep,errors.New("KEYFRAME_COUNT_MISMATCH")}
  for i,t:=range ts{
   if !finite(t)||t< -0.001||t>8.001||(i>0&&t<=ts[i-1]){return rep,fmt.Errorf("%s INVALID_KEY_TIMING",j.Name)}
   q:=[4]float64{qs[i*4],qs[i*4+1],qs[i*4+2],qs[i*4+3]}
   if err:=checkQuaternion(j,q);err!=nil{return rep,fmt.Errorf("%s key %d: %w",j.Name,i,err)}
   rep.Keyframes++
  }
  if math.Abs(ts[0])>0.001||math.Abs(ts[len(ts)-1]-8)>0.001{return rep,fmt.Errorf("%s TRACK_DURATION",j.Name)}
  switch j.Kind{case "revolute":rep.Revolute++;case "continuous":rep.Continuous++;default:return rep,errors.New("UNKNOWN_JOINT_KIND")}
  rep.Joints++
 }
 rep.Status="PASS"
 return rep,nil
}
func main(){
 mf:=flag.String("manifest","","public rig manifest path")
 glb:=flag.String("glb","","pinned public GLB path")
 out:=flag.String("output","","report JSON path")
 flag.Parse()
 if *mf==""||*glb==""{fmt.Fprintln(os.Stderr,"--manifest and --glb required");os.Exit(2)}
 mb,e:=os.ReadFile(*mf);if e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(1)}
 data,e:=os.ReadFile(*glb);if e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(1)}
 var m manifest
 e=json.Unmarshal(mb,&m);if e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(1)}
 g,b,e:=decodeGLB(data)
 var rep report
 if e==nil{rep,e=qualify(m,g,b)}
 rep.Schema="mechanica.joint_limits.v1"
 rep.GLBSHA256=fmt.Sprintf("%x",sha256.Sum256(data))
 if e!=nil{rep.Status="FAIL";fmt.Fprintln(os.Stderr,"first_failure:",e)}
 encoder:=json.NewEncoder(os.Stdout);encoder.SetIndent("","  ");_ = encoder.Encode(rep)
 if *out!=""{f,err:=os.Create(*out);if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)};defer f.Close();_ = json.NewEncoder(f).Encode(rep)}
 if e!=nil{os.Exit(1)}
 // Deterministically keep sorted item semantics for future report expansion.
 _ = sort.Strings
}
