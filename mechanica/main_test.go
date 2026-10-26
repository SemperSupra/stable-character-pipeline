package main
import (
 "bytes"
 "encoding/binary"
 "encoding/json"
 "math"
 "os"
 "path/filepath"
 "testing"
)
func TestIndependentRigCatalog(t *testing.T) {
 s:=makeScene()
 if len(s.Rigs)!=4 {t.Fatalf("rig count = %d",len(s.Rigs))}
 names:=[]string{"ground/suv","air/utility-twin","space/orbital-tug","titan/iron-atlas"}
 seen:=map[string]bool{}
 total:=0
 for i,r:=range s.Rigs {
  if r.Name!=names[i] {t.Errorf("rig %d is %s",i,r.Name)}
  if len(r.Joints)<5 {t.Errorf("rig %s too few joints: %d",r.Name,len(r.Joints))}
  for _,j:=range r.Joints {
   total++
   if seen[j.Name] {t.Error("duplicate joint",j.Name)}
   seen[j.Name]=true
   if j.Node<=r.Root || j.Node>=len(s.Parts) {t.Error("invalid joint node",j.Name)}
   if j.Min>j.Max {t.Error("inverted joint bounds",j.Name)}
   if math.Hypot(math.Hypot(j.Axis[0],j.Axis[1]),j.Axis[2])<.99 {t.Error("invalid axis",j.Name)}
  }
 }
 if len(s.Rigs[3].Joints)<20 {t.Fatalf("mech has too few articulated joints: %d",len(s.Rigs[3].Joints))}
 if total!=len(s.Tracks) {t.Fatalf("joints %d, tracks %d",total,len(s.Tracks))}
 for _,name:=range []string{"car/left/front-hinge","car/right/rear-hinge","car/tailgate-hinge","air/port/flap","air/starboard/propeller","air/elevator","air/rudder","air/port/landing-gear","space/port/solar-yoke","space/docking-hatch","space/antenna-pan","titan/iron-atlas/torso-yaw","titan/iron-atlas/cockpit-yaw","titan/iron-atlas/port/hip-pitch","titan/iron-atlas/starboard/knee-pitch","titan/iron-atlas/port/cannon-elevation","titan/iron-atlas/starboard/claw-finger-1","titan/iron-atlas/maintenance-hatch","titan/iron-atlas/port/pod-elevation"} {
  if !seen[name] {t.Error("missing articulated mechanism",name)}
 }
}
func TestAnimationsAreFiniteAndMoving(t *testing.T) {
 s:=makeScene()
 for _,a:=range s.Tracks {
  if len(a.Times)<4 || len(a.Values)!=len(a.Times)*4 {t.Fatal("bad keyframe width",a.Node)}
  if a.Times[0]!=0 || a.Times[len(a.Times)-1]!=8 {t.Fatal("bad timeline",a.Node)}
  changed:=false
  for i,v:=range a.Values {
   if math.IsNaN(float64(v))||math.IsInf(float64(v),0){t.Fatal("nonfinite quaternion")}
   if i>=4 && math.Abs(float64(v-a.Values[i%4]))>.001 {changed=true}
  }
  if !changed {t.Fatal("static animation",a.Node)}
 }
}
func TestGLBAndReproducibleExport(t *testing.T) {
 a,b:=t.TempDir(),t.TempDir()
 for _,d:=range []string{a,b} {if e:=export(makeScene(),d);e!=nil{t.Fatal(e)}}
 for _,n:=range []string{"mechanical_scene.gltf","mechanical_scene.bin","mechanical_scene.glb","rig_manifest.json"} {
  x,e:=os.ReadFile(filepath.Join(a,n));if e!=nil{t.Fatal(e)}
  y,e:=os.ReadFile(filepath.Join(b,n));if e!=nil{t.Fatal(e)}
  if !bytes.Equal(x,y){t.Error("non deterministic "+n)}
 }
 g,e:=os.ReadFile(filepath.Join(a,"mechanical_scene.glb"));if e!=nil{t.Fatal(e)}
 if len(g)<32||binary.LittleEndian.Uint32(g[:4])!=0x46546c67||binary.LittleEndian.Uint32(g[8:12])!=uint32(len(g)){t.Fatal("GLB header/length")}
 data,e:=os.ReadFile(filepath.Join(a,"mechanical_scene.gltf"));if e!=nil{t.Fatal(e)}
 var doc map[string]any
 if e=json.Unmarshal(data,&doc);e!=nil{t.Fatal(e)}
 if len(doc["animations"].([]any))!=1||len(doc["meshes"].([]any))<30{t.Fatal("missing exported meshes or animation")}
}
