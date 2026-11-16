package main

import (
	"bytes"
	"encoding/json"
	"image"
	"image/color"
	"image/png"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func fixture(t *testing.T, root, arm string, shift uint8, solid bool) string {
	t.Helper()
	dir:=filepath.Join(root,arm)
	if err:=os.MkdirAll(dir,0755);err!=nil{t.Fatal(err)}
	img:=image.NewNRGBA(image.Rect(0,0,64,64))
	for y:=0;y<64;y++ {
		for x:=0;x<64;x++ {
			var v uint8
			if solid {v=120} else {v=uint8((x*3+y*2)%180)+shift}
			img.SetNRGBA(x,y,color.NRGBA{R:v,G:uint8((x+y)%180)+shift,B:55,A:255})
		}
	}
	var buf bytes.Buffer
	if err:=png.Encode(&buf,img);err!=nil{t.Fatal(err)}
	p:=filepath.Join(dir,"beauty.png")
	if err:=os.WriteFile(p,buf.Bytes(),0644);err!=nil{t.Fatal(err)}
	exr:=append([]byte{0x76,0x2f,0x31,0x01},[]byte("SYNTHETIC_SIGNATURE_ONLY_NOT_VALID_EXR")...)
	if err:=os.WriteFile(filepath.Join(dir,"passes.exr"),exr,0644);err!=nil{t.Fatal(err)}
	r:=Receipt{
		SchemaVersion:schema,
		ExperimentID:"r037-synthetic-material-screen",
		SceneID:"original-synthetic-head-v1",
		SourceSHA256:digest([]byte("original-synthetic-head-v1")),
		GeometrySHA256:digest([]byte("geometry")),
		CameraSHA256:digest([]byte("camera")),
		AnimationSHA256:digest([]byte("animation")),
		Arm:arm,Seed:13,Rights:"ORIGINAL_SYNTHETIC",
		Status:"PASS_RENDER_ONLY",Engine:"CYCLES",Samples:12,
		Resolution:64,ElapsedSeconds:1.5,
		BeautyPNG:Artifact{"beauty.png",digest(buf.Bytes())},
		RenderPassesEXR:Artifact{"passes.exr",digest(exr)},
	}
	data,err:=json.Marshal(r)
	if err!=nil{t.Fatal(err)}
	p=filepath.Join(dir,"receipt.json")
	if err:=os.WriteFile(p,data,0644);err!=nil{t.Fatal(err)}
	return p
}

func rewrite(t *testing.T, path string, change func(*Receipt)) {
	t.Helper()
	b,err:=os.ReadFile(path)
	if err!=nil{t.Fatal(err)}
	var r Receipt
	if err:=json.Unmarshal(b,&r);err!=nil{t.Fatal(err)}
	change(&r)
	b,err=json.Marshal(r)
	if err!=nil{t.Fatal(err)}
	if err:=os.WriteFile(path,b,0644);err!=nil{t.Fatal(err)}
}

func TestPairedSyntheticStructuralEvidence(t *testing.T) {
	root:=t.TempDir()
	a:=fixture(t,root,"baseline",0,false)
	b:=fixture(t,root,"physical_material",15,false)
	r,err:=compare(a,b)
	if err!=nil{t.Fatal(err)}
	if r.Status!="PASS_STRUCTURAL_RENDER_DIFFERENCE_ONLY" ||
		r.Qualification!="NOT_PHOTOREALISM_OR_HUMAN_PREFERENCE_EVIDENCE" ||
		r.ChangedPixelFraction<=0 || r.MeanAbsoluteRGBDelta<=0 {t.Fatalf("wrong status: %+v",r)}
}

func TestRejectGeometryDrift(t *testing.T) {
	root:=t.TempDir()
	a:=fixture(t,root,"baseline",0,false)
	b:=fixture(t,root,"physical_material",15,false)
	rewrite(t,b,func(r *Receipt){r.GeometrySHA256=digest([]byte("different geometry"))})
	if _,err:=compare(a,b);err==nil{t.Fatal("geometry drift falsely passed")}
}

func TestRejectDifferentCameraAndPose(t *testing.T) {
	for _,dimension:=range []string{"camera","pose"} {
		t.Run(dimension,func(t *testing.T){
			root:=t.TempDir()
			a:=fixture(t,root,"baseline",0,false)
			b:=fixture(t,root,"physical_material",15,false)
			rewrite(t,b,func(r *Receipt){
				if dimension=="camera" {r.CameraSHA256=digest([]byte("drift"))} else {r.AnimationSHA256=digest([]byte("drift"))}
			})
			if _,err:=compare(a,b);err==nil{t.Fatal("drift falsely passed")}
		})
	}
}

func TestRejectSourceRightsAndTamper(t *testing.T) {
	for _,dimension:=range []string{"rights","digest","path","source"} {
		t.Run(dimension,func(t *testing.T){
			root:=t.TempDir()
			a:=fixture(t,root,"baseline",0,false)
			b:=fixture(t,root,"physical_material",15,false)
			rewrite(t,b,func(r *Receipt){
				switch dimension {
				case "rights":r.Rights="UNKNOWN"
				case "digest":r.BeautyPNG.SHA256=digest([]byte("wrong"))
				case "path":r.BeautyPNG.File="../beauty.png"
				case "source":r.SourceSHA256=digest([]byte("unrecognized"))
				}
			})
			if _,err:=compare(a,b);err==nil{t.Fatal("unsafe fixture falsely passed")}
		})
	}
}

func TestRejectBlankImage(t *testing.T) {
	root:=t.TempDir()
	a:=fixture(t,root,"baseline",0,false)
	b:=fixture(t,root,"physical_material",15,true)
	// The helper's solid flag still varies G; enforce an actually constant PNG.
	p:=filepath.Join(root,"physical_material","beauty.png")
	im:=image.NewNRGBA(image.Rect(0,0,64,64))
	for y:=0;y<64;y++ {for x:=0;x<64;x++ {im.SetNRGBA(x,y,color.NRGBA{R:120,G:120,B:120,A:255})}}
	var out bytes.Buffer
	if err:=png.Encode(&out,im);err!=nil{t.Fatal(err)}
	if err:=os.WriteFile(p,out.Bytes(),0644);err!=nil{t.Fatal(err)}
	rewrite(t,b,func(r *Receipt){r.BeautyPNG.SHA256=digest(out.Bytes())})
	if _,err:=compare(a,b);err==nil{t.Fatal("blank image falsely passed")}
}

func TestRejectDuplicateKeysUnknownFieldsAndTrailingData(t *testing.T) {
	cases:=[]string{
		`{"arm":"baseline","arm":"physical_material"}`,
		`{"unknown_parameter":true}`,
		`{"arm":"baseline"}{"arm":"material"}`,
	}
	for _,s:=range cases {
		var r Receipt
		if err:=decodeStrict([]byte(s),&r);err==nil{t.Fatalf("accepted malformed data %s",s)}
	}
}

func TestRejectNonFiniteAndNegativeElapsed(t *testing.T) {
	root:=t.TempDir()
	p:=fixture(t,root,"baseline",0,false)
	for _,elapsed:=range []float64{-1,0,1e9} {
		rewrite(t,p,func(r *Receipt){r.ElapsedSeconds=elapsed})
		if _,_,_,err:=loadReceipt(p);err==nil{t.Fatalf("accepted elapsed=%f",elapsed)}
	}
	// Raw NaN tokens are invalid JSON and cannot bypass strict parsing.
	var r Receipt
	if err:=decodeStrict([]byte(strings.Replace(`{"elapsed_seconds": 1}`,"1","NaN",1)),&r);err==nil{
		t.Fatal("accepted NaN")
	}
}
