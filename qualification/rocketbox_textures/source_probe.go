// R009 source-pinned MIT Rocketbox COLOR texture TGA provenance audit.
// This qualifies source bytes and header, NOT UV/Blender mapping or human appearance.
package main

import (
 "crypto/sha1"
 "crypto/sha256"
 "encoding/binary"
 "encoding/hex"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "os"
 "path/filepath"
)

type entry struct { Actor, Filename, GitBlob string; Size int }
var sources=[]entry{
 {"F01","f001_body_color.tga","25852db0db1f44a0de0643ce1e09c88aef587e6f",12582956},
 {"F01","f001_head_color.tga","0cdc62ab47da3dca01aff0bb179159865a559c63",12582956},
 {"F02","f002_body_color.tga","5eb8ee83281a7526544a80ddf9804507670eb049",12582956},
 {"F02","f002_head_color.tga","8f59bb553f24d3581de68bcf4683695c014bcc0f",12582956},
}
type tga struct { Width,Height,PixelDepth,ImageType,Pixels int }
type sourceReceipt struct {
 Actor string `json:"actor"`
 Filename string `json:"filename"`
 Bytes int `json:"bytes"`
 GitBlob string `json:"git_blob_sha1"`
 SHA256 string `json:"sha256"`
 Width int `json:"width"`
 Height int `json:"height"`
 PixelDepth int `json:"pixel_depth"`
 ImageType int `json:"tga_image_type"`
}
type receipt struct {
 Schema string `json:"schema"`
 SourceRepo string `json:"source_repo"`
 SourceCommit string `json:"source_commit"`
 License string `json:"license"`
 SourceClass string `json:"source_class"`
 Observations []sourceReceipt `json:"observations"`
 BlenderUVMapping string `json:"blender_uv_mapping"`
 CharacterRealism string `json:"character_realism"`
 ProductAccepted bool `json:"product_accepted"`
}
func gitBlobSHA(data []byte) string{
 h:=sha1.New()
 fmt.Fprintf(h,"blob %d%c",len(data),byte(0))
 _,_=h.Write(data)
 return hex.EncodeToString(h.Sum(nil))
}
func parseTGA(data []byte)(tga,error){
 var t tga
 if len(data)<18{return t,errors.New("TRUNCATED_TGA_HEADER")}
 if data[1]!=0{return t,errors.New("PALETTED_TGA_UNSUPPORTED")}
 if data[0]!=0{return t,errors.New("UNEXPECTED_TGA_IMAGE_ID")}
 t.ImageType=int(data[2])
 if t.ImageType!=2{return t,errors.New("UNSUPPORTED_TGA_IMAGE_TYPE")}
 t.Width=int(binary.LittleEndian.Uint16(data[12:14]))
 t.Height=int(binary.LittleEndian.Uint16(data[14:16]))
 t.PixelDepth=int(data[16])
 if t.Width==0||t.Height==0||t.Width>8192||t.Height>8192{return t,errors.New("TGA_BAD_DIMENSIONS")}
 if t.PixelDepth!=24&&t.PixelDepth!=32{return t,errors.New("TGA_BAD_PIXEL_DEPTH")}
 t.Pixels=t.Width*t.Height
 wanted:=18+t.Pixels*(t.PixelDepth/8)
 if len(data)!=wanted&&len(data)!=wanted+26{return t,fmt.Errorf("TGA_BYTE_LENGTH_MISMATCH got%d expected%d_or_%d",len(data),wanted,wanted+26)}
 if len(data)==wanted+26 {
  // Conventional TGA 2.0 footer after original uncompressed pixel bytes.
  if string(data[len(data)-18:len(data)-1])!="TRUEVISION-XFILE." || data[len(data)-1]!=0{
   return t,errors.New("TGA_FOOTER_SIGNATURE_MISMATCH")
  }
 }
 return t,nil
}
func check(e entry,dir string)(sourceReceipt,error){
 r:=sourceReceipt{Actor:e.Actor,Filename:e.Filename,GitBlob:e.GitBlob}
 p:=filepath.Join(dir,e.Filename)
 st,err:=os.Lstat(p);if err!=nil{return r,err}
 if !st.Mode().IsRegular(){return r,errors.New("SYMLINK_OR_NONREGULAR_TEXTURE_SOURCE")}
 if st.Size()!=int64(e.Size){return r,fmt.Errorf("FROZEN_MIT_TEXTURE_SIZE_MISMATCH_%s",e.Filename)}
 raw,err:=os.ReadFile(p);if err!=nil{return r,err}
 if gitBlobSHA(raw)!=e.GitBlob{return r,fmt.Errorf("FROZEN_MIT_GIT_BLOB_MISMATCH_%s",e.Filename)}
 t,err:=parseTGA(raw);if err!=nil{return r,fmt.Errorf("%s: %w",e.Filename,err)}
 digest:=sha256.Sum256(raw)
 r.SHA256=hex.EncodeToString(digest[:])
 r.Bytes=len(raw);r.Width=t.Width;r.Height=t.Height;r.PixelDepth=t.PixelDepth;r.ImageType=t.ImageType
 return r,nil
}
func main(){
 dir:=flag.String("directory","","directory with exactly four pinned official MIT TGA objects")
 out:=flag.String("out","","JSON receipt path")
 flag.Parse()
 if *dir==""||*out==""{fmt.Fprintln(os.Stderr,"DIRECTORY_AND_OUT_REQUIRED");os.Exit(2)}
 r:=receipt{Schema:"scp.mit_rocketbox_original_color_texture_source.v1",
  SourceRepo:"microsoft/Microsoft-Rocketbox",
  SourceCommit:"0943055db6ec570bcef9f2c8b41c9e5467c808f9",
  License:"MIT_WITH_NOTICE",SourceClass:"OFFICIAL_PINNED_MIT_TEXTURES",
  BlenderUVMapping:"NOT_RUN",CharacterRealism:"UNKNOWN",ProductAccepted:false}
 for _,e:=range sources{
  obs,err:=check(e,*dir)
  if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(3)}
  r.Observations=append(r.Observations,obs)
 }
 raw,err:=json.MarshalIndent(r,"","  ")
 if err!=nil{panic(err)}
 raw=append(raw,byte(10))
 if err=os.WriteFile(*out,raw,0600);err!=nil{panic(err)}
 fmt.Printf("MIT_SOURCE_COLOR_TEXTURES_VERIFIED %d/4; UV_MAPPING_NOT_RUN PRODUCT_NOT_ACCEPTED%c",len(r.Observations),byte(10))
}
