// R065: source-original decoded frame geometric witness, not a human-motion critic.
// No model output/semantic claim can override this independently measured direction.
package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"image"
	"image/color"
	"image/draw"
	"image/png"
	"math"
	"os"
	"path/filepath"
)

type Point struct {
	X float64 `json:"x"`
	Pixels int `json:"pixels"`
	Width int `json:"width"`
	Height int `json:"height"`
}

type Receipt struct {
	Schema string `json:"schema"`
	SourceSHA string `json:"source_sha"`
	Status string `json:"status"`
	Decision string `json:"decision"`
	Expected string `json:"expected"`
	FirstFrameSHA string `json:"first_frame_sha256"`
	SecondFrameSHA string `json:"second_frame_sha256"`
	DeltaPixels float64 `json:"delta_x_pixels"`
	FirstCount int `json:"first_red_pixels"`
	SecondCount int `json:"second_red_pixels"`
	Reason string `json:"reason,omitempty"`
	Scope string `json:"scope"`
}

func marker(p string) (Point,error) {
	f,err:=os.Open(p)
	if err!=nil {return Point{},err}
	defer f.Close()
	img,err:=png.Decode(f)
	if err!=nil {return Point{},err}
	b:=img.Bounds()
	var sum float64
	var n int
	for y:=b.Min.Y;y<b.Max.Y;y++ {
		for x:=b.Min.X;x<b.Max.X;x++ {
			cr,cg,cb,ca:=img.At(x,y).RGBA()
			r,g,bl,a:=int(cr>>8),int(cg>>8),int(cb>>8),int(ca>>8)
			if a>=220 && r>=170 && r>=g+65 && r>=bl+65 {
				sum+=float64(x-b.Min.X)
				n++
			}
		}
	}
	if n<100 {return Point{},errors.New("NO_RED_SUBJECT")}
	return Point{X:sum/float64(n),Pixels:n,Width:b.Dx(),Height:b.Dy()},nil
}

func classify(first,second Point) (string,float64,error) {
	if first.Width!=second.Width || first.Height!=second.Height {
		return "UNKNOWN",0,errors.New("FRAME_DIMENSION_MISMATCH")
	}
	if first.Pixels<100||second.Pixels<100 {
		return "UNKNOWN",0,errors.New("NO_RED_SUBJECT")
	}
	ratio:=float64(second.Pixels)/float64(first.Pixels)
	if ratio<0.85||ratio>1.15 {
		return "UNKNOWN",0,errors.New("RED_SUBJECT_AREA_INCONSISTENT")
	}
	dx:=second.X-first.X
	if math.Abs(dx)<=10{return "STILL",dx,nil}
	if dx>0{return "RIGHT",dx,nil}
	return "LEFT",dx,nil
}

func genFrame(dir string, idx,x int,red bool) error {
	img:=image.NewRGBA(image.Rect(0,0,224,224))
	draw.Draw(img,img.Bounds(),&image.Uniform{C:color.RGBA{255,255,255,255}},image.Point{},draw.Src)
	if red {
		draw.Draw(img,image.Rect(x,80,x+60,140),
			&image.Uniform{C:color.RGBA{255,0,0,255}},image.Point{},draw.Src)
	}
	path:=filepath.Join(dir,fmt.Sprintf("frame_%03d.png",idx))
	f,err:=os.Create(path)
	if err!=nil{return err}
	err=png.Encode(f,img)
	err2:=f.Close()
	if err!=nil{return err}
	return err2
}

func generate(which,dir string) error {
	var a,b int
	show:=true
	switch which {
	case "right":a,b=10,148
	case "left":a,b=148,10
	case "still":a,b=74,74
	case "occluded":a,b=74,74;show=false
	default:return errors.New("unsupported fixture")
	}
	if err:=os.MkdirAll(dir,0700);err!=nil{return err}
	if err:=genFrame(dir,1,a,true);err!=nil{return err}
	return genFrame(dir,2,b,show)
}

func fileSHA(p string) string {
	contents,err:=os.ReadFile(p)
	if err!=nil{return ""}
	h:=sha256.Sum256(contents)
	return hex.EncodeToString(h[:])
}

func main() {
	which:=flag.String("make","","original generated fixture: left,right,still,occluded")
	out:=flag.String("out","","output directory for source-only PNG")
	first:=flag.String("first","","actual decoded first PNG")
	second:=flag.String("second","","actual decoded second PNG")
	expected:=flag.String("expect","","LEFT,RIGHT,STILL or UNKNOWN")
	flag.Parse()
	if *which!="" {
		if *out=="" {fmt.Fprintln(os.Stderr,"R065_HOLD missing fixture directory");os.Exit(12)}
		if err:=generate(*which,*out);err!=nil {fmt.Fprintln(os.Stderr,"R065_HOLD",err);os.Exit(12)}
		fmt.Println("R065_CREATED_ORIGINAL_SOURCE_ONLY",*which)
		return
	}
	if *first==""||*second==""||*expected=="" {
		fmt.Fprintln(os.Stderr,"R065_HOLD missing decoded frames or expected state")
		os.Exit(12)
	}
	r:=Receipt{Schema:"scp.r065.decoded-direction.v1",Status:"UNKNOWN",
		Decision:"UNKNOWN",Expected:*expected,
		SourceSHA:os.Getenv("GITHUB_SHA"),
		FirstFrameSHA:fileSHA(*first),SecondFrameSHA:fileSHA(*second),
		Scope:"ORIGINAL_RED_SQUARE_ONLY_NOT_HUMAN_MOTION"}
	p,err1:=marker(*first)
	q,err2:=marker(*second)
	var err error
	if err1!=nil {err=err1} else if err2!=nil{err=err2} else {
		r.FirstCount=p.Pixels
		r.SecondCount=q.Pixels
		r.Decision,r.DeltaPixels,err=classify(p,q)
	}
	switch {
	case err!=nil:
		r.Reason=err.Error()
	case r.Decision==*expected:
		r.Status="PASS_NARROW_SOURCE_ONLY"
	default:
		r.Status="FAIL_WRONG_DIRECTION"
		r.Reason="DIRECTION_MISMATCH"
	}
	data,_:=json.Marshal(r)
	fmt.Println(string(data))
	if r.Status!="PASS_NARROW_SOURCE_ONLY" {os.Exit(12)}
}
