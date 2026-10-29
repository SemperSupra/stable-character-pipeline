// Generate a rights-clean 144-case compositional scene/gain/PCM batch. The
// source remains the immutable signed PCM16 fixture; native output is explicit
// float32 interleaved canonical layout with no DSP from any game engine.
package main
import(
 "crypto/sha256"
 "encoding/binary"
 "encoding/hex"
 "encoding/json"
 "fmt"
 "math"
 "os"
 "path/filepath"
 "example.invalid/spatial-contract/attenuation"
 "example.invalid/spatial-contract/sceneadapter"
)
const frames=1024
var emitters=[]sceneadapter.Position{
 {East:2,North:0,Up:0},{East:0,North:4,Up:0},
 {East:0,North:0,Up:20},{East:10,North:10,Up:0},
}
var listeners=[]sceneadapter.Position{
 {East:0,North:0,Up:0},{East:1,North:0,Up:0},
 {East:-1,North:2,Up:0},
}
var layouts=[]sceneadapter.ChannelLayout{sceneadapter.Stereo,sceneadapter.Surround51,sceneadapter.Surround71}
var curves=[]attenuation.Curve{attenuation.Identity,attenuation.InverseDistance}
var kinds=[]string{"impulse","tone"}
type Record struct {
 File string `json:"file"`
 Decision sceneadapter.Decision `json:"decision"`
 Emitter sceneadapter.Position `json:"emitter"`
 Listener sceneadapter.Position `json:"listener"`
 OriginalKind string `json:"original_kind"`
 SHA256 string `json:"sha256"`
}
type Manifest struct {
 Schema string `json:"schema"`
 Rights string `json:"rights"`
 SourceSHA map[string]string `json:"source_sha256"`
 Cases []Record `json:"cases"`
}
func hash(b []byte)string{h:=sha256.Sum256(b);return hex.EncodeToString(h[:])}
func pcm(kind string)([]int16,[]byte){
 x:=make([]int16,frames)
 for i:=range x{
  if kind=="impulse"{if i==0{x[i]=12345};if i==255{x[i]=2468}
  }else{x[i]=int16(math.Round(.15*32767*math.Sin(2*math.Pi*410*float64(i)/48000)))}
 }
 b:=make([]byte,2*frames)
 for i,v:=range x{binary.LittleEndian.PutUint16(b[2*i:],uint16(v))}
 return x,b
}
func writeUnique(path string,data []byte)error{
 f,err:=os.OpenFile(path,os.O_WRONLY|os.O_CREATE|os.O_EXCL,0600);if err!=nil{return err}
 _,writeErr:=f.Write(data);closeErr:=f.Close()
 if writeErr!=nil{return writeErr};return closeErr
}
func wav(v []float32,channels int)[]byte{
 payload:=make([]byte,len(v)*4)
 for i,x:=range v{binary.LittleEndian.PutUint32(payload[4*i:],math.Float32bits(x))}
 h:=make([]byte,44+len(payload))
 copy(h[0:4],"RIFF")
 binary.LittleEndian.PutUint32(h[4:],uint32(36+len(payload)))
 copy(h[8:16],"WAVEfmt ")
 binary.LittleEndian.PutUint32(h[16:],16)
 binary.LittleEndian.PutUint16(h[20:],3)
 binary.LittleEndian.PutUint16(h[22:],uint16(channels))
 binary.LittleEndian.PutUint32(h[24:],48000)
 binary.LittleEndian.PutUint32(h[28:],uint32(48000*channels*4))
 binary.LittleEndian.PutUint16(h[32:],uint16(channels*4))
 binary.LittleEndian.PutUint16(h[34:],32)
 copy(h[36:40],"data")
 binary.LittleEndian.PutUint32(h[40:],uint32(len(payload)))
 copy(h[44:],payload)
 return h
}
func run(root string)error{
 if err:=os.Mkdir(root,0700);err!=nil{return err}
 m:=Manifest{Schema:"spatial_audio.scene_adapter_batch.v1",
  Rights:sceneadapter.OriginalRights,SourceSHA:map[string]string{},Cases:[]Record{}}
 for _,kind:=range kinds{
  orig,bytes:=pcm(kind)
  m.SourceSHA[kind]=hash(bytes)
  if err:=writeUnique(filepath.Join(root,"original_"+kind+".s16le"),bytes);err!=nil{return err}
  for ei,e:=range emitters{for li,l:=range listeners{for _,layout:=range layouts{
   for _,curve:=range curves{
    s:=sceneadapter.Scene{
     SourceID:fmt.Sprintf("emitter_%d_%s",ei,kind),
     ListenerID:fmt.Sprintf("listener_%d",li),
     Rights:sceneadapter.OriginalRights,
     OriginalSourceSHA256:hash(bytes),RateHz:48000,StartFrame:1024,
     FrameCount:frames,Emitter:e,Listener:l,Layout:layout,
     Envelope:attenuation.Envelope{Curve:curve,ReferenceMeters:10,MinimumMeters:1},
    }
    n:=layout.Channels()
    buffer:=make([]float32,frames*n)
    for fi,v:=range orig{for ch:=0;ch<n;ch++{
     if n>=6&&ch==3{continue}
     buffer[fi*n+ch]=float32(v)/32768*float32(.6/float64(ch+1))
    }}
    rendered,decision,err:=sceneadapter.Apply(s,buffer)
    if err!=nil{return err}
    filename:=fmt.Sprintf("scene_e%d_l%d_ch%d_%s_%s.wav",ei,li,n,curve,kind)
    out:=wav(rendered,n)
    if err:=writeUnique(filepath.Join(root,filename),out);err!=nil{return err}
    m.Cases=append(m.Cases,Record{File:filename,Decision:decision,
     Emitter:e,Listener:l,OriginalKind:kind,SHA256:hash(out)})
   }
  }}}
 }
 raw,err:=json.MarshalIndent(m,"","  ");if err!=nil{return err}
 if err=writeUnique(filepath.Join(root,"scene_batch.json"),append(raw,'\n'));err!=nil{return err}
 if len(m.Cases)!=144{return fmt.Errorf("wrong batch count %d",len(m.Cases))}
 fmt.Printf("W4D_GO_SCENE_BATCH_NATIVE_PASS cases=%d distinct_original_sources=%d\n",len(m.Cases),len(m.SourceSHA))
 return nil
}
func main(){if len(os.Args)!=2{panic("usage: scene-batch OUTPUT_NEW_DIR")}
 if err:=run(os.Args[1]);err!=nil{panic(err)}}
