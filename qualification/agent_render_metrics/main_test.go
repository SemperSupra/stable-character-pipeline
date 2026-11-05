package main

import (
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
func digest(c string)string{return strings.Repeat(c,64)}
func fixture(t *testing.T,dir,name string,w,h int,points [][2]int,channel string)Source{
 t.Helper()
 im:=image.NewNRGBA(image.Rect(0,0,w,h))
 for y:=0;y<h;y++{for x:=0;x<w;x++{
  v:=color.NRGBA{R:0,G:0,B:0,A:0}
  if channel=="luma"{v.A=255}
  for _,pt:=range points{if pt[0]==x&&pt[1]==y{v=color.NRGBA{R:255,G:255,B:255,A:255}}}
  im.SetNRGBA(x,y,v)
 }}
 var b bytes.Buffer
 if e:=png.Encode(&b,im);e!=nil{t.Fatal(e)}
 if e:=os.WriteFile(filepath.Join(dir,name),b.Bytes(),0600);e!=nil{t.Fatal(e)}
 sha:=sha256.Sum256(b.Bytes())
 return Source{Path:name,SHA256:hex.EncodeToString(sha[:])}
}
func setup(t *testing.T)(string,Request){
 t.Helper();root:=t.TempDir()
 ref:=fixture(t,root,"reference.png",4,4,[][2]int{{1,1},{2,1},{1,2},{2,2}},"alpha")
 base:=fixture(t,root,"baseline.png",4,4,[][2]int{{1,1},{2,1},{3,2},{3,3}},"alpha")
 cand:=fixture(t,root,"candidate.png",4,4,[][2]int{{1,1},{2,1},{1,2},{3,3}},"alpha")
 return root,Request{
 Schema:"scp.render_masks.v1",ExperimentID:"synthetic_pony_silhouette",
 BaselineSHA256:digest("a"),CandidateSHA256:digest("b"),
 SubjectClass:"public_original_synthetic_equine",CameraID:"heldout_side",FrameIndex:12,
 Split:"heldout",Channel:"alpha",Threshold:128,
 Reference:ref,Baseline:base,Candidate:cand,
 }
}
func TestPNGMeasuredPixels(t *testing.T){
 root,q:=setup(t)
 if e:=validate(q);e!=nil{t.Fatal(e)}
 r,e:=measure(root,q);if e!=nil{t.Fatal(e)}
 if r.ReferenceForeground!=4||r.Width!=4||r.Height!=4{t.Fatal("source geometry",r)}
 if r.Baseline.Intersection!=2||r.Baseline.Union!=6{t.Fatal("baseline not actual PNG",r)}
 if r.Candidate.Intersection!=3||r.Candidate.Union!=5{t.Fatal("candidate not actual PNG",r)}
 if r.Baseline.IoU<0.3333||r.Baseline.IoU>0.3334||r.Candidate.IoU!=0.6{t.Fatal("bad IoU",r)}
 if r.DeltaIoU<0.2666||r.DeltaIoU>0.2667{t.Fatal("bad improvement",r)}
 if r.SourceAttestation!="UNAUTHENTICATED_SPLIT_AND_CAMERA_METADATA"{t.Fatal("false attestation",r)}
 b,e:=json.Marshal(r);if e!=nil||!json.Valid(b){t.Fatal("invalid JSON",e)}
}
func TestBadManifest(t *testing.T){
 _,q:=setup(t)
 cases:=[]struct{name string;mod func(*Request)}{
  {"private",func(v *Request){v.SubjectClass="private_human"}},
  {"no_heldout",func(v *Request){v.Split="training"}},
  {"unrecognized_operation",func(v *Request){v.Channel="red"}},
  {"path_escape",func(v *Request){v.Reference.Path="../secret.png"}},
  {"wrong_hash",func(v *Request){v.Baseline.SHA256="ff"}},
  {"identical_model",func(v *Request){v.CandidateSHA256=v.BaselineSHA256}},
  {"threshold",func(v *Request){v.Threshold=256}},
  {"view_injection",func(v *Request){v.CameraID="../../private"}},
  {"frame",func(v *Request){v.FrameIndex=-1}},
 }
 for _,tc:=range cases{t.Run(tc.name,func(t *testing.T){x:=q;tc.mod(&x);if validate(x)==nil{t.Fatal("bad source admitted")}})}
}
func TestStrictJSON(t *testing.T){
 _,q:=setup(t);b,e:=json.Marshal(q);if e!=nil{t.Fatal(e)}
 got,e:=parse(b);if e!=nil||got.Reference.SHA256!=q.Reference.SHA256{t.Fatal("good manifest rejected",e)}
 for _,bad:=range []string{string(b)+" {}",`{"schema":"a","schema":"b"}`,`{"reference":{"path":"a","path":"b"}}`,`{"unknown":4}`}{if _,e:=parse([]byte(bad));e==nil{t.Fatal("bad JSON admitted")}}
}
func TestWrongImageBytes(t *testing.T){
 root,q:=setup(t)
 q.Candidate.SHA256=digest("f")
 if _,e:=measure(root,q);e==nil{t.Fatal("tampered PNG admitted")}
}
func TestDimensionsAndEmptyReference(t *testing.T){
 root,q:=setup(t)
 q.Candidate=fixture(t,root,"wrong_size.png",5,4,[][2]int{{1,1}},"alpha")
 if _,e:=measure(root,q);e==nil{t.Fatal("mismatched image sizes accepted")}
 q.Candidate=fixture(t,root,"candidate2.png",4,4,[][2]int{{1,1}},"alpha")
 q.Reference=fixture(t,root,"empty.png",4,4,nil,"alpha")
 if _,e:=measure(root,q);e==nil{t.Fatal("no-foreground reference accepted")}
}
func TestSymlinkEscape(t *testing.T){
 root,q:=setup(t);outside:=t.TempDir()
 if e:=os.WriteFile(filepath.Join(outside,"other.png"),[]byte("not a PNG"),0600);e!=nil{t.Fatal(e)}
 if e:=os.Symlink(filepath.Join(outside,"other.png"),filepath.Join(root,"outside.png"));e!=nil{t.Skip("symlink unavailable")}
 q.Reference.Path="outside.png"
 if _,e:=measure(root,q);e==nil||!strings.Contains(e.Error(),"escapes root"){t.Fatalf("symlink escape accepted or misdiagnosed: %v",e)}
}
func TestLumaAndSoftEdges(t *testing.T){
 root:=t.TempDir()
 ref:=fixture(t,root,"ref.png",3,3,[][2]int{{1,1}},"luma")
 baseline:=fixture(t,root,"base.png",3,3,[][2]int{{2,2}},"luma")
 cand:=fixture(t,root,"cand.png",3,3,[][2]int{{1,1}},"luma")
 q:=Request{Schema:"scp.render_masks.v1",ExperimentID:"human_luma_trial",BaselineSHA256:digest("a"),CandidateSHA256:digest("c"),SubjectClass:"public_original_synthetic_human",CameraID:"withheld_front",FrameIndex:5,Split:"heldout",Channel:"luma",Threshold:128,Reference:ref,Baseline:baseline,Candidate:cand}
 r,e:=measure(root,q);if e!=nil{t.Fatal(e)}
 if r.Baseline.IoU!=0||r.Candidate.IoU!=1{t.Fatal("bad luma masks",r)}
}
