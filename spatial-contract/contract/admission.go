package contract

import (
 "crypto/sha256"
 "encoding/binary"
 "encoding/hex"
 "errors"
 "fmt"
 "io"
 "math"
 "os"
 "path/filepath"
 "strings"
)

// AssetReceipt is a content-addressed observation of REAL bytes, not merely
// the declared hash of an authoring fixture. This does not spatialize audio.
type AssetReceipt struct {
 EmitterID string `json:"emitter_id"`
 Name string `json:"name"`
 SHA256 string `json:"sha256"`
 Bytes int64 `json:"bytes"`
 Frames int `json:"frames"`
 Codec string `json:"codec"`
}
func little16(b []byte) uint16 { return binary.LittleEndian.Uint16(b) }
func little32(b []byte) uint32 { return binary.LittleEndian.Uint32(b) }

// inspectPCM deliberately supports a narrow original 48k mono 16bit PCM WAV
// subset. Unknown source formats must pass through an explicit conversion workcell.
func inspectPCM(f *os.File, sceneFrames int) (int,int64,error) {
 st,e:=f.Stat();if e!=nil{return 0,0,e}
 size:=st.Size()
 if !st.Mode().IsRegular() || size<44 || size>64*1024*1024 {return 0,0,errors.New("unsupported source type or size")}
 head:=make([]byte,44)
 if _,e=io.ReadFull(f,head);e!=nil{return 0,0,e}
 if string(head[0:4])!="RIFF" || string(head[8:12])!="WAVE" || string(head[12:16])!="fmt " ||
 little32(head[16:20])!=16 || little16(head[20:22])!=1 ||
 little16(head[22:24])!=1 || little32(head[24:28])!=48000 ||
 little32(head[28:32])!=96000 || little16(head[32:34])!=2 ||
 little16(head[34:36])!=16 || string(head[36:40])!="data" {
  return 0,0,errors.New("only canonical 48k mono PCM16 WAV admitted")
 }
 payload:=int64(little32(head[40:44]))
 if payload<=0 || payload%2!=0 || payload!=size-44 || uint64(little32(head[4:8]))!=uint64(size-8) {
  return 0,0,errors.New("truncated or malformed RIFF frame data")
 }
 frames:=int(payload/2)
 if frames!=sceneFrames {return 0,0,fmt.Errorf("source timeline frames=%d; expected=%d",frames,sceneFrames)}
 return frames,size,nil
}
func isRealRoot(root string) (string,error) {
 if root=="" {return "",errors.New("empty audio root")}
 abs,e:=filepath.Abs(root);if e!=nil{return "",e}
 clean:=filepath.Clean(abs)
 for path:=clean;;path=filepath.Dir(path) {
  st,e:=os.Lstat(path);if e!=nil{return "",e}
  if st.Mode()&os.ModeSymlink!=0 {return "",errors.New("symlink in audio root ancestry")}
  if !st.IsDir() {return "",errors.New("audio root component is not directory")}
  if path==filepath.Dir(path) {break}
 }
 return clean,nil
}

// AdmitSources checks strict scene-classification and REAL mono WAV contents.
// Filename paths in Scene already must be local basename-only. The file identity
// is verified after reading to reject a common replacement/symlink race.
func AdmitSources(s Scene,root string,publicWorker bool)([]AssetReceipt,error){
 if _,e:=s.Admission(publicWorker);e!=nil{return nil,e}
 base,e:=isRealRoot(root);if e!=nil{return nil,e}
 frames:=s.DurationMS*48
 receipts:=make([]AssetReceipt,0,len(s.Emitters))
 for _,em:=range s.Emitters {
  if filepath.Base(em.AudioAsset)!=em.AudioAsset || strings.ContainsAny(em.AudioAsset,"/\\") {return nil,errors.New("unsafe source filename")}
  file:=filepath.Join(base,em.AudioAsset)
  before,e:=os.Lstat(file);if e!=nil{return nil,e}
  if !before.Mode().IsRegular() || before.Mode()&os.ModeSymlink!=0{return nil,errors.New("source not a regular file")}
  f,e:=os.Open(file);if e!=nil{return nil,e}
  opened,e:=f.Stat();if e!=nil{f.Close();return nil,e}
  if !os.SameFile(before,opened){f.Close();return nil,errors.New("source changed during open")}
  n,bytes,e:=inspectPCM(f,frames)
  if e!=nil{f.Close();return nil,fmt.Errorf("%s: %w",em.ID,e)}
  if _,e=f.Seek(0,io.SeekStart);e!=nil{f.Close();return nil,e}
  hash:=sha256.New()
  if _,e=io.Copy(hash,f);e!=nil{f.Close();return nil,e}
  after,e:=os.Lstat(file)
  closeErr:=f.Close()
  if e!=nil{return nil,e};if closeErr!=nil{return nil,closeErr}
  if !os.SameFile(before,after) || after.Size()!=bytes || after.ModTime()!=before.ModTime() {
    return nil,errors.New("source changed during hashing")
  }
  digest:=hex.EncodeToString(hash.Sum(nil))
  if digest!=em.AssetSHA256{return nil,fmt.Errorf("%s source SHA256 mismatch",em.ID)}
  receipts=append(receipts,AssetReceipt{EmitterID:em.ID,Name:em.AudioAsset,SHA256:digest,Bytes:bytes,Frames:n,Codec:"pcm_s16le"})
 }
 return receipts,nil
}

// WriteOriginalSine creates an intentionally synthetic, rights-clean, real
// test file, and returns its actual SHA256. Never overwrite a previous source.
func WriteOriginalSine(path string, durationMS int)(string,error){
 if durationMS<=0 || durationMS>600000 {return "",errors.New("invalid fixture duration")}
 n:=durationMS*48
 total:=44+2*n
 if total>64*1024*1024 {return "",errors.New("fixture exceeds source budget")}
 out:=make([]byte,total)
 copy(out[0:4],"RIFF")
 binary.LittleEndian.PutUint32(out[4:8],uint32(total-8))
 copy(out[8:12],"WAVE");copy(out[12:16],"fmt ")
 binary.LittleEndian.PutUint32(out[16:20],16)
 binary.LittleEndian.PutUint16(out[20:22],1)
 binary.LittleEndian.PutUint16(out[22:24],1)
 binary.LittleEndian.PutUint32(out[24:28],48000)
 binary.LittleEndian.PutUint32(out[28:32],96000)
 binary.LittleEndian.PutUint16(out[32:34],2)
 binary.LittleEndian.PutUint16(out[34:36],16)
 copy(out[36:40],"data")
 binary.LittleEndian.PutUint32(out[40:44],uint32(2*n))
 for i:=0;i<n;i++ {
  sample:=math.Sin(2*math.Pi*410*float64(i)/48000)
  binary.LittleEndian.PutUint16(out[44+2*i:46+2*i],uint16(int16(math.Round(0.12*sample*32767))))
 }
 f,e:=os.OpenFile(path,os.O_WRONLY|os.O_CREATE|os.O_EXCL,0600);if e!=nil{return "",e}
 wrote,e:=f.Write(out);ce:=f.Close()
 if e!=nil||ce!=nil||wrote!=len(out){os.Remove(path);return "",errors.New("incomplete fixture WAV write")}
 h:=sha256.Sum256(out)
 return hex.EncodeToString(h[:]),nil
}
