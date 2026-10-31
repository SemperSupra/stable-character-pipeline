package main
import(
 "os"
 "path/filepath"
 "testing"
)
func TestNoOverwrite(t *testing.T){
 dest:=filepath.Join(t.TempDir(),"witness")
 if e:=run([]string{"-out",dest});e!=nil{t.Fatal(e)}
 if _,e:=os.Stat(filepath.Join(dest,"receipt.json"));e!=nil{t.Fatal("missing immutable receipt")}
 if e:=run([]string{"-out",dest});e==nil{t.Fatal("existing evidence overwritten")}
 if e:=run([]string{});e==nil{t.Fatal("missing args admitted")}
}
