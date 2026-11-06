package main

import (
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

var actors = []string{"AsterOriginal","JuniperOriginal"}
var views = []string{"front","side","face"}

func makeFixture(t *testing.T, root string, crop, blank, opaque bool) string {
    t.Helper()
    i:=Index{
        Schema:"scp.r009.source_original_alpha_masks.v1",
        SourceSHA:strings.Repeat("a",64),FileCount:6,
        Pose:"REST",Pixels:"RGBA_FILM_TRANSPARENT",BlenderVersion:"4.5.15 LTS",
    }
    for _,actor:=range actors{
        for _,view:=range views{
            p:=image.NewNRGBA(image.Rect(0,0,768,768))
            if opaque {
                for y:=0;y<768;y++ {for x:=0;x<768;x++ {
                    p.SetNRGBA(x,y,color.NRGBA{R:120,G:120,B:120,A:255})
                }}
            }else if !blank{
                left,right:=220,550
                top,bottom:=94,680
                if view=="face"{left,right,top,bottom=270,500,200,500}
                if crop{left=0}
                for y:=top;y<bottom;y++{for x:=left;x<right;x++{
                    p.SetNRGBA(x,y,color.NRGBA{R:140,G:80,B:60,A:255})
                }}
            }
            name:=actor+"_"+view+"_alpha.png"
            output:=filepath.Join(root,name)
            f,err:=os.Create(output)
            if err!=nil{t.Fatal(err)}
            if err=png.Encode(f,p);err!=nil{t.Fatal(err)}
            if err=f.Close();err!=nil{t.Fatal(err)}
            raw,err:=os.ReadFile(output);if err!=nil{t.Fatal(err)}
            sum:=sha256.Sum256(raw)
            i.Images=append(i.Images,ImageMeta{
                Actor:actor,View:view,Name:name,SHA256:hex.EncodeToString(sum[:]),
                Bytes:len(raw),CameraScale:2.45,Preset:"adventure",
            })
        }
    }
    doc,_:=json.MarshalIndent(i,"","  ")
    out:=filepath.Join(root,"alpha_index.json")
    if err:=os.WriteFile(out,doc,0600);err!=nil{t.Fatal(err)}
    return out
}
func readIndex(t *testing.T,path string) Index {
    t.Helper()
    raw,err:=os.ReadFile(path);if err!=nil{t.Fatal(err)}
    var i Index
    if err:=json.Unmarshal(raw,&i);err!=nil{t.Fatal(err)}
    return i
}
func rewriteIndex(t *testing.T,path string,i Index){
    t.Helper()
    raw,err:=json.Marshal(i);if err!=nil{t.Fatal(err)}
    if err:=os.WriteFile(path,raw,0600);err!=nil{t.Fatal(err)}
}
func TestSixNativeAlphaViewsAndScienceAbstention(t *testing.T) {
    path:=makeFixture(t,t.TempDir(),false,false,false)
    r,err:=Evaluate(path);if err!=nil{t.Fatal(err)}
    if r.Count!=6 || r.CropScreen!="PASS_ALL_SIX_ALPHA_FRAMES_GEOMETRIC_ONLY" {
        t.Fatalf("unexpected receipt %#v",r)
    }
    if r.AnatomicalAccuracyAccepted || r.GarmentClearanceAccepted ||
        r.FaceIdentityAccepted || r.SexFromImageInferred {t.Fatal("false scientific acceptance")}
    for _,v:=range r.Captures{
        if v.AlphaPixels==0 || v.MiddleBandWidth==0 || v.Coverage<=.01 {
            t.Fatalf("bad alpha view %#v",v)
        }
    }
}
func TestCroppedSourceFailsClosed(t *testing.T){
    path:=makeFixture(t,t.TempDir(),true,false,false)
    _,err:=Evaluate(path)
    if err==nil || !strings.Contains(err.Error(),"SILHOUETTE_CROPPED"){
        t.Fatalf("crop oracle accepted invalid frame: %v",err)
    }
}
func TestBlankAndOpaqueSourcesFail(t *testing.T){
    for _,tc:=range []struct{blank,opaque bool;why string}{
        {true,false,"BLANK_SILHOUETTE"},
        {false,true,"ALPHA_BACKGROUND_MISSING"},
    }{
        path:=makeFixture(t,t.TempDir(),false,tc.blank,tc.opaque)
        _,err:=Evaluate(path)
        if err==nil || !strings.Contains(err.Error(),tc.why){
            t.Fatalf("accepted %s: %v",tc.why,err)
        }
    }
}
func TestForgedDigestRejected(t *testing.T){
    path:=makeFixture(t,t.TempDir(),false,false,false)
    i:=readIndex(t,path);i.Images[0].SHA256=strings.Repeat("0",64);rewriteIndex(t,path,i)
    _,err:=Evaluate(path)
    if err==nil || !strings.Contains(err.Error(),"PNG_BYTES_OR_DIGEST_MISMATCH"){
        t.Fatalf("accepted tampered image hash: %v",err)
    }
}
func TestDuplicateOrMissingNativeViewRejected(t *testing.T){
    path:=makeFixture(t,t.TempDir(),false,false,false)
    i:=readIndex(t,path);i.Images[5].View=i.Images[4].View;rewriteIndex(t,path,i)
    _,err:=Evaluate(path)
    if err==nil || !strings.Contains(err.Error(),"INVALID_DUPLICATE"){
        t.Fatalf("accepted duplicate/missing view: %v",err)
    }
}
func TestUnsafePathAndFalseScienceRejected(t *testing.T) {
    path:=makeFixture(t,t.TempDir(),false,false,false)
    i:=readIndex(t,path);i.Images[0].Name="../out.png";rewriteIndex(t,path,i)
    _,err:=Evaluate(path)
    if err==nil || !strings.Contains(err.Error(),"UNSAFE_IMAGE_NAME"){
        t.Fatalf("accepted traversal: %v",err)
    }
    i=readIndex(t,path);i.Images[0].Name="safe.png";i.FullBodyAccepted=true
    rewriteIndex(t,path,i)
    _,err=Evaluate(path)
    if err==nil || !strings.Contains(err.Error(),"INDEX_OR_SCIENCE_CONTRACT"){
        t.Fatalf("accepted falsely approved science: %v",err)
    }
}
func TestNanAndBadCameraRejected(t *testing.T) {
    path:=makeFixture(t,t.TempDir(),false,false,false)
    i:=readIndex(t,path);i.Images[0].CameraScale=0
    rewriteIndex(t,path,i)
    _,err:=Evaluate(path)
    if err==nil || !strings.Contains(err.Error(),"INVALID_DUPLICATE"){
        t.Fatalf("accepted bad camera: %v",err)
    }
}
func TestBadIndexSHARejected(t *testing.T) {
    path:=makeFixture(t,t.TempDir(),false,false,false)
    i:=readIndex(t,path);i.SourceSHA="NOT_HASH"
    rewriteIndex(t,path,i)
    _,err:=Evaluate(path)
    if err==nil || !strings.Contains(err.Error(),"INDEX_OR_SCIENCE_CONTRACT"){
        t.Fatalf("accepted bad source lineage: %v",err)
    }
}


func replaceFaceFixture(t *testing.T, indexPath string, top int) {
    t.Helper()
    idx:=readIndex(t,indexPath)
    for n,m:=range idx.Images {
        if m.Actor!="AsterOriginal" || m.View!="face"{continue}
        p:=image.NewNRGBA(image.Rect(0,0,768,768))
        for y:=top;y<768;y++ {for x:=275;x<495;x++ {
            p.SetNRGBA(x,y,color.NRGBA{R:120,G:75,B:65,A:255})
        }}
        file:=filepath.Join(filepath.Dir(indexPath),m.Name)
        out,err:=os.Create(file);if err!=nil{t.Fatal(err)}
        if err=png.Encode(out,p);err!=nil{t.Fatal(err)}
        if err=out.Close();err!=nil{t.Fatal(err)}
        raw,err:=os.ReadFile(file);if err!=nil{t.Fatal(err)}
        digest:=sha256.Sum256(raw)
        idx.Images[n].SHA256=hex.EncodeToString(digest[:])
        idx.Images[n].Bytes=len(raw)
        rewriteIndex(t,indexPath,idx)
        return
    }
    t.Fatal("missing AsterOriginal/face fixture")
}
func TestIntentionalFaceBottomCropDoesNotDisableFullBodyGuard(t *testing.T){
    path:=makeFixture(t,t.TempDir(),false,false,false)
    replaceFaceFixture(t,path,175)
    r,err:=Evaluate(path)
    if err!=nil{t.Fatal(err)}
    for _,o:=range r.Captures {
        if o.Actor=="AsterOriginal" && o.View=="face" {
            if o.Margins[2]!=0 || o.Result!="PASS_FACE_TOP_AND_SIDE_FRAMING_ONLY"{
                t.Fatalf("unexpected face ROI %#v",o)
            }
            return
        }
    }
    t.Fatal("face observation not reported")
}
func TestFaceForeheadCropStillFails(t *testing.T){
    path:=makeFixture(t,t.TempDir(),false,false,false)
    replaceFaceFixture(t,path,0)
    _,err:=Evaluate(path)
    if err==nil || !strings.Contains(err.Error(),"FACE_FOREHEAD_OR_SIDE_CROPPED"){
        t.Fatalf("accepted cropped forehead: %v",err)
    }
}
