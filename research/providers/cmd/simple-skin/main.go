package main

import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "io"
 "net/http"
 "net/url"
 "os"
 "path/filepath"
 "strings"
 "time"
)
const upstream="8f492390ddc7a2ae221a1369ef560589cf8c70fb"
const base="https://raw.githubusercontent.com/KhronosGroup/glTF-Sample-Assets/"+upstream+"/Models/SimpleSkin/"
const ua="StableCharacterPipeline-Research/0.1 (+https://github.com/SemperSupra/stable-character-pipeline/issues/19)"
type Receipt struct{Schema string `json:"schema"`;File string `json:"file"`;Source string `json:"source"`;Bytes int `json:"bytes"`;SHA256 string `json:"sha256"`;License string `json:"license"`}
func fetch(cl *http.Client,urlstr string,max int64)([]byte,error){
 u,err:=url.Parse(urlstr)
 if err!=nil||u.Scheme!="https"||u.Hostname()!="raw.githubusercontent.com"||u.User!=nil{return nil,errors.New("unapproved URL")}
 req,err:=http.NewRequest(http.MethodGet,urlstr,nil);if err!=nil{return nil,err}
 req.Header.Set("User-Agent",ua)
 resp,err:=cl.Do(req);if err!=nil{return nil,err};defer resp.Body.Close()
 if resp.StatusCode!=200{return nil,fmt.Errorf("source HOLD status %d",resp.StatusCode)}
 raw,err:=io.ReadAll(io.LimitReader(resp.Body,max+1));if err!=nil{return nil,err}
 if int64(len(raw))>max{return nil,errors.New("unbounded source response")}
 return raw,nil
}
func main(){
 out:=flag.String("out","reports/simple-skin","isolated CC0 file directory")
 flag.Parse()
 if err:=os.MkdirAll(*out,0700);err!=nil{panic(err)}
 cl:=&http.Client{Timeout:15*time.Second,CheckRedirect:func(_ *http.Request,_ []*http.Request)error{return http.ErrUseLastResponse}}
 files:=[]struct{name,url string;expected int}{
  {"README.md",base+"README.md",0},
  {"SimpleSkin.gltf",base+"glTF/SimpleSkin.gltf",0},
  {"SimpleSkin_geometry.bin",base+"glTF/SimpleSkin_geometry.bin",168},
  {"SimpleSkin_skinningData.bin",base+"glTF/SimpleSkin_skinningData.bin",320},
  {"SimpleSkin_inverseBindMatrices.bin",base+"glTF/SimpleSkin_inverseBindMatrices.bin",128},
  {"SimpleSkin_animation.bin",base+"glTF/SimpleSkin_animation.bin",240},
 }
 receipts:=[]Receipt{}
 content:=map[string][]byte{}
 for i,f:=range files {
  if i>0{time.Sleep(2100*time.Millisecond)}
  cap:=int64(8192);if f.expected>0 {cap=int64(f.expected)}
  raw,err:=fetch(cl,f.url,cap);if err!=nil{fmt.Fprintln(os.Stderr,f.name,err);os.Exit(1)}
  if f.expected>0&&len(raw)!=f.expected{fmt.Fprintln(os.Stderr,"buffer length mismatch",f.name);os.Exit(1)}
  content[f.name]=raw
  if err:=os.WriteFile(filepath.Join(*out,f.name),raw,0600);err!=nil{panic(err)}
  h:=sha256.Sum256(raw)
  receipts=append(receipts,Receipt{Schema:"scp.simple_skin_provenance.v1",File:f.name,Source:f.url,Bytes:len(raw),SHA256:hex.EncodeToString(h[:]),License:"CC0-1.0 per this model's upstream README"})
 }
 if !strings.Contains(string(content["README.md"]),"Creative Commons Zero v1.0 Universal"){panic("model-specific CC0 evidence absent")}
 var model struct{Asset struct{Version string `json:"version"`} `json:"asset"`;Skins []struct{Joints []int `json:"joints"`} `json:"skins"`;Animations []json.RawMessage `json:"animations"`;Buffers []struct{URI string `json:"uri"`;Length int `json:"byteLength"`} `json:"buffers"`}
 if err:=json.Unmarshal(content["SimpleSkin.gltf"],&model);err!=nil{panic(err)}
 if model.Asset.Version!="2.0"||len(model.Skins)!=1||len(model.Skins[0].Joints)!=2||len(model.Animations)!=1||len(model.Buffers)!=4{panic("missing intended two-joint skinned animation")}
 for _,b:=range model.Buffers{v,ok:=content[b.URI];if !ok||len(v)!=b.Length{panic("buffer manifest or path mismatch")}}
 outJSON,_:=json.MarshalIndent(receipts,"","  ")
 if err:=os.WriteFile(filepath.Join(*out,"source-receipt.json"),append(outJSON,'\n'),0600);err!=nil{panic(err)}
 fmt.Println(string(outJSON))
}
