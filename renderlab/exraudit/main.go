// exraudit checks OpenEXR header channels for the R037 synthetic renderer.
// It does NOT decompress pixel data or validate physical meaning of render passes.
package main

import (
 "crypto/sha256"
 "encoding/binary"
 "encoding/hex"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "os"
 "sort"
 "strings"
)

const maxBytes = 32 << 20

type Audit struct {
 Status string `json:"status"`
 Qualification string `json:"qualification"`
 BaselineSHA256 string `json:"baseline_sha256"`
 MaterialSHA256 string `json:"material_sha256"`
 Channels []string `json:"channels"`
 RequiredPasses []string `json:"required_passes"`
}

func cstr(b []byte, at *int) (string,error) {
 start:=*at
 for *at<len(b) && *at-start<=1024 {
  if b[*at]==0 { s:=string(b[start:*at]); *at++; return s,nil }
  *at++
 }
 return "", errors.New("missing or overlong EXR string terminator")
}

func parseChannels(b []byte) ([]string,error) {
 off:=0
 seen:=map[string]bool{}
 var names []string
 for {
  n,err:=cstr(b,&off);if err!=nil{return nil,err}
  if n=="" {if off!=len(b){return nil,errors.New("trailing EXR channel bytes")};break}
  if seen[n]{return nil,fmt.Errorf("duplicate EXR channel %q",n)}
  seen[n]=true
  if len(names)>=128 || off+16>len(b){return nil,errors.New("truncated or excessive EXR channels")}
  pt:=binary.LittleEndian.Uint32(b[off:]);off+=4
  linear:=b[off];off++
  reserved:=b[off:off+3];off+=3
  xs:=int32(binary.LittleEndian.Uint32(b[off:]));off+=4
  ys:=int32(binary.LittleEndian.Uint32(b[off:]));off+=4
  if pt>2 || linear>1 || reserved[0]!=0 || reserved[1]!=0 || reserved[2]!=0 || xs<1 || ys<1 {return nil,fmt.Errorf("invalid EXR channel declaration %q",n)}
  names=append(names,n)
 }
 if len(names)==0 {return nil,errors.New("no EXR channels")}
 sort.Strings(names)
 return names,nil
}

func inspect(data []byte) ([]string,error) {
 if len(data)<32 || binary.LittleEndian.Uint32(data[:4])!=20000630 {return nil,errors.New("invalid OpenEXR magic/size")}
 version:=binary.LittleEndian.Uint32(data[4:8])
 if version&0xff!=2 || version&0x1000!=0 {return nil,errors.New("unsupported OpenEXR version or multipart layout")}
 off:=8
 attrs:=map[string]bool{}
 var channels []string
 for n:=0;n<64;n++ {
  key,err:=cstr(data,&off);if err!=nil{return nil,err}
  if key=="" {break}
  if attrs[key]{return nil,fmt.Errorf("duplicate EXR attribute %q",key)}
  attrs[key]=true
  kind,err:=cstr(data,&off);if err!=nil{return nil,err}
  if off+4>len(data) {return nil,errors.New("truncated EXR attribute length")}
  size:=uint64(binary.LittleEndian.Uint32(data[off:]));off+=4
  if size>1<<20 || size>uint64(len(data)-off){return nil,errors.New("invalid EXR attribute size")}
  raw:=data[off:off+int(size)];off+=int(size)
  if key=="channels" {
   if kind!="chlist" {return nil,errors.New("EXR channels not chlist")}
   channels,err=parseChannels(raw);if err!=nil{return nil,err}
  }
  if key=="dataWindow" && (kind!="box2i" || size!=16) {return nil,errors.New("invalid EXR dataWindow")}
 }
 if !attrs["channels"] || !attrs["dataWindow"] || !attrs["compression"] {return nil,errors.New("missing mandatory EXR header metadata")}
 // Header can advertise channels without valid pixel chunks. This is strictly
 // a channel-declaration audit, never a decoded image or photorealism claim.
 return channels,nil
}

func passes(channels []string) ([]string,error) {
 got:=map[string]map[string]bool{}
 for _,name:=range channels {
  split:=strings.LastIndexByte(name,'.')
  if split<0 {continue}
  layer,component:=strings.ToLower(name[:split]),strings.ToUpper(name[split+1:])
  for _,spec:=range []struct{group,needle string}{{"beauty","combined"},{"depth","depth"},{"depth",".z"},{"normal","normal"},{"vector","vector"},{"object","indexob"}} {
   if strings.Contains(layer,spec.needle) {
    if got[spec.group]==nil {got[spec.group]=map[string]bool{}}
    got[spec.group][component]=true
   }
  }
 }
 for _,c:=range []string{"R","G","B"} {if !got["beauty"][c] {return nil,fmt.Errorf("missing beauty Combined.%s",c)}}
 if !got["depth"]["Z"] && !got["depth"]["X"] {return nil,errors.New("missing depth Z/X channel")}
 for _,c:=range []string{"X","Y","Z"} {if !got["normal"][c] {return nil,fmt.Errorf("missing Normal.%s",c)}}
 for _,c:=range []string{"X","Y"} {if !got["vector"][c] {return nil,fmt.Errorf("missing Vector.%s",c)}}
 if !got["object"]["X"] {return nil,errors.New("missing IndexOB.X channel")}
 return []string{"beauty-RGB","depth","normal-XYZ","motion-vector-XY","object-index"},nil
}

func read(path string) ([]string,string,error) {
 fi,err:=os.Lstat(path);if err!=nil{return nil,"",err}
 if !fi.Mode().IsRegular() || fi.Size()<32 || fi.Size()>maxBytes{return nil,"",errors.New("EXR must be bounded regular file")}
 data,err:=os.ReadFile(path);if err!=nil{return nil,"",err}
 d:=sha256.Sum256(data)
 ch,err:=inspect(data)
 return ch,hex.EncodeToString(d[:]),err
}

func audit(a,b string) (Audit,error) {
 ca,ha,err:=read(a);if err!=nil{return Audit{},fmt.Errorf("baseline: %w",err)}
 cb,hb,err:=read(b);if err!=nil{return Audit{},fmt.Errorf("material: %w",err)}
 if len(ca)!=len(cb){return Audit{},errors.New("EXR treatment channel lists differ")}
 for i:=range ca {if ca[i]!=cb[i]{return Audit{},errors.New("EXR treatment channel names differ")}}
 groups,err:=passes(ca);if err!=nil{return Audit{},err}
 return Audit{Status:"EXR_HEADER_CHANNELS_VERIFIED",Qualification:"NO_PIXEL_DECODE_OR_PHOTOREALISM_CLAIM",BaselineSHA256:ha,MaterialSHA256:hb,Channels:ca,RequiredPasses:groups},nil
}

func run(args []string) error {
 fs:=flag.NewFlagSet("exraudit",flag.ContinueOnError)
 a:=fs.String("baseline","","baseline EXR")
 b:=fs.String("material","","material treatment EXR")
 out:=fs.String("out","","audit JSON path")
 if err:=fs.Parse(args);err!=nil{return err}
 if fs.NArg()!=0 || *a==""||*b==""||*out=="" {return errors.New("usage: exraudit -baseline file -material file -out report.json")}
 report,err:=audit(*a,*b);if err!=nil{return err}
 body,err:=json.MarshalIndent(report,"","  ");if err!=nil{return err}
 body=append(body,'
')
 if err:=os.WriteFile(*out,body,0644);err!=nil{return err}
 fmt.Print(string(body));return nil
}

func main(){if err:=run(os.Args[1:]);err!=nil{fmt.Fprintln(os.Stderr,"HOLD:",err);os.Exit(1)}}
