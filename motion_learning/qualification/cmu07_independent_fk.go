// CMU07 source ASF/AMC independent full-skeleton forward kinematics in Go.
// No third-party FK library: this is an independent oracle against pinned
// MIT AMCParser Python, not a generated clip or rights/adoption grant.
// Original complete motion trajectories may exist only in disposable RUNNER_TEMP.
package main

import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "flag"
 "fmt"
 "math"
 "os"
 "path/filepath"
 "strconv"
 "strings"
)
const factor = 2.54 / 100.0 / 0.45
const asfSHA="c29414591d76a34885bff0b04a2666bf9659f869751a2549591c55277cf95b04"
var amcSHA=map[string]string{
 "07_01":"3ca8e8b834481c97c32e9dd555f8c9023e33b6c52d93c9d556c83570204bf3f2",
 "07_02":"a6062c6c6bce037241d345ca8d802ab36a5cf003b60f759aa7b1db545219c065",
}
type Vec [3]float64
type Mat [3][3]float64
type Bone struct{
 Name string
 Dir Vec
 Length float64
 Axis Vec
 DOF []string
 Parent string
 Children []string
}
type Frame struct{
 Index int
 Channels map[string][]float64
}
type Ephemeral struct{
 Schema string `json:"schema"`
 Motion string `json:"motion"`
 Units string `json:"units"`
 ClockHz int `json:"clock_hz"`
 SourceHashes map[string]string `json:"source_sha256"`
 BoneCount int `json:"bone_count"`
 Frames []map[string]Vec `json:"frames"`
}
func readVerified(path,want string)([]string,error){
 b,e:=os.ReadFile(path);if e!=nil{return nil,e}
 h:=sha256.Sum256(b)
 if hex.EncodeToString(h[:])!=want{return nil,fmt.Errorf("source digest mismatch %s",filepath.Base(path))}
 if len(b)>15000000||len(b)<100{return nil,errors.New("source size out of bounds")}
 return strings.Split(strings.ReplaceAll(string(b),string(rune(13))+string(rune(10)),string(rune(10))),string(rune(10))),nil
}
func floats(parts []string, n int)([]float64,error){
 if len(parts)!=n{return nil,fmt.Errorf("invalid vector of length %d expected %d",len(parts),n)}
 out:=make([]float64,n)
 for i,s:=range parts{v,e:=strconv.ParseFloat(s,64);if e!=nil||math.IsNaN(v)||math.IsInf(v,0){return nil,fmt.Errorf("nonfinite or invalid scalar %q",s)};out[i]=v}
 return out,nil
}
func v3(parts []string)(Vec,error){q,e:=floats(parts,3);if e!=nil{return Vec{},e};return Vec{q[0],q[1],q[2]},nil}
func parseASF(lines []string)(map[string]*Bone,error){
 bones:=map[string]*Bone{"root":{Name:"root"}}
 section:="";active:=false;inHier:=false;var current *Bone
 for _,raw:=range lines{
  line:=strings.TrimSpace(raw);if line==""||strings.HasPrefix(line,"#"){continue}
  if strings.HasPrefix(line,":"){section=strings.ToLower(strings.Fields(line)[0]);active=false;inHier=false;continue}
  p:=strings.Fields(line)
  if section==":bonedata"{
   if p[0]=="begin"{if active{return nil,errors.New("nested bone")};active=true;current=&Bone{};continue}
   if p[0]=="end"{if !active||current.Name==""{return nil,errors.New("invalid bone end")};if _,has:=bones[current.Name];has{return nil,errors.New("duplicate source bone")};bones[current.Name]=current;active=false;continue}
   if !active{continue}
   switch p[0] {
   case "name":if len(p)!=2{return nil,errors.New("bad bone name")};current.Name=p[1]
   case "direction":q,e:=v3(p[1:]);if e!=nil{return nil,e};current.Dir=q
   case "length":q,e:=floats(p[1:],1);if e!=nil{return nil,e};current.Length=q[0]
   case "axis":if len(p)!=5||p[4]!="XYZ"{return nil,errors.New("unknown bone axis order")};q,e:=v3(p[1:4]);if e!=nil{return nil,e};current.Axis=q
   case "dof":current.DOF=append([]string{},p[1:]...)
   }
  }
  if section==":hierarchy"{
   if p[0]=="begin"{inHier=true;continue}
   if p[0]=="end"{inHier=false;continue}
   if !inHier{continue}
   if len(p)<2{return nil,errors.New("hierarchy row too short")}
   parent,ok:=bones[p[0]];if !ok{return nil,fmt.Errorf("unknown parent %q",p[0])}
   for _,child:=range p[1:]{b,has:=bones[child];if !has||b.Parent!=""{return nil,fmt.Errorf("unknown or repeated child %q",child)}
    b.Parent=parent.Name;parent.Children=append(parent.Children,child)}
  }
 }
 if len(bones)!=31{return nil,fmt.Errorf("expected 31 source nodes, got %d",len(bones))}
 for k,b:=range bones{if k!="root" && b.Parent==""{return nil,fmt.Errorf("orphan %s",k)}
  if b.Length<0||math.IsNaN(b.Length){return nil,errors.New("invalid ASF length")}
  for _,d:=range b.DOF{if d!="rx"&&d!="ry"&&d!="rz"{return nil,fmt.Errorf("unsupported dof %q",d)}}
 }
 return bones,nil
}
func parseAMC(lines []string)([]Frame,error){
 out:=[]Frame{};var frame *Frame;last:=0;degrees:=false;ref:=""
 for _,raw:=range lines{
  line:=strings.TrimSpace(raw);if line==""||strings.HasPrefix(line,"#"){continue}
  if strings.HasPrefix(line,":"){if strings.ToUpper(line)==":DEGREES"{degrees=true};continue}
  if !degrees{return nil,errors.New("AMC before DEGREES")}
  p:=strings.Fields(line)
  if len(p)==1 {if n,e:=strconv.Atoi(p[0]);e==nil{
   if n!=last+1{return nil,errors.New("frame sequence discontinuity")}
   if frame!=nil{
    if len(frame.Channels)<10{return nil,errors.New("too few AMC channels")}
    out=append(out,*frame)
   }
   frame=&Frame{Index:n,Channels:map[string][]float64{}};last=n;continue
  }}
  if frame==nil||len(p)<2{return nil,errors.New("invalid AMC row")}
  if _,yes:=frame.Channels[p[0]];yes{return nil,errors.New("duplicate AMC joint")}
  values,e:=floats(p[1:],len(p)-1);if e!=nil{return nil,e}
  if len(values)>8{return nil,errors.New("implausibly many DOFs")}
  frame.Channels[p[0]]=values
  names:=make([]string,0,len(frame.Channels));for k:=range frame.Channels{names=append(names,k)}
  // Frame channel count and bone matching validated below and by parity.
  _=names
 }
 if frame!=nil{out=append(out,*frame)}
 if len(out)<20||len(out)>100000{return nil,errors.New("AMC frame count implausible")}
 for i,f:=range out{
  if len(f.Channels)!=len(out[0].Channels){return nil,fmt.Errorf("nonstationary AMC joint channel set frame %d",i)}
  q,ok:=f.Channels["root"];if !ok||len(q)!=6{return nil,errors.New("missing six source root channels")}
  if ref==""{ref=fmt.Sprint(len(f.Channels))}
 }
 return out,nil
}
func I()Mat{return Mat{{1,0,0},{0,1,0},{0,0,1}}}
func mul(a,b Mat)Mat{var c Mat;for i:=0;i<3;i++{for j:=0;j<3;j++{for k:=0;k<3;k++{c[i][j]+=a[i][k]*b[k][j]}}};return c}
func trans(a Mat)Mat{var b Mat;for i:=0;i<3;i++{for j:=0;j<3;j++{b[i][j]=a[j][i]}};return b}
func rot(v Vec)Mat{
 x,y,z:=v[0]*math.Pi/180.,v[1]*math.Pi/180.,v[2]*math.Pi/180.
 sx,cx:=math.Sin(x),math.Cos(x);sy,cy:=math.Sin(y),math.Cos(y);sz,cz:=math.Sin(z),math.Cos(z)
 // Static XYZ exactly Rz(z) * Ry(y) * Rx(x), independent Go derivation.
 return Mat{{cz*cy,cz*sy*sx-sz*cx,cz*sy*cx+sz*sx},
            {sz*cy,sz*sy*sx+cz*cx,sz*sy*cx-cz*sx},
            {-sy,cy*sx,cy*cx}}
}
func mv(m Mat,v Vec)Vec{return Vec{m[0][0]*v[0]+m[0][1]*v[1]+m[0][2]*v[2],
 m[1][0]*v[0]+m[1][1]*v[1]+m[1][2]*v[2],
 m[2][0]*v[0]+m[2][1]*v[1]+m[2][2]*v[2]}}
func add(a,b Vec)Vec{return Vec{a[0]+b[0],a[1]+b[1],a[2]+b[2]}}
func sub(a,b Vec)Vec{return Vec{a[0]-b[0],a[1]-b[1],a[2]-b[2]}}
func norm(a Vec)float64{return math.Sqrt(a[0]*a[0]+a[1]*a[1]+a[2]*a[2])}
func fk(bones map[string]*Bone,frame Frame)(map[string]Vec,error){
 pos:=map[string]Vec{}
 visited:=map[string]bool{}
 var walk func(string,Mat,Vec)error
 walk=func(name string,pm Mat,pp Vec)error{
  if visited[name]{return fmt.Errorf("cycle in source hierarchy at %q",name)}
  visited[name]=true
  b,ok:=bones[name];if !ok{return fmt.Errorf("unknown bone %q",name)}
  var m Mat;var p Vec
  if name=="root"{
   q,yes:=frame.Channels["root"];if !yes||len(q)!=6{return errors.New("invalid root AMC channels")}
   m=rot(Vec{q[3],q[4],q[5]});p=Vec{q[0]*factor,q[1]*factor,q[2]*factor}
  }else{
   values,has:=frame.Channels[name]
   if !has&&len(b.DOF)>0{return fmt.Errorf("missing articulated bone channel %s",name)}
   if has&&len(values)!=len(b.DOF){return fmt.Errorf("bone %s dof expected %d got %d",name,len(b.DOF),len(values))}
   angles:=Vec{}
   for i,axis:=range b.DOF{switch axis{case "rx":angles[0]=values[i];case "ry":angles[1]=values[i];case "rz":angles[2]=values[i]}}
   C:=rot(b.Axis)
   m=mul(mul(mul(pm,C),rot(angles)),trans(C))
   d:=mv(m,b.Dir)
   p=add(pp,Vec{d[0]*b.Length*factor,d[1]*b.Length*factor,d[2]*b.Length*factor})
   if !isFinite(p){return errors.New("nonfinite FK result")}
   if want:=b.Length*norm(b.Dir)*factor;math.Abs(norm(sub(p,pp))-want)>1e-8{return fmt.Errorf("broken bone length %s",name)}
  }
  pos[name]=p
  for _,child:=range b.Children{if e:=walk(child,m,p);e!=nil{return e}}
  return nil
 }
 if e:=walk("root",I(),Vec{});e!=nil{return nil,e}
 if len(pos)!=len(bones){return nil,fmt.Errorf("incomplete rooted graph %d/%d",len(pos),len(bones))}
 return pos,nil
}
func isFinite(x Vec)bool{for _,v:=range x{if math.IsNaN(v)||math.IsInf(v,0){return false}};return true}
func selftest()error{
 b:=map[string]*Bone{"root":{Name:"root",Children:[]string{"a"}},
 "a":{Name:"a",Parent:"root",Length:1,Dir:Vec{1,0,0},DOF:[]string{"rz"}}}
 for _,t:=range []struct{angle float64;expected Vec}{{0,Vec{factor,0,0}},{90,Vec{0,factor,0}},{180,Vec{-factor,0,0}}}{
  r,e:=fk(b,Frame{Index:1,Channels:map[string][]float64{"root":{0,0,0,0,0,0},"a":{t.angle}}})
  if e!=nil{return e}
  if norm(sub(r["a"],t.expected))>1e-12{return fmt.Errorf("nontrivial FK incorrect at %.2f deg: %v",t.angle,r["a"])}
 }
 if len(mul(rot(Vec{30,15,45}),trans(rot(Vec{30,15,45}))))!=3{return errors.New("shape")}
 for i:=0;i<3;i++{for j:=0;j<3;j++{q:=mul(rot(Vec{30,15,45}),trans(rot(Vec{30,15,45})))[i][j];expected:=0.;if i==j{expected=1};if math.Abs(q-expected)>1e-12{return errors.New("rotation not orthonormal")}}}
 return nil
}
func main(){
 if len(os.Args)==2&&os.Args[1]=="--selftest"{if e:=selftest();e!=nil{panic(e)};fmt.Println("CMU_GO_INDEPENDENT_FK_SELFTEST_PASS");return}
 motion:=flag.String("motion","","original CMU AMC basename");asf:=flag.String("asf","","source ASF path");amc:=flag.String("amc","","source AMC path");out:=flag.String("out","","ephemeral output JSON, never public artifact");flag.Parse()
 sha,ok:=amcSHA[*motion];if !ok||*asf==""||*amc==""||*out==""{panic("explicit exact S1 source arguments required")}
 al,e:=readVerified(*asf,asfSHA);if e!=nil{panic(e)}
 ml,e:=readVerified(*amc,sha);if e!=nil{panic(e)}
 bones,e:=parseASF(al);if e!=nil{panic(e)}
 frames,e:=parseAMC(ml);if e!=nil{panic(e)}
 expected:=map[string]int{"07_01":316,"07_02":329}[*motion];if len(frames)!=expected{panic("source frame count mismatch")}
 all:=make([]map[string]Vec,0,len(frames))
 for _,f:=range frames{p,e:=fk(bones,f);if e!=nil{panic(e)};all=append(all,p)}
 output:=Ephemeral{Schema:"motion.cmu07.goindependent_fk_ephemeral.v1",Motion:*motion,
 Units:"publisher CMU native units multiplied by (1/0.45)*0.0254, right handed original source axes",
 ClockHz:120,SourceHashes:map[string]string{"asf":asfSHA,"amc":sha},
 BoneCount:len(bones),Frames:all}
 b,e:=json.Marshal(output);if e!=nil{panic(e)}
 if e:=os.WriteFile(*out,append(b,byte(10)),0600);e!=nil{panic(e)}
 fmt.Println(fmt.Sprintf("CMU_GO_SOURCE_FK_ORACLE motion=%s frames=%d bones=%d SHA256=%x EPHEMERAL_ONLY",*motion,len(all),len(bones),sha256.Sum256(b)))
}
