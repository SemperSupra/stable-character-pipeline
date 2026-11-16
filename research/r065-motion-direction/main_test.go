package main

import (
	"path/filepath"
	"strings"
	"testing"
)

func TestOriginalDirectionAndStationary(t *testing.T) {
	for _,item:=range []struct{input,want string}{
		{"right","RIGHT"},{"left","LEFT"},{"still","STILL"},
	} {
		t.Run(item.input,func(t *testing.T){
			dir:=t.TempDir()
			if err:=generate(item.input,dir);err!=nil{t.Fatal(err)}
			first,err:=marker(filepath.Join(dir,"frame_001.png"));if err!=nil{t.Fatal(err)}
			second,err:=marker(filepath.Join(dir,"frame_002.png"));if err!=nil{t.Fatal(err)}
			found,_,err:=classify(first,second)
			if err!=nil||found!=item.want{t.Fatalf("want %s got %s, err %v",item.want,found,err)}
		})
	}
}
func TestAdversarialOcclusionIsNotPass(t *testing.T) {
	dir:=t.TempDir()
	if err:=generate("occluded",dir);err!=nil{t.Fatal(err)}
	if _,err:=marker(filepath.Join(dir,"frame_001.png"));err!=nil{t.Fatal(err)}
	if _,err:=marker(filepath.Join(dir,"frame_002.png"));err==nil||
		!strings.Contains(err.Error(),"NO_RED_SUBJECT"){t.Fatalf("hidden subject false-pass: %v",err)}
}
func TestDirectionalReverseAndNumericalRejects(t *testing.T) {
	a:=Point{X:20,Pixels:3600,Width:224,Height:224}
	b:=Point{X:160,Pixels:3600,Width:224,Height:224}
	right,dx,err:=classify(a,b)
	left,dxBack,errBack:=classify(b,a)
	if err!=nil||errBack!=nil||right!="RIGHT"||left!="LEFT"||dx<=0||dxBack>=0{
		t.Fatalf("reversal oracle failed: %s/%s %.3f/%.3f %v %v",right,left,dx,dxBack,err,errBack)
	}
	_,_,err=classify(a,Point{X:160,Pixels:15,Width:224,Height:224})
	if err==nil {t.Fatal("missing marker false pass")}
	_,_,err=classify(a,Point{X:160,Pixels:3600,Width:225,Height:224})
	if err==nil {t.Fatal("dimension mismatch false pass")}
	_,_,err=classify(a,Point{X:160,Pixels:1000,Width:224,Height:224})
	if err==nil {t.Fatal("area shrink false pass")}
}
