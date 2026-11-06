package main
import(
 "bytes"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "image"
 "image/color"
 "image/png"
 "os"
 "path/filepath"
 "strings"
 "testing"
)
func h(c string)string{return strings.Repeat(c,64)}
func pngFixture(t *testing.T,root,name string,shade uint8)string{
 t.Helper()
 img:=image.NewNRGBA(image.Rect(0,0,12,12))
 for y:=0;y<12;y++{for x:=0;x<12;x++{img.Set(x,y,color.NRGBA{R:shade,G:uint8(x*10),B:uint8(y*10),A:255})}}
 var b bytes.Buffer
 if e:=png.Encode(&b,img);e!=nil{t.Fatal(e)}
 if e:=os.WriteFile(filepath.Join(root,name),b.Bytes(),0600);e!=nil{t.Fatal(e)}
 sha:=sha256.Sum256(b.Bytes());return hex.EncodeToString(sha[:])
}
func setup(t *testing.T)(string,Manifest){
 t.Helper();root:=t.TempDir()
 m:=Manifest{Schema:"scp.synthetic_observations.v1",SubjectClass:"public_original_synthetic_equine",
 SubjectID:"original_pony_001",RightsClass:"original_self_authored_synthetic"}
 for i,x:=range []struct{name,cam,family,split,rootHash string}{
 {"train_a.png","camera_a","capture_one","training",h("a")},
 {"train_b.png","camera_b","capture_one","training",h("a")},
 {"heldout_c.png","camera_c","capture_two","heldout",h("b")},
 }{
  sh:=pngFixture(t,root,x.name,uint8((i+1)*51))
  m.Observations=append(m.Observations,Observation{ID:"image_0"+string(rune('1'+i)),Path:x.name,
  SHA256:sh,SourceRootSHA256:x.rootHash,CaptureFamily:x.family,CameraID:x.cam,Split:x.split})
 }
 return root,m
}
func encoded(m Manifest)[]byte{b,_:=json.Marshal(m);return b}
func TestTrueDecodedSourceBytes(t *testing.T){
 root,m:=setup(t)
 r,e:=admit(root,encoded(m));if e!=nil{t.Fatal(e)}
 if r.Training!=2||r.Heldout!=1||len(r.Observations)!=3{t.Fatal("wrong counts")}
 if r.ScientificResult!="UNKNOWN"||r.ExternalPhotoAdmission!="NOT_RUN"||r.Mutation{t.Fatal("false scientific success")}
 if r.CameraIndependence!="UNKNOWN_NO_EXTERNAL_CALIBRATION"{t.Fatal("false camera acceptance")}
 if r.Observations[0].Width!=12{t.Fatal("did not inspect PNG")}
 a,e:=admit(root,encoded(m));if e!=nil||r.ManifestSHA256!=a.ManifestSHA256{t.Fatal("unstable receipt",e)}
}
func TestStrictJSON(t *testing.T){
 _,m:=setup(t);b:=encoded(m)
 if _,e:=parse(b);e!=nil{t.Fatal(e)}
 for _,bad:=range []string{string(b)+" {}",`{"schema":"x","schema":"y"}`,`{"observations":[{"id":"x","id":"y"}]}`,`{"unknown":1}`}{
  if _,e:=parse([]byte(bad));e==nil{t.Fatal("invalid JSON accepted")}
 }
}
func TestLeakageAndRights(t *testing.T){
 _,orig:=setup(t)
 cases:=[]struct{name string;change func(*Manifest)}{
  {"protected",func(m *Manifest){m.SubjectClass="private_human"}},
  {"rights",func(m *Manifest){m.RightsClass="web_scraped"}},
  {"family_leak",func(m *Manifest){m.Observations[2].CaptureFamily=m.Observations[0].CaptureFamily}},
  {"root_leak",func(m *Manifest){m.Observations[2].SourceRootSHA256=m.Observations[0].SourceRootSHA256}},
  {"image_leak",func(m *Manifest){m.Observations[2].SHA256=m.Observations[0].SHA256}},
  {"bad_split",func(m *Manifest){m.Observations[2].Split="validation"}},
  {"same_train_camera",func(m *Manifest){m.Observations[1].CameraID="camera_a"}},
  {"duplicate_id",func(m *Manifest){m.Observations[1].ID=m.Observations[0].ID}},
  {"reused_path",func(m *Manifest){m.Observations[1].Path=m.Observations[0].Path}},
  {"path_escape",func(m *Manifest){m.Observations[0].Path="../other.png"}},
  {"bad_timestamp",func(m *Manifest){m.Observations[0].FrameTimeNS=-1}},
 }
 for _,tc:=range cases{t.Run(tc.name,func(t *testing.T){m:=orig; m.Observations=append([]Observation(nil),orig.Observations...);tc.change(&m);if e:=validate(m);e==nil{t.Fatal("invalid observation admitted")}})}
}
func TestTamperAndEscape(t *testing.T){
 root,m:=setup(t)
 if e:=os.WriteFile(filepath.Join(root,m.Observations[0].Path),[]byte("tampered"),0600);e!=nil{t.Fatal(e)}
 if _,e:=admit(root,encoded(m));e==nil{t.Fatal("changed image passed digest")}
 root,m=setup(t)
 other:=t.TempDir()
 original:=filepath.Join(other,"other.png")
 if e:=os.WriteFile(original,[]byte("outside"),0600);e!=nil{t.Fatal(e)}
 if e:=os.Symlink(original,filepath.Join(root,"symlink.png"));e!=nil{t.Skip("symlinks unsupported")}
 m.Observations[0].Path="symlink.png"
 if _,e:=admit(root,encoded(m));e==nil||!strings.Contains(e.Error(),"escapes"){t.Fatal("symlink escape accepted",e)}
}
func TestRejectBadPNGWithCorrectHash(t *testing.T){
 root,m:=setup(t)
 raw:=[]byte("not a PNG even with good hash")
 p:=filepath.Join(root,m.Observations[0].Path)
 if e:=os.WriteFile(p,raw,0600);e!=nil{t.Fatal(e)}
 digest:=sha256.Sum256(raw)
 m.Observations[0].SHA256=hex.EncodeToString(digest[:])
 if _,e:=admit(root,encoded(m));e==nil{t.Fatal("non-PNG data accepted")}
}
