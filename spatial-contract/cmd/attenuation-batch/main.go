// Original-public batched distance qualification fixture generator.
// Build once, generate 84 actual 48k stereo/5.1/7.1 float PCM WAVs plus a
// distinct sample-ramp waveform without importing any game/audio middleware.
package main

import (
    "crypto/sha256"
    "encoding/binary"
    "encoding/hex"
    "encoding/json"
    "fmt"
    "math"
    "os"
    "path/filepath"
    "strconv"
    "example.invalid/spatial-contract/attenuation"
)
const rate=48000
const frames=2048
var channels=[]int{2,6,8}
var distances=[]int{1,2,5,10,20,40,100}
var kinds=[]string{"impulse","tone"}
var curves=[]attenuation.Curve{attenuation.Identity,attenuation.InverseDistance}
type Receipt struct{
    Schema string `json:"schema"`
    Rights string `json:"rights"`
    Rate int `json:"rate"`
    Frames int `json:"frames"`
    Oracle string `json:"oracle"`
    Source map[string]string `json:"source_sha256"`
    Outputs []Entry `json:"outputs"`
}
type Entry struct{
    Filename string `json:"filename"`
    SourceKind string `json:"source_kind"`
    Channels int `json:"channels"`
    Distance int `json:"distance_m"`
    Mode string `json:"mode"`
    Gain float64 `json:"gain"`
    SHA string `json:"sha256"`
    Bytes int `json:"bytes"`
}
func writeWAV(path string,data []byte,nchannels,format,bits uint16)error{
    f,err:=os.OpenFile(path,os.O_CREATE|os.O_EXCL|os.O_WRONLY,0600)
    if err!=nil{return err}
    defer f.Close()
    size:=len(data)
    bps:=uint32(rate)*uint32(nchannels)*uint32(bits/8)
    h:=make([]byte,44)
    copy(h[0:4],"RIFF")
    binary.LittleEndian.PutUint32(h[4:],uint32(36+size))
    copy(h[8:16],"WAVEfmt ")
    binary.LittleEndian.PutUint32(h[16:],16)
    binary.LittleEndian.PutUint16(h[20:],format)
    binary.LittleEndian.PutUint16(h[22:],nchannels)
    binary.LittleEndian.PutUint32(h[24:],rate)
    binary.LittleEndian.PutUint32(h[28:],bps)
    binary.LittleEndian.PutUint16(h[32:],uint16(int(nchannels)*int(bits/8)))
    binary.LittleEndian.PutUint16(h[34:],bits)
    copy(h[36:40],"data")
    binary.LittleEndian.PutUint32(h[40:],uint32(size))
    if _,err=f.Write(h);err!=nil{return err}
    _,err=f.Write(data)
    return err
}
func sha(path string)(string,error){ b,err:=os.ReadFile(path);if err!=nil{return "",err};hash:=sha256.Sum256(b);return hex.EncodeToString(hash[:]),nil }
func original(kind string) []int16{
    p:=make([]int16,frames)
    for i:=range p{
        v:=0.0
        if kind=="impulse"{
            if i==0{v=.25}
            if i==1023{v=.15}
        }else{
            v=.125*math.Sin(2*math.Pi*410*float64(i)/rate)
        }
        p[i]=int16(math.Round(v*32767))
    }
    return p
}
func monoWAVData(p []int16)[]byte{ b:=make([]byte,len(p)*2);for i,v:=range p{binary.LittleEndian.PutUint16(b[i*2:],uint16(v))};return b}
func carrier(p []int16,n int)[]float32{
    v:=make([]float32,len(p)*n)
    for frame,x:=range p{for ch:=0;ch<n;ch++{
        if n>=6 && ch==3{continue}
        v[frame*n+ch]=float32(x)/32768*float32(.6/float64(ch+1))
    }}
    return v
}
func encodeF32(v []float32)[]byte{
    b:=make([]byte,len(v)*4)
    for i,x:=range v{binary.LittleEndian.PutUint32(b[i*4:],math.Float32bits(x))}
    return b
}
func main() {
    if len(os.Args)!=2{panic("usage: attenuation-batch OUTPUT_NEW_DIRECTORY")}
    root:=os.Args[1]
    if err:=os.Mkdir(root,0700);err!=nil{panic(err)}
    receipt:=Receipt{Schema:"spatial_audio/w4c_go_attenuation_batch/1",
       Rights:"ORIGINAL_SELF_AUTHORED_PUBLIC_SYNTHETIC",Rate:rate,Frames:frames,
       Oracle:"INDEPENDENT_FLOAT64_PRESSURE_AMPLITUDE_MIN_1_REFERENCE_10_CLAMP_ONE",
       Source:make(map[string]string),Outputs:[]Entry{}}
    originals:=make(map[string][]int16)
    for _,kind:=range kinds{
        x:=original(kind)
        originals[kind]=x
        path:=filepath.Join(root,"original_"+kind+".wav")
        if err:=writeWAV(path,monoWAVData(x),1,1,16);err!=nil{panic(err)}
        hash,err:=sha(path);if err!=nil{panic(err)}
        receipt.Source[kind]=hash
    }
    for _,mode:=range curves{
        envelope:=attenuation.Envelope{Curve:mode,ReferenceMeters:10,MinimumMeters:1}
        for _,distance:=range distances{
            gain,err:=envelope.Gain(float64(distance));if err!=nil{panic(err)}
            for _,n:=range channels{
                for _,kind:=range kinds{
                    input:=carrier(originals[kind],n)
                    output:=make([]float32,len(input))
                    if err:=attenuation.ApplyInterleaved(output,input,n,gain,gain);err!=nil{panic(err)}
                    filename:=string(mode)+"_d"+fmt.Sprintf("%03d",distance)+"_ch"+strconv.Itoa(n)+"_"+kind+".wav"
                    path:=filepath.Join(root,filename)
                    data:=encodeF32(output)
                    if err:=writeWAV(path,data,uint16(n),3,32);err!=nil{panic(err)}
                    hash,err:=sha(path);if err!=nil{panic(err)}
                    receipt.Outputs=append(receipt.Outputs,Entry{Filename:filename,SourceKind:kind,
                        Channels:n,Distance:distance,Mode:string(mode),Gain:gain,SHA:hash,Bytes:44+len(data)})
                }
            }
        }
    }
    // Sample-accurate bounded amplitude transition probe, distinct from
    // physically modeled propagation delay or sample-continuous emitter motion.
    ramp:=make([]float32,frames*8)
    if err:=attenuation.ApplyInterleaved(ramp,carrier(originals["tone"],8),8,1,.5);err!=nil{panic(err)}
    rampPath:=filepath.Join(root,"ramp_ch8_tone.wav")
    if err:=writeWAV(rampPath,encodeF32(ramp),8,3,32);err!=nil{panic(err)}
    rampSHA,err:=sha(rampPath);if err!=nil{panic(err)}
    receipt.Outputs=append(receipt.Outputs,Entry{Filename:"ramp_ch8_tone.wav",
        SourceKind:"tone",Channels:8,Distance:10,Mode:"sample_linear_ramp_1_to_0.5",
        Gain:-1,SHA:rampSHA,Bytes:44+len(ramp)*4})
    b,err:=json.MarshalIndent(receipt,"","  ");if err!=nil{panic(err)}
    if err:=os.WriteFile(filepath.Join(root,"manifest.json"),append(b,'\n'),0600);err!=nil{panic(err)}
    fmt.Printf("W4C_NATIVE_GO_BATCH_PASS cases=%d+1 original_sources=2 rate=%d frames=%d\n",len(receipt.Outputs)-1,rate,frames)
}
