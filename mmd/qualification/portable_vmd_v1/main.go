// Original-source-only MMD VMD v2 binary structural serializer and readback.
// No ASF/AMC/BVH parser, PMX model, real capture, native MMD playback or gait.
package main
import (
 "bytes"
 "crypto/sha256"
 "encoding/binary"
 "encoding/hex"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "io"
 "math"
 "os"
)
const magic="Vocaloid Motion Data 0002"
const model="SCP_SYNTHETIC"
const recordSize=111
type Frame struct {
 Name string
 Index uint32
 Position [3]float32
 Rotation [4]float32 // x,y,z,w
}
func fixed(s string,n int)([]byte,error){
 if len(s)<1||len(s)>=n{return nil,errors.New("name length incompatible with null-terminated VMD field")}
 for _,r:=range s{if r<33||r>126{return nil,errors.New("synthetic VMD supports ASCII bone names only; Shift-JIS unqualified")}}
 b:=make([]byte,n);copy(b,[]byte(s));return b,nil
}
func valid(f Frame) error {
 if _,e:=fixed(f.Name,15);e!=nil{return e}
 if f.Index>1800{return errors.New("frame budget exceeded")}
 n:=float64(0)
 for _,p:=range f.Position{if math.IsNaN(float64(p))||math.IsInf(float64(p),0)||math.Abs(float64(p))>100{return errors.New("invalid position")}}
 for _,q:=range f.Rotation{if math.IsNaN(float64(q))||math.IsInf(float64(q),0){return errors.New("nonfinite quaternion")};n+=float64(q)*float64(q)}
 if math.Abs(n-1)>1e-5{return errors.New("nonunit quaternion")}
 return nil
}
func Write(frames []Frame)([]byte,error){
 if len(frames)==0||len(frames)>10000{return nil,errors.New("invalid number of frames")}
 var b bytes.Buffer
 header:=make([]byte,30);copy(header,magic);b.Write(header)
 name,e:=fixed(model,20);if e!=nil{return nil,e};b.Write(name)
 if e=binary.Write(&b,binary.LittleEndian,uint32(len(frames)));e!=nil{return nil,e}
 seen:=map[string]uint32{}
 for _,f:=range frames{
  if e=valid(f);e!=nil{return nil,e}
  if old,ok:=seen[f.Name];ok&&old>=f.Index{return nil,errors.New("duplicate or backwards bone frame")}
  seen[f.Name]=f.Index
  label,_:=fixed(f.Name,15);b.Write(label)
  binary.Write(&b,binary.LittleEndian,f.Index)
  for _,x:=range f.Position{binary.Write(&b,binary.LittleEndian,x)}
  for _,q:=range f.Rotation{binary.Write(&b,binary.LittleEndian,q)}
  // Four 16-byte axis/rotation banks. MMD Tools v4.5.14 reads
  // bank[0:16:4] at offsets 0,16,32,48 for X/Y/Z/Rotation.
  // This is a bounded authored source encoding, NOT native engine acceptance.
  interp:=make([]byte,64)
  for ch:=0;ch<4;ch++{
   start:=ch*16
   interp[start+0]=20
   interp[start+4]=20
   interp[start+8]=107
   interp[start+12]=107
  }
  b.Write(interp)
 }
 // Newer files may include five zero-count trailing sections. No non-bone data.
 for i:=0;i<5;i++{binary.Write(&b,binary.LittleEndian,uint32(0))}
 return b.Bytes(),nil
}
func Parse(data []byte)([]Frame,error){
 if len(data)<74||len(data)>2<<20{return nil,errors.New("invalid bounded VMD size")}
 hdr:=make([]byte,30);copy(hdr,magic)
 if !bytes.Equal(data[:30],hdr){return nil,errors.New("wrong VMD v2 signature")}
 mn,_:=fixed(model,20)
 if !bytes.Equal(data[30:50],mn){return nil,errors.New("unexpected target model label")}
 n:=binary.LittleEndian.Uint32(data[50:54])
 if n==0||n>10000||int(n)>(len(data)-74)/recordSize||len(data)!=74+int(n)*recordSize{
  return nil,errors.New("truncated, surplus or unbounded VMD keyframe data")
 }
 out:=make([]Frame,n)
 seen:=map[string]uint32{}
 for i:=range out{
  at:=54+i*recordSize;block:=data[at:at+recordSize]
  j:=bytes.IndexByte(block[:15],0)
  if j<=0{return nil,errors.New("missing null termination")}
  for _,x:=range block[j+1:15]{if x!=0{return nil,errors.New("nonzero trailing bone-name bytes")}}
  f:=Frame{Name:string(block[:j]),Index:binary.LittleEndian.Uint32(block[15:19])}
  for k:=0;k<3;k++{f.Position[k]=math.Float32frombits(binary.LittleEndian.Uint32(block[19+k*4:23+k*4]))}
  for k:=0;k<4;k++{f.Rotation[k]=math.Float32frombits(binary.LittleEndian.Uint32(block[31+k*4:35+k*4]))}
  if e:=valid(f);e!=nil{return nil,e}
  if old,ok:=seen[f.Name];ok&&old>=f.Index{return nil,errors.New("duplicate or reversed bone timeline")}
  seen[f.Name]=f.Index
  // Reject unreviewed Bezier controls in every axis bank.
  for ch:=0;ch<4;ch++{
   start:=47+ch*16
   for j:=0;j<16;j++{
    want:=byte(0)
    switch j{case 0,4:want=20;case 8,12:want=107}
    if block[start+j]!=want{return nil,errors.New("unreviewed VMD channel interpolation byte")}
   }
  }
  out[i]=f
 }
 for at:=54+int(n)*recordSize;at<len(data);at+=4{
  if binary.LittleEndian.Uint32(data[at:at+4])!=0{return nil,errors.New("unqualified non-bone VMD section")}
 }
 return out,nil
}
func Fixture()[]Frame{
 frames:=make([]Frame,0,93)
 for _,name:=range []string{"Center","L_Ankle","R_Ankle"}{
  for t:=0;t<=30;t++{
   offset:=float32(0);if name=="L_Ankle"{offset=-0.35};if name=="R_Ankle"{offset=0.35}
   f:=Frame{Name:name,Index:uint32(t),Position:[3]float32{float32(t)/30,0,offset},Rotation:[4]float32{0,0,0,1}}
   frames=append(frames,f)
  }
 }
 return frames
}
func Main(args []string)error{
 fs:=flag.NewFlagSet("synthetic-vmd",flag.ContinueOnError)
 out:=fs.String("out","","new original synthetic VMD file")
 receipt:=fs.String("receipt","","new JSON evidence file")
 caps:=fs.Bool("capabilities",false,"read-only action discovery")
 if err:=fs.Parse(args);err!=nil{return err}
 if *caps{fmt.Println(`{"schema":"scp.mmd.original-synthetic-vmd.v1","actions":["capabilities","generate_nonoverwriting"],"actual_source":"NOT_ADMITTED","real_MMD_playback":"NOT_RUN","R009":"HELD"}`);return nil}
 if *out==""||*receipt==""||*out==*receipt||fs.NArg()!=0{return errors.New("distinct -out and -receipt required")}
 if _,e:=os.Stat(*out);e==nil{return errors.New("refuse existing VMD")};if _,e:=os.Stat(*receipt);e==nil{return errors.New("refuse existing receipt")}
 data,e:=Write(Fixture());if e!=nil{return e}
 round,e:=Parse(data);if e!=nil{return e}
 if len(round)!=93{return errors.New("self structural roundtrip mismatch")}
 h:=sha256.Sum256(data)
 report:=map[string]any{"schema":"scp.mmd.original-synthetic-vmd.v1","status":"PASS_SOURCE_ONLY_VMD_BINARY_STRUCTURAL_ROUNDTRIP","source":"ORIGINAL_SYNTHETIC","bone_names":[]string{"Center","L_Ankle","R_Ankle"},"keyframes":len(round),"fps":30,"vmd_sha256":hex.EncodeToString(h[:]),"real_mocap":"NOT_ADMITTED","PMX_bone_binding":"NOT_RUN","native_MMD_playback":"NOT_RUN","interpolation_playback":"UNKNOWN","human_anatomy":"UNKNOWN","R009":"HELD_NOT_ACCEPTED"}
 js,e:=json.MarshalIndent(report,"","  ");if e!=nil{return e}
 f,e:=os.OpenFile(*out,os.O_WRONLY|os.O_CREATE|os.O_EXCL,0600);if e!=nil{return e}
 if _,e=io.Copy(f,bytes.NewReader(data));e!=nil{f.Close();os.Remove(*out);return e};if e=f.Close();e!=nil{os.Remove(*out);return e}
 rf,e:=os.OpenFile(*receipt,os.O_WRONLY|os.O_CREATE|os.O_EXCL,0600);if e!=nil{os.Remove(*out);return e}
 if _,e=rf.Write(append(js,byte(10)));e!=nil{rf.Close();os.Remove(*receipt);os.Remove(*out);return e};if e=rf.Close();e!=nil{os.Remove(*receipt);os.Remove(*out);return e}
 return nil
}
func main(){if e:=Main(os.Args[1:]);e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(1)}}
