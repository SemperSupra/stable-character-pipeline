package catalog
import ("os";"strings";"testing")
func TestCatalog(t *testing.T) {
 b,err:=os.ReadFile("catalog.json");if err!=nil{t.Fatal(err)}
 cat,err:=Validate(b);if err!=nil{t.Fatal(err)}
 if len(cat.Entries)<8{t.Fatalf("too few entries: %d",len(cat.Entries))}
}
func TestRightsGate(t *testing.T) {
 b,err:=os.ReadFile("catalog.json");if err!=nil{t.Fatal(err)}
 s:=strings.Replace(string(b),`"publication": "METADATA_ONLY"`,`"publication": "THIRD_PARTY_ARTIFACT"`,1)
 if _,err:=Validate([]byte(s));err==nil{t.Fatal("unlicensed redistribution accepted")}
 s=strings.Replace(string(b),`"mmd-blender.mmd-tools.v4.5.14"`,`"scp.synthetic-triangle.v1"`,1)
 if _,err:=Validate([]byte(s));err==nil{t.Fatal("duplicate ID accepted")}
 s=strings.Replace(string(b),"https://github.com/MMD-Blender","file:///etc/MMD-Blender",1)
 if _,err:=Validate([]byte(s));err==nil{t.Fatal("invalid source accepted")}
}
