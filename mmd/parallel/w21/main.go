// W21 cross-run independently verify original iPhone MP4 custody, faststart
// container and H.264 structural evidence. No ffmpeg/apt needed on runner.
package main
import (
  "bytes"
  "crypto/sha256"
  "encoding/binary"
  "encoding/hex"
  "encoding/json"
  "fmt"
  "os"
  "path/filepath"
)
type Media struct{
 Name string `json:"name"`
 Hash string `json:"source_sha256"`
 Codec string `json:"codec"`
 Pixel string `json:"pixel_format"`
 Width int `json:"width"`
 Height int `json:"height"`
 Frames int `json:"decoded_frames"`
 Duration float64 `json:"duration_s"`
}
type Receipt struct{
 Status string `json:"status"`
 Media []Media `json:"media"`
}
func sha(b []byte)string{sum:=sha256.Sum256(b);return hex.EncodeToString(sum[:])}
func inspectMP4(b []byte)error{
 if len(b)<32||len(b)>15*1024*1024{return fmt.Errorf("unexpected MP4 size")}
 var ftyp,moov,mdat int64=-1,-1,-1
 var moovBody []byte
 for p:=0;p<len(b);{
   if p+8>len(b){return fmt.Errorf("box header truncated")}
   size:=int(binary.BigEndian.Uint32(b[p:p+4]))
   kind:=string(b[p+4:p+8])
   head:=8
   if size==1{
     if p+16>len(b){return fmt.Errorf("invalid extended header")}
     ext:=binary.BigEndian.Uint64(b[p+8:p+16])
     if ext>uint64(len(b)){return fmt.Errorf("oversized extended box")}
     size=int(ext);head=16
   } else if size==0{size=len(b)-p}
   if size<head||p+size>len(b){return fmt.Errorf("truncated MP4 box %s",kind)}
   switch kind{
   case "ftyp": ftyp=int64(p)
   case "moov": moov=int64(p);moovBody=b[p+head:p+size]
   case "mdat": mdat=int64(p)
   }
   p+=size
 }
 if ftyp!=0||moov<0||mdat<0||moov>mdat{return fmt.Errorf("not faststart MP4 ftyp/moov/mdat")}
 if !bytes.Contains(moovBody,[]byte("avc1"))||!bytes.Contains(moovBody,[]byte("avcC")){
   return fmt.Errorf("no real avc1 and avcC video sample entry in moov")
 }
 return nil
}
func main(){
 if len(os.Args)!=4{panic("usage ARTIFACT_DIR LANE_ID REPORT.json")}
 dir,id,out:=os.Args[1],os.Args[2],os.Args[3]
 if id!="W21-A"&&id!="W21-B"{panic("unexpected lane ID")}
 rb,err:=os.ReadFile(filepath.Join(dir,"mobile_capture_receipt.json"));if err!=nil{panic(err)}
 var receipt Receipt;if err=json.Unmarshal(rb,&receipt);err!=nil{panic(err)}
 if receipt.Status!="PASS_PHONE_COMPATIBLE_H264_FROM_GENUINE_SOURCE_RENDER_BYTES"||len(receipt.Media)!=2{panic("source receipt status invalid")}
 expected:=map[string]string{
  "original_31frames_looped_iphone.mp4":"3d1da9b33af0c8794a264ad6f8dff9fff32709204041b419c81206257e2d1242",
  "g7_g9_real_keyframe_slideshow_iphone.mp4":"b244d2d0551e72e982b8f58215096d57474c6fc545ff30bb5f3649b9f18b53d5",
 }
 verification:=map[string]string{}
 for _,m:=range receipt.Media{
   if expected[m.Name]==""||m.Hash!=expected[m.Name]{panic("source media hash mismatch")}
   data,err:=os.ReadFile(filepath.Join(dir,m.Name));if err!=nil{panic(err)}
   if sha(data)!=m.Hash{panic("actual MP4 bytes differ from source custody receipt")}
   if err:=inspectMP4(data);err!=nil{panic(m.Name+": "+err.Error())}
   if m.Codec!="h264"||m.Pixel!="yuv420p"||m.Width%2!=0||m.Height%2!=0||m.Frames<90{
     panic("iPhone codec/frame evidence is inconsistent")
   }
   verification[m.Name]=sha(data)
 }
 for i:=0;i<3;i++{
   file:=filepath.Join(dir,fmt.Sprintf("phoneframe_%03d.png",i))
   data,err:=os.ReadFile(file);if err!=nil{panic(err)}
   if len(data)<100||!bytes.Equal(data[:8],[]byte{137,80,78,71,13,10,26,10}){panic("bad source PNG "+file)}
 }
 res:=map[string]any{
   "schema":"scp.mmd.parallel.w21-independent-mobile-audit.v1",
   "status":"PASS_INDEPENDENT_IPHONE_MEDIA_BYTES_FASTSTART_AND_PNG",
   "lane_id":id,"receipt_sha256":sha(rb),
   "exact_source_mp4_sha256":verification,
   "confidence_scope":"two independent public hosted machines verify SAME original bytes; no new render generated",
   "limits":[]string{"ffprobe generation already performed in source W21 media workcell",
     "no third-party source model or private character media",
     "full iOS device hardware playback not measured here"},
 }
 b,_:=json.MarshalIndent(res,"","  ")
 if err=os.MkdirAll(filepath.Dir(out),0755);err!=nil{panic(err)}
 if err=os.WriteFile(out,append(b,'\n'),0644);err!=nil{panic(err)}
 fmt.Println("W21_PARALLEL_MOBILE_AUDIT",string(b))
}
