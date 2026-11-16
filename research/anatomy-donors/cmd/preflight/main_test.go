package main
import "testing"
func TestSourceManifest(t *testing.T){if e:=validateSources(sources);e!=nil{t.Fatal(e)}}
func TestRejectDuplicate(t *testing.T){xs:=append([]Source{},sources...);xs=append(xs,sources[0]);if validateSources(xs)==nil{t.Fatal("duplicate accepted")}}
func TestRejectPathTraversal(t *testing.T){xs:=[]Source{{Repo:"ok/../bad",Branch:"main",Readme:"README",License:"LICENSE"}};if validateSources(xs)==nil{t.Fatal("path traversal accepted")}}
func TestRejectEmpty(t *testing.T){if validateSources(nil)==nil{t.Fatal("empty accepted")}}

func TestGitRefsIgnoreUnrelatedMirror(t *testing.T){
 exact:="5156bf1d6bda91b0a8b4a4812e4e71919fcab3d1"
 mirror:="bd0128e658bd24206dde0a2ca98655aac832689c"
 refs:=exact+"\trefs/heads/master\n"+mirror+"\trefs/original/refs/heads/master\n"
 got,err:=parseGitRefs(refs,"master")
 if err!=nil||got!=exact{t.Fatalf("exact branch not retained: %q %v",got,err)}
 if _,err:=parseGitRefs(mirror+"\trefs/original/refs/heads/master","master");err==nil{t.Fatal("mirror incorrectly accepted")}
 if _,err:=parseGitRefs(refs+exact+"\trefs/heads/master\n","master");err==nil{t.Fatal("duplicate exact branch accepted")}
}
