package main

// Converts documentary-captioned NASA video 2D landmark estimates into a camera-plane
// animated glTF 2.0 skin. This is not 3D anatomy, depth estimation, or identity.
import (
  "crypto/sha256"
  "encoding/binary"
  "encoding/json"
  "errors"
  "flag"
  "fmt"
  "math"
  "os"
  "path/filepath"
  "sort"
)

type Landmark struct {
  X float64 `json:"x"`
  Y float64 `json:"y"`
  Z float64 `json:"z"`
  Visibility float64 `json:"visibility"`
}
type Frame struct {
  Index int `json:"frame"`
  SourceTimeMS int `json:"source_video_offset_ms"`
  Landmarks []Landmark `json:"landmarks2d"`
}
type SourceReceipt struct {
  Media map[string]struct { Bytes int `json:"bytes"`; SHA1 string `json:"sha1"` } `json:"media"`
  Model struct { SHA256 string `json:"sha256"` } `json:"model"`
}
const originalVideoSHA1 = "dfc000088cfff728b57fe0c8ae38a7266410caeb"
const officialTaskSHA256 = "59929e1d1ee95287735ddd833b19cf4ac46d29bc7afddbbf6753c459690d574a"

// Human topology is explicit and finite. These are MediaPipe landmark indices,
// not a biomechanically fitted pelvis/spine skeleton.
var parent = [33]int{
  11,0,1,2,0,4,5,3,6,0,0,
  23,24,11,12,13,14,15,16,15,16,15,16,
  -1,-1,23,24,25,26,27,28,29,30,
}
var segments = [][2]int{
  {11,12},{11,13},{13,15},{12,14},{14,16},
  {23,24},{11,23},{12,24},{23,25},{25,27},
  {24,26},{26,28},{0,11},{0,12},
  {15,17},{15,19},{15,21},{16,18},{16,20},{16,22},
  {27,29},{29,31},{28,30},{30,32},
}
func finite(v float64) bool { return !math.IsNaN(v) && !math.IsInf(v,0) }
func validate(frames []Frame) error {
  if len(frames) != 30 { return fmt.Errorf("expected fixed 30 source frames, got %d",len(frames)) }
  for i,f := range frames {
    if f.Index != i || f.SourceTimeMS != 11000+i*1000 {
      return fmt.Errorf("source clock discontinuity/index mismatch at frame %d",i)
    }
    if len(f.Landmarks)!=0 && len(f.Landmarks)!=33 {
      return fmt.Errorf("partial skeleton at source frame %d",i)
    }
    for j,p:=range f.Landmarks {
      if !finite(p.X)||!finite(p.Y)||!finite(p.Z)||!finite(p.Visibility) {
        return fmt.Errorf("nonfinite landmark at %d/%d",i,j)
      }
      if p.X < -1.5 || p.X > 2.5 || p.Y < -1.5 || p.Y > 2.5 ||
        p.Z < -10 || p.Z > 10 || p.Visibility < 0 || p.Visibility > 1 {
        return fmt.Errorf("invalid model output bounds at %d/%d",i,j)
      }
    }
  }
  return nil
}
func longestRun(frames []Frame) (int,int,error) {
  if err:=validate(frames);err!=nil{return 0,0,err}
  bestStart,bestLen:=0,0
  for i:=0;i<len(frames);{
    if len(frames[i].Landmarks)!=33 {i++;continue}
    j:=i+1
    for j<len(frames)&&len(frames[j].Landmarks)==33 {j++}
    if j-i>bestLen{bestStart,bestLen=i,j-i}
    i=j
  }
  if bestLen<2{return 0,0,errors.New("no two-frame continuous observed pose interval")}
  return bestStart,bestLen,nil
}
func xy(p Landmark) [3]float32 {
  // 16:9 reference image, arbitrary display units, Z intentionally fixed to ZERO.
  return [3]float32{float32((p.X-.5)*3.55555556),float32((.5-p.Y)*2),0}
}
func sub(a,b [3]float32)[3]float32{return [3]float32{a[0]-b[0],a[1]-b[1],a[2]-b[2]}}
type binBuilder struct {
  data []byte
  views []map[string]any
  accessors []map[string]any
}
func (b *binBuilder) append(raw []byte, target int)(int,int){
  for len(b.data)%4!=0 {b.data=append(b.data,0)}
  start:=len(b.data); b.data=append(b.data,raw...)
  v:=map[string]any{"buffer":0,"byteOffset":start,"byteLength":len(raw)}
  if target!=0{v["target"]=target}
  b.views=append(b.views,v)
  return len(b.views)-1,start
}
func f32(vals []float32) []byte {
  out:=make([]byte,len(vals)*4)
  for i,v:=range vals {binary.LittleEndian.PutUint32(out[i*4:],math.Float32bits(v))}
  return out
}
func u16(vals []uint16) []byte {
  out:=make([]byte,len(vals)*2)
  for i,v:=range vals {binary.LittleEndian.PutUint16(out[i*2:],v)}
  return out
}
func u32(vals []uint32) []byte {
  out:=make([]byte,len(vals)*4)
  for i,v:=range vals {binary.LittleEndian.PutUint32(out[i*4:],v)}
  return out
}
func (b *binBuilder) accessor(raw []byte, typ string, component,count,target int, min,max []float32)int{
  view,_:=b.append(raw,target)
  a:=map[string]any{"bufferView":view,"componentType":component,"count":count,"type":typ}
  if min!=nil{a["min"]=min};if max!=nil{a["max"]=max}
  b.accessors=append(b.accessors,a)
  return len(b.accessors)-1
}
func verifyReceipt(data []byte)error{
  var r SourceReceipt
  if err:=json.Unmarshal(data,&r);err!=nil{return err}
  v,ok:=r.Media["video"]
  if !ok || v.Bytes!=10680037 || v.SHA1!=originalVideoSHA1{
    return errors.New("NASA original video source proof mismatch")
  }
  if r.Model.SHA256!=officialTaskSHA256{return errors.New("pinned task model checksum mismatch")}
  return nil
}
func createGLB(frames []Frame)([]byte,map[string]any,error){
  start,n,err:=longestRun(frames);if err!=nil{return nil,nil,err}
  b:=&binBuilder{}
  nodes:=make([]map[string]any,34)
  // Root-pose global coordinates and per-frame relative translations.
  absolute:=make([][][3]float32,n)
  for i:=0;i<n;i++{
    absolute[i]=make([][3]float32,33)
    for j,p:=range frames[start+i].Landmarks{absolute[i][j]=xy(p)}
  }
  children:=make([][]int,33)
  sceneRoots:=[]int{33}
  for j,p:=range parent{
    if p>=0{children[p]=append(children[p],j)}
    else {sceneRoots=append(sceneRoots,j)}
  }
  for j,p:=range parent {
    t:=absolute[0][j]
    if p>=0 {t=sub(t,absolute[0][p])}
    node:=map[string]any{"name":fmt.Sprintf("mp_landmark_%02d",j),"translation":t}
    if len(children[j])>0 {sort.Ints(children[j]);node["children"]=children[j]}
    nodes[j]=node
  }
  // A genuinely skinned 3D thin-beam mannequin. Each segment has bind-pose
  // endpoints weighted 100% to its own joint. This is not a recovered body mesh.
  var positions []float32
  var joints []uint16
  var weights []float32
  var indices []uint32
  lo:=[3]float32{999,999,999};hi:=[3]float32{-999,-999,-999}
  for _,edge:=range segments{
    a,c:=absolute[0][edge[0]],absolute[0][edge[1]]
    d:=sub(c,a)
    length:=float32(math.Hypot(float64(d[0]),float64(d[1])))
    if length<.001 {continue}
    nx,ny:= -d[1]/length*.014,d[0]/length*.014
    offsets:=[4][3]float32{{nx,ny,.014},{-nx,-ny,.014},{-nx,-ny,-.014},{nx,ny,-.014}}
    base:=uint32(len(positions)/3)
    for endpoint,pt:=range [2][3]float32{a,c}{
      bone:=uint16(edge[endpoint])
      for _,off:=range offsets{
        v:=[3]float32{pt[0]+off[0],pt[1]+off[1],pt[2]+off[2]}
        for k:=0;k<3;k++{positions=append(positions,v[k]);if v[k]<lo[k]{lo[k]=v[k]};if v[k]>hi[k]{hi[k]=v[k]}}
        joints=append(joints,bone,0,0,0)
        weights=append(weights,1,0,0,0)
      }
    }
    for k:=uint32(0);k<4;k++{
      next:=(k+1)%4
      indices=append(indices,base+k,base+next,base+4+next,base+k,base+4+next,base+4+k)
    }
  }
  if len(indices)==0{return nil,nil,errors.New("no nondegenerate skin segments")}
  posA:=b.accessor(f32(positions),"VEC3",5126,len(positions)/3,34962,lo[:],hi[:])
  jointsA:=b.accessor(u16(joints),"VEC4",5123,len(joints)/4,34962,nil,nil)
  weightsA:=b.accessor(f32(weights),"VEC4",5126,len(weights)/4,34962,nil,nil)
  indicesA:=b.accessor(u32(indices),"SCALAR",5125,len(indices),34963,nil,nil)
  ibm:=make([]float32,0,33*16)
  for j:=0;j<33;j++{
    t:=absolute[0][j]
    ibm=append(ibm,1,0,0,0,0,1,0,0,0,0,1,0,-t[0],-t[1],-t[2],1)
  }
  ibmA:=b.accessor(f32(ibm),"MAT4",5126,33,0,nil,nil)
  times:=make([]float32,n)
  for k:=range times{times[k]=float32(k)}
  timeA:=b.accessor(f32(times),"SCALAR",5126,n,0,[]float32{0},[]float32{float32(n-1)})
  samplers:=make([]map[string]any,0,33)
  channels:=make([]map[string]any,0,33)
  for j,p:=range parent{
    translations:=make([]float32,0,n*3)
    for f:=0;f<n;f++{
      tr:=absolute[f][j]
      if p>=0{tr=sub(tr,absolute[f][p])}
      translations=append(translations,tr[:]...)
    }
    out:=b.accessor(f32(translations),"VEC3",5126,n,0,nil,nil)
    samplers=append(samplers,map[string]any{"input":timeA,"output":out,"interpolation":"LINEAR"})
    channels=append(channels,map[string]any{
      "sampler":len(samplers)-1,"target":map[string]any{"node":j,"path":"translation"}})
  }
  jointIDs:=make([]int,33)
  for i:=range jointIDs{jointIDs[i]=i}
  nodes[33]=map[string]any{"name":"SOURCE_ESTIMATED_CAMERA_PLANE_SKIN","mesh":0,"skin":0}
  root:=map[string]any{
    "asset":map[string]any{"version":"2.0","generator":"stable-character R3 Go camera-plane skin exporter"},
    "scene":0,"scenes":[]any{map[string]any{"nodes":sceneRoots}},
    "nodes":nodes,
    "meshes":[]any{map[string]any{"name":"NOT_A_RECONSTRUCTED_PERSON",
      "primitives":[]any{map[string]any{"mode":4,"indices":indicesA,
        "attributes":map[string]any{"POSITION":posA,"JOINTS_0":jointsA,"WEIGHTS_0":weightsA},
        "material":0}}}},
    "materials":[]any{map[string]any{"name":"camera_plane_proxy_only","doubleSided":true,
      "pbrMetallicRoughness":map[string]any{"baseColorFactor":[]float32{.12,.75,.94,1},"metallicFactor":0,"roughnessFactor":1}}},
    "skins":[]any{map[string]any{"joints":jointIDs,"inverseBindMatrices":ibmA,"name":"MediaPipe33_proxy"}},
    "animations":[]any{map[string]any{"name":"source_video_longest_contiguous_pose_only",
      "channels":channels,"samplers":samplers}},
    "accessors":b.accessors,"bufferViews":b.views,
    "buffers":[]any{map[string]any{"byteLength":len(b.data)}},
  }
  j,err:=json.Marshal(root);if err!=nil{return nil,nil,err}
  for len(j)%4!=0{j=append(j,' ')}
  for len(b.data)%4!=0{b.data=append(b.data,0)}
  total:=12+8+len(j)+8+len(b.data)
  buf:=make([]byte,total)
  binary.LittleEndian.PutUint32(buf[0:],0x46546c67)
  binary.LittleEndian.PutUint32(buf[4:],2)
  binary.LittleEndian.PutUint32(buf[8:],uint32(total))
  binary.LittleEndian.PutUint32(buf[12:],uint32(len(j)))
  binary.LittleEndian.PutUint32(buf[16:],0x4e4f534a)
  copy(buf[20:],j)
  off:=20+len(j)
  binary.LittleEndian.PutUint32(buf[off:],uint32(len(b.data)))
  binary.LittleEndian.PutUint32(buf[off+4:],0x004e4942)
  copy(buf[off+8:],b.data)
  coverage:=make([]map[string]any,0,len(frames))
  for _,f:=range frames{
    count:=len(f.Landmarks)
    coverage=append(coverage,map[string]any{
      "source_video_ms":f.SourceTimeMS,"landmarks":count,
      "included_in_glb":f.Index>=start&&f.Index<start+n})
  }
  manifest:=map[string]any{
    "status":"EDITABLE_CAMERA_PLANE_SKIN_AND_ANIMATION_NOT_RECOVERED_3D",
    "input_source":"NASA workout R2 captions and validated file/source checksum",
    "source_video_sha1":originalVideoSHA1,
    "glb_frame_start_source_ms":frames[start].SourceTimeMS,
    "glb_frame_end_source_ms":frames[start+n-1].SourceTimeMS,
    "glb_sample_count":n,"glb_frame_rate_hz":1,
    "all_30_frame_coverage":coverage,
    "full_source_detected_frames":countDetected(frames),
    "joints":33,"skin_vertices":len(positions)/3,
    "deformed_segments":len(indices)/24,"triangles":len(indices)/3,
    "coordinate_space":"camera_plane_proxy_XY_arbitrary_units_Z_zero",
    "bone_length_consistency":"NOT_ENFORCED",
    "joint_angle_limits":"NOT_ENFORCED",
    "missing_frames":"EXCLUDED_NO_INTERPOLATION",
    "true_3d_shape":"UNKNOWN",
    "identity_recovered":false,"body_measurements_recovered":false,
    "model_release_or_global_publicity_rights":"UNKNOWN",
  }
  return buf,manifest,nil
}
func countDetected(a []Frame)int{n:=0;for _,f:=range a{if len(f.Landmarks)==33{n++}};return n}
func execute(in,receipt,out string)error{
  raw,err:=os.ReadFile(in);if err!=nil{return err}
  proof,err:=os.ReadFile(receipt);if err!=nil{return err}
  if err:=verifyReceipt(proof);err!=nil{return err}
  var frames []Frame
  if err:=json.Unmarshal(raw,&frames);err!=nil{return err}
  glb,manifest,err:=createGLB(frames);if err!=nil{return err}
  digest:=sha256.Sum256(raw)
  manifest["input_landmarks_sha256"]=fmt.Sprintf("%x",digest)
  os.MkdirAll(out,0755)
  if err:=os.WriteFile(filepath.Join(out,"camera_plane_skinned_motion.glb"),glb,0644);err!=nil{return err}
  gsum:=sha256.Sum256(glb)
  manifest["glb_sha256"]=fmt.Sprintf("%x",gsum)
  outJ,err:=json.MarshalIndent(manifest,"","  ");if err!=nil{return err}
  if err:=os.WriteFile(filepath.Join(out,"rig_manifest.json"),append(outJ,'
'),0644);err!=nil{return err}
  fmt.Println(string(outJ))
  return nil
}
func main(){
  in:=flag.String("input","nasa-pair-output/video_landmarks.json","source-bound R2 observation JSON")
  receipt:=flag.String("receipt","nasa-pair-output/receipt.json","R2 source provenance receipt")
  out:=flag.String("out","pose-rig-output","derived candidate output dir")
  flag.Parse()
  if err:=execute(*in,*receipt,*out);err!=nil{
    fmt.Fprintln(os.Stderr,"R3 FAIL:",err);os.Exit(4)
  }
}
