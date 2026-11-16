package main
import (
 "archive/zip"
 "bytes"
 "os"
 "path/filepath"
 "strings"
 "testing"
)
func sampleObj()string{return "v 0 0 0\nv 1 0 0\nv 0 1 0\nv 0 0 1\nf 1 2 3\nf 1 2 4\n"}
func TestRealOBJParserAndBadIndex(t *testing.T){
 v,f,b,h,e:=parseOBJ(strings.NewReader(sampleObj()),2048)
 if e!=nil||v!=4||f!=2||len(h)!=64||b[5]!=1{t.Fatalf("%v %d %d %+v",e,v,f,b)}
 for _,s:=range []string{
 "v 0 0 0\nv 1 0 0\nv 0 1 0\nv 0 0 1\nf 1 2 10\nf 1 2 4\n",
 "v 0 0 nan\nv 1 0 0\nv 0 1 0\nv 0 0 1\nf 1 2 3\nf 1 2 4\n",
 }{if _,_,_,_,e:=parseOBJ(strings.NewReader(s),2048);e==nil{t.Fatal("bad OBJ accepted")}}
 if _,_,_,_,e:=parseOBJ(strings.NewReader(sampleObj()),2);e==nil{t.Fatal("byte cap ignored")}
}
func writeArchive(t *testing.T,dir string,members map[string]string)string{
 t.Helper();dest:=filepath.Join(dir,"partof_BP3D_4.0_obj_99.zip")
 buf:=new(bytes.Buffer);zw:=zip.NewWriter(buf)
 for n,txt:=range members{w,e:=zw.Create(n);if e!=nil{t.Fatal(e)};_,e=w.Write([]byte(txt));if e!=nil{t.Fatal(e)}}
 if e:=zw.Close();e!=nil{t.Fatal(e)}
 if e:=os.WriteFile(dest,buf.Bytes(),0600);e!=nil{t.Fatal(e)}
 return dest
}
func TestElementsHeaderAndConceptEdges(t *testing.T){
 d:=t.TempDir();file:=filepath.Join(d,"partof_element_parts.txt")
 s:="concept id\tname\telement file id\nFMA7310\tleft lung\tFJ2\nFMA7310\tleft lung\tFJ1\nFMA7309\tright lung\tFJ3M\n"
 if e:=os.WriteFile(file,[]byte(s),0600);e!=nil{t.Fatal(e)}
 x,rows,unique,e:=readElements(file)
 if e!=nil||rows!=3||unique!=3||len(x["FMA7310"])!=2||x["FMA7310"][0].ID!="FJ1"{t.Fatalf("%v %d %d %+v",e,rows,unique,x)}
 if e:=os.WriteFile(file,[]byte(s+"FMA7310\tleft lung\tFJ1\n"),0600);e!=nil{t.Fatal(e)}
 if _,_,_,e=readElements(file);e==nil{t.Fatal("duplicate source edge accepted")}
}
func TestRejectZipPathTraversalWithoutExtracting(t *testing.T){
 d:=t.TempDir();table:=filepath.Join(d,"partof_element_parts.txt")
 os.WriteFile(table,[]byte("concept id\tname\telement file id\nFMA7310\tleft lung\tFJ1\n"),0600)
 dest:=writeArchive(t,d,map[string]string{"../FJ1.obj":sampleObj()})
 // Tiny synthetic ZIP must fail preflight before unsafe-mesh processing.
 if _,e:=inspect(table,dest);e==nil{t.Fatal("small unadmitted archive accepted")}
}
