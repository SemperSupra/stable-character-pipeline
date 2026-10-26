// Mechanical Systems: deterministic animated glTF 2.0/GLB in pure Go.
// X forward, Y lateral, Z up; a scene-root transform converts to glTF Y up.
// Independent synthetic test models; no human identities, licensed CAD, or network dependencies.
package main

import (
 "bytes"
 "encoding/binary"
 "encoding/json"
 "flag"
 "fmt"
 "math"
 "os"
 "path/filepath"
)

type V [3]float64
type Part struct { Name, Shape string; Parent int; Pos, Size V; Mat int }
type Track struct { Node int; Times, Values []float32 }
type Joint struct { Name, Kind string; Axis V; Min, Max float64; Node int }
type Rig struct { Name string; Root int; Joints []Joint }
type Builder struct { Parts []Part; Tracks []Track; Rigs []Rig; Mats []map[string]any }

func (s *Builder) material(name string, c V) int {
 i:=len(s.Mats);s.Mats=append(s.Mats,map[string]any{"name":name,"doubleSided":true,
 "pbrMetallicRoughness":map[string]any{"baseColorFactor":[]float64{c[0],c[1],c[2],1},"metallicFactor":0.14,"roughnessFactor":0.68}});return i
}
func (s *Builder) part(name,shape string,p int,at,size V,mat int) int {
 id:=len(s.Parts);s.Parts=append(s.Parts,Part{name,shape,p,at,size,mat});return id
}
func (s *Builder) rig(name string,at V)(int,int) {
 root:=s.part(name+"/root","pivot",-1,at,V{},0);s.Rigs=append(s.Rigs,Rig{Name:name,Root:root});return root,len(s.Rigs)-1
}
func (s *Builder) joint(r int,name,kind string,p int,at,axis V,min,max float64) int {
 if min>max {panic("inverted joint range")}
 node:=s.part(name,"pivot",p,at,V{},0)
 s.Rigs[r].Joints=append(s.Rigs[r].Joints,Joint{name,kind,axis,min,max,node});return node
}
func quat(axis V,deg float64) []float32 {
 n:=math.Sqrt(axis[0]*axis[0]+axis[1]*axis[1]+axis[2]*axis[2]);if n==0 {panic("zero axis")}
 a:=deg*math.Pi/360;v:=float32(math.Sin(a)/n)
 return []float32{v*float32(axis[0]),v*float32(axis[1]),v*float32(axis[2]),float32(math.Cos(a))}
}
func (s *Builder) animate(node int,axis V,angles ...float64) {
 if len(angles)<2 {panic("animation keys required")}
 t:=Track{Node:node}
 for i,deg:=range angles {t.Times=append(t.Times,float32(8*float64(i)/float64(len(angles)-1)));t.Values=append(t.Values,quat(axis,deg)...)}
 s.Tracks=append(s.Tracks,t)
}
func (s *Builder) spin(node int,axis V,turns float64) {
 a:=make([]float64,65);for i:=range a {a[i]=turns*360*float64(i)/64};s.animate(node,axis,a...)
}
func makeScene()*Builder {
 s:=&Builder{}
 blue:=s.material("blue-car",V{.06,.30,.69});white:=s.material("ivory-aircraft",V{.86,.87,.84})
 glass:=s.material("glass",V{.13,.22,.31});metal:=s.material("metal",V{.55,.60,.66})
 black:=s.material("rubber-engine",V{.052,.058,.068});orange:=s.material("orange-articulation",V{.89,.29,.06})
 solar:=s.material("solar-blue",V{.04,.12,.38})
 // Ground SUV: separate wheel spin/steering, four hinged doors and lift gate.
 car,rc:=s.rig("ground/suv",V{0,-10,0})
 s.part("car/chassis","box",car,V{0,0,.98},V{4.6,1.9,.47},blue)
 s.part("car/roof","box",car,V{-.29,0,1.57},V{2.52,1.67,.67},blue)
 s.part("car/windscreen","box",car,V{.99,0,1.57},V{.08,1.6,.49},glass)
 s.part("car/grille","box",car,V{2.33,0,.93},V{.06,1.54,.32},metal)
 for _,side:=range []int{-1,1} {
  sy:=float64(side);sn:="left";if side>0{sn="right"}
  for _,door:=range []struct{label string; x,width float64}{{"front",1.05,1.13},{"rear",-.22,1.07}} {
   j:=s.joint(rc,"car/"+sn+"/"+door.label+"-hinge","revolute",car,V{door.x,sy*.95,1.02},V{0,0,1},-70,70)
   s.part("car/"+sn+"/"+door.label+"-door","box",j,V{-door.width/2,0,.28},V{door.width,.085,.61},blue)
   s.part("car/"+sn+"/"+door.label+"-window","box",j,V{-door.width/2,0,.69},V{door.width*.87,.07,.25},glass)
   swing:=-62.;if side<0{swing=62}
   s.animate(j,V{0,0,1},0,swing,swing,0,0)
  }
  for _,wheel:=range []struct{name string;x float64;steers bool}{{"front",1.38,true},{"rear",-1.48,false}} {
   p:=car;at:=V{wheel.x,sy*1.04,.48}
   if wheel.steers {
    p=s.joint(rc,"car/"+sn+"/steering","revolute",car,at,V{0,0,1},-35,35)
    s.animate(p,V{0,0,1},0,20,-20,0,0);at=V{}
   }
   ax:=s.joint(rc,"car/"+sn+"/"+wheel.name+"-axle","continuous",p,at,V{0,1,0},-1e6,1e6)
   s.part("car/"+sn+"/"+wheel.name+"-tire","cylinder-y",ax,V{},V{.92,.26,.92},black)
   s.part("car/"+sn+"/"+wheel.name+"-hub","cylinder-y",ax,V{0,sy*.15,0},V{.40,.02,.40},metal)
   s.spin(ax,V{0,1,0},1.25)
  }
 }
 tail:=s.joint(rc,"car/tailgate-hinge","revolute",car,V{-2.26,0,1.49},V{0,1,0},0,75)
 s.part("car/tailgate","box",tail,V{0,0,-.35},V{.09,1.83,.70},blue)
 s.animate(tail,V{0,1,0},0,60,60,0,0)
 // Aircraft: twin propellers, independent flaps/ailerons, folding gear, elevator and rudder.
 air,ra:=s.rig("air/utility-twin",V{0,0,1.65})
 s.part("air/fuselage","ellipsoid",air,V{0,0,.39},V{6.3,1.05,1.15},white)
 s.part("air/cockpit","ellipsoid",air,V{1.35,0,.83},V{1.6,.85,.60},glass)
 s.part("air/main-wing","box",air,V{.12,0,.43},V{1.52,9,.18},white)
 s.part("air/tailplane","box",air,V{-2.60,0,.7},V{.84,3.3,.12},white)
 s.part("air/vertical-tail","box",air,V{-2.66,0,1.29},V{.77,.13,1.18},orange)
 for _,side:=range []int{-1,1} {
  sy:=float64(side);sn:="port";if side>0{sn="starboard"}
  flap:=s.joint(ra,"air/"+sn+"/flap","revolute",air,V{-.69,sy*2.10,.4},V{0,1,0},-5,45)
  s.part("air/"+sn+"/flap-surface","box",flap,V{-.25,0,0},V{.49,2.57,.12},orange)
  s.animate(flap,V{0,1,0},0,30,30,0,0)
  ail:=s.joint(ra,"air/"+sn+"/aileron","revolute",air,V{-.68,sy*3.69,.4},V{0,1,0},-25,25)
  s.part("air/"+sn+"/aileron-surface","box",ail,V{-.2,0,0},V{.43,1.11,.10},metal)
  def:=21.;if side<0{def=-21};s.animate(ail,V{0,1,0},0,def,-def,0,0)
  s.part("air/"+sn+"/nacelle","ellipsoid",air,V{.56,sy*2.26,.16},V{1.3,.53,.59},metal)
  prop:=s.joint(ra,"air/"+sn+"/propeller","continuous",air,V{1.27,sy*2.26,.16},V{1,0,0},-1e6,1e6)
  s.part("air/"+sn+"/propeller-blades","box",prop,V{},V{.08,.19,2.12},black)
  s.part("air/"+sn+"/propeller-hub","ellipsoid",prop,V{},V{.26,.24,.24},orange)
  s.spin(prop,V{1,0,0},2.5)
  gear:=s.joint(ra,"air/"+sn+"/landing-gear","revolute",air,V{.22,sy*2.08,-.08},V{1,0,0},-85,85)
  s.part("air/"+sn+"/gear-strut","box",gear,V{0,0,-.72},V{.12,.12,1.43},metal)
  s.part("air/"+sn+"/gear-wheel","cylinder-y",gear,V{0,0,-1.40},V{.68,.19,.68},black)
  fold:=69.;if side<0{fold=-69};s.animate(gear,V{1,0,0},0,fold,fold,0,0)
 }
 elev:=s.joint(ra,"air/elevator","revolute",air,V{-3.03,0,.68},V{0,1,0},-25,25)
 s.part("air/elevator-surface","box",elev,V{-.18,0,0},V{.39,3.05,.10},metal)
 s.animate(elev,V{0,1,0},0,20,-20,0,0)
 rud:=s.joint(ra,"air/rudder","revolute",air,V{-3.09,0,1.27},V{0,0,1},-30,30)
 s.part("air/rudder-surface","box",rud,V{-.18,0,.22},V{.38,.11,.91},metal)
 s.animate(rud,V{0,0,1},0,24,-24,0,0)
 // Orbital tug: folding panel yokes, animated docking hatch, RCS gimbals and antenna.
 space,rs:=s.rig("space/orbital-tug",V{0,10,1.8})
 s.part("space/pressure-hull","cylinder-x",space,V{},V{2.4,2.1,2.1},metal)
 s.part("space/nose","ellipsoid",space,V{1.25,0,0},V{1.8,1.56,1.56},white)
 s.part("space/engine-bell","cylinder-x",space,V{-1.45,0,0},V{1.16,1.3,1.3},black)
 for _,side:=range []int{-1,1} {
  sy:=float64(side);sn:="port";if side>0{sn="starboard"}
  p:=s.joint(rs,"space/"+sn+"/solar-yoke","revolute",space,V{0,sy*1.11,.15},V{1,0,0},-100,100)
  s.part("space/"+sn+"/solar-panel","box",p,V{0,sy*1.43,0},V{1.65,2.65,.055},solar)
  s.part("space/"+sn+"/panel-spine","box",p,V{0,sy*1.43,.06},V{.05,2.65,.07},metal)
  fold:=85.;if side<0{fold=-85}
  s.animate(p,V{1,0,0},fold,0,0,fold,fold)
  g:=s.joint(rs,"space/"+sn+"/RCS-gimbal","revolute",space,V{-1.14,sy*.74,0},V{0,0,1},-15,15)
  s.part("space/"+sn+"/RCS-thruster","cylinder-x",g,V{-.2,0,0},V{.4,.34,.34},orange)
  s.animate(g,V{0,0,1},0,12,-12,0,0)
 }
 hatch:=s.joint(rs,"space/docking-hatch","revolute",space,V{1.78,.55,0},V{0,0,1},0,115)
 s.part("space/hatch-panel","box",hatch,V{.04,-.55,0},V{.09,1.13,1.10},orange)
 s.animate(hatch,V{0,0,1},0,96,96,0,0)
 ant:=s.joint(rs,"space/antenna-pan","revolute",space,V{-.45,0,.85},V{0,0,1},-170,170)
 s.part("space/antenna-dish","ellipsoid",ant,V{0,0,.45},V{.18,.7,.7},white)
 s.animate(ant,V{0,0,1},0,120,-120,0,0)
 return s
}
type Geometry struct { Pos []float32; Idx []uint32 }
func makeGeometry(shape string,d V) Geometry {
 g:=Geometry{};add:=func(x,y,z float64){g.Pos=append(g.Pos,float32(x),float32(y),float32(z))}
 tri:=func(a,b,c uint32){g.Idx=append(g.Idx,a,b,c)}
 if shape=="box" {
  x,y,z:=d[0]/2,d[1]/2,d[2]/2
  for _,v:=range []V{{-x,-y,-z},{x,-y,-z},{x,y,-z},{-x,y,-z},{-x,-y,z},{x,-y,z},{x,y,z},{-x,y,z}}{add(v[0],v[1],v[2])}
  for _,f:=range [][3]uint32{{0,2,1},{0,3,2},{4,5,6},{4,6,7},{0,1,5},{0,5,4},{1,2,6},{1,6,5},{2,3,7},{2,7,6},{3,0,4},{3,4,7}}{tri(f[0],f[1],f[2])}
 } else if shape=="ellipsoid" {
  const lat,lon=10,20
  for i:=0;i<=lat;i++ {t:=math.Pi*float64(i)/lat;for j:=0;j<=lon;j++ {p:=2*math.Pi*float64(j)/lon;add(d[0]/2*math.Sin(t)*math.Cos(p),d[1]/2*math.Sin(t)*math.Sin(p),d[2]/2*math.Cos(t))}}
  for i:=0;i<lat;i++ {for j:=0;j<lon;j++ {a:=uint32(i*(lon+1)+j);b:=a+lon+1;tri(a,b,a+1);tri(a+1,b,b+1)}}
 } else if shape=="cylinder-x"||shape=="cylinder-y" {
  const n=20
  for i:=0;i<2;i++ {for j:=0;j<n;j++ {a:=2*math.Pi*float64(j)/n;c,si:=math.Cos(a),math.Sin(a)
   if shape=="cylinder-x"{add((float64(i)-.5)*d[0],c*d[1]/2,si*d[2]/2)} else{add(c*d[0]/2,(float64(i)-.5)*d[1],si*d[2]/2)}
  }}
  for j:=0;j<n;j++ {a:=uint32(j);b:=uint32((j+1)%n);tri(a,b,a+n);tri(b,b+n,a+n)}
  for j:=1;j<n-1;j++{tri(0,uint32(j+1),uint32(j));tri(n,n+uint32(j),n+uint32(j+1))}
 } else {panic("invalid shape "+shape)}
 return g
}
func export(s *Builder,out string)error {
 var bin bytes.Buffer
 views:=[]map[string]any{};acc:=[]map[string]any{};meshes:=[]map[string]any{}
 nodes:=make([]map[string]any,len(s.Parts)+1)
 appendBytes:=func(v any,target int)(int,error){
  for bin.Len()%4!=0{bin.WriteByte(0)}
  start:=bin.Len();if err:=binary.Write(&bin,binary.LittleEndian,v);err!=nil{return -1,err}
  item:=map[string]any{"buffer":0,"byteOffset":start,"byteLength":bin.Len()-start}
  if target!=0{item["target"]=target}
  views=append(views,item);return len(views)-1,nil
 }
 children:=map[int][]int{};roots:=[]int{}
 for i,p:=range s.Parts{
  n:=map[string]any{"name":p.Name,"translation":p.Pos,"extras":map[string]any{"kind":"procedural-rig-part","shape":p.Shape}}
  if p.Shape!="pivot"{
   geo:=makeGeometry(p.Shape,p.Size)
   view,e:=appendBytes(geo.Pos,34962);if e!=nil{return e}
   lo:=[]float32{math.MaxFloat32,math.MaxFloat32,math.MaxFloat32};hi:=[]float32{-math.MaxFloat32,-math.MaxFloat32,-math.MaxFloat32}
   for k:=0;k<len(geo.Pos);k+=3{for j:=0;j<3;j++{v:=geo.Pos[k+j];if v<lo[j]{lo[j]=v};if v>hi[j]{hi[j]=v}}}
   acc=append(acc,map[string]any{"bufferView":view,"componentType":5126,"count":len(geo.Pos)/3,"type":"VEC3","min":lo,"max":hi})
   pi:=len(acc)-1
   view,e=appendBytes(geo.Idx,34963);if e!=nil{return e}
   acc=append(acc,map[string]any{"bufferView":view,"componentType":5125,"count":len(geo.Idx),"type":"SCALAR"})
   ii:=len(acc)-1;mi:=len(meshes)
   meshes=append(meshes,map[string]any{"name":p.Name,"primitives":[]any{map[string]any{"attributes":map[string]int{"POSITION":pi},"indices":ii,"material":p.Mat}}})
   n["mesh"]=mi
  }
  nodes[i]=n
  if p.Parent<0{roots=append(roots,i)}else{children[p.Parent]=append(children[p.Parent],i)}
 }
 for parent,ids:=range children{nodes[parent]["children"]=ids}
 for _,rig:=range s.Rigs{for _,j:=range rig.Joints{nodes[j.Node]["extras"]=map[string]any{"kind":"mechanical-joint","rig":rig.Name,"jointType":j.Kind,"axis":j.Axis,"rangeDegrees":[]float64{j.Min,j.Max}}}}
 nodes[len(s.Parts)]=map[string]any{"name":"Z-up-to-glTF-Y-up","rotation":[]float64{-math.Sqrt(.5),0,0,math.Sqrt(.5)},"children":roots}
 samplers:=[]map[string]any{};channels:=[]map[string]any{}
 for _,t:=range s.Tracks{
  tv,e:=appendBytes(t.Times,0);if e!=nil{return e}
  acc=append(acc,map[string]any{"bufferView":tv,"componentType":5126,"count":len(t.Times),"type":"SCALAR","min":[]float32{0},"max":[]float32{8}})
  ti:=len(acc)-1;dv,e:=appendBytes(t.Values,0);if e!=nil{return e}
  acc=append(acc,map[string]any{"bufferView":dv,"componentType":5126,"count":len(t.Times),"type":"VEC4"})
  di:=len(acc)-1;samplers=append(samplers,map[string]any{"input":ti,"output":di,"interpolation":"LINEAR"})
  channels=append(channels,map[string]any{"sampler":len(samplers)-1,"target":map[string]any{"node":t.Node,"path":"rotation"}})
 }
 doc:=map[string]any{"asset":map[string]any{"version":"2.0","generator":"Mechanical Systems Go v0.1"},
  "scene":0,"scenes":[]any{map[string]any{"nodes":[]int{len(s.Parts)}}},
  "nodes":nodes,"meshes":meshes,"materials":s.Mats,
  "buffers":[]map[string]any{{"uri":"mechanical_scene.bin","byteLength":bin.Len()}},
  "bufferViews":views,"accessors":acc,
  "animations":[]any{map[string]any{"name":"articulation-8s","samplers":samplers,"channels":channels}},
  "extras":map[string]any{"schema":"mechanical.scene.v0","rigs":3}}
 if err:=os.MkdirAll(out,0755);err!=nil{return err}
 jsonBytes,e:=json.MarshalIndent(doc,"","  ");if e!=nil{return e}
 if e=os.WriteFile(filepath.Join(out,"mechanical_scene.gltf"),jsonBytes,0644);e!=nil{return e}
 if e=os.WriteFile(filepath.Join(out,"mechanical_scene.bin"),bin.Bytes(),0644);e!=nil{return e}
 // glb embeds the same geometry. Replace only the external buffer URI.
 doc["buffers"]=[]map[string]any{{"byteLength":bin.Len()}}
 packed,e:=json.Marshal(doc);if e!=nil{return e}
 for len(packed)%4!=0{packed=append(packed,' ')}
 raw:=bin.Bytes();for len(raw)%4!=0{raw=append(raw,0)}
 var glb bytes.Buffer
 for _,word:=range []uint32{0x46546c67,2,uint32(12+8+len(packed)+8+len(raw)),uint32(len(packed)),0x4e4f534a}{binary.Write(&glb,binary.LittleEndian,word)}
 glb.Write(packed);for _,word:=range []uint32{uint32(len(raw)),0x004e4942}{binary.Write(&glb,binary.LittleEndian,word)}
 glb.Write(raw)
 if e=os.WriteFile(filepath.Join(out,"mechanical_scene.glb"),glb.Bytes(),0644);e!=nil{return e}
 type JointSpec struct{Name,Kind string;Node int;Axis V;MinDegrees,MaxDegrees float64}
 type RigSpec struct{Name string;Root int;Joints []JointSpec}
 manifest:=struct{Schema string;DurationSeconds,Parts,Tracks int;Rigs []RigSpec}{"mechanical.rig.v0",8,len(s.Parts),len(s.Tracks),nil}
 for _,rig:=range s.Rigs{
  rs:=RigSpec{Name:rig.Name,Root:rig.Root}
  for _,j:=range rig.Joints{rs.Joints=append(rs.Joints,JointSpec{j.Name,j.Kind,j.Node,j.Axis,j.Min,j.Max})}
  manifest.Rigs=append(manifest.Rigs,rs)
 }
 receipt,e:=json.MarshalIndent(manifest,"","  ");if e!=nil{return e}
 return os.WriteFile(filepath.Join(out,"rig_manifest.json"),receipt,0644)
}
func main(){out:=flag.String("out","out","generated artifact directory");flag.Parse()
 s:=makeScene();if err:=export(s,*out);err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}
 fmt.Printf("generated %d parts, %d moving joints, %d keyframe tracks\n",len(s.Parts),func()int{n:=0;for _,r:=range s.Rigs{n+=len(r.Joints)};return n}(),len(s.Tracks))
}