package main
import "testing"
func TestSourceManifest(t *testing.T){if e:=validateSources(sources);e!=nil{t.Fatal(e)}}
func TestRejectDuplicate(t *testing.T){xs:=append([]Source{},sources...);xs=append(xs,sources[0]);if validateSources(xs)==nil{t.Fatal("duplicate accepted")}}
func TestRejectPathTraversal(t *testing.T){xs:=[]Source{{Repo:"ok/../bad",Branch:"main",Readme:"README",License:"LICENSE"}};if validateSources(xs)==nil{t.Fatal("path traversal accepted")}}
func TestRejectEmpty(t *testing.T){if validateSources(nil)==nil{t.Fatal("empty accepted")}}
