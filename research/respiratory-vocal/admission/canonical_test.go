package admission
import("strings";"testing")
func TestCanonicalFieldAliasesFailClosed(t *testing.T){
 good:=string(healthy())
 cases:=[]struct{name,text string}{
  {"root uppercase",strings.Replace(good,\`"schema":\`,\`"Schema":\`,1)},
  {"root mixed",strings.Replace(good,\`"classification":\`,\`"Classification":\`,1)},
  {"root semantic overwrite",strings.Replace(good,\`"schema":\`,\`"SCHEMA":"unknown","schema":\`,1)},
  {"frame uppercase",strings.Replace(good,\`"phase":\`,\`"Phase":\`,1)},
  {"frame semantic overwrite",strings.Replace(good,\`"phase":\`,\`"PHASE":"inspiration","phase":\`,1)},
  {"nested source uppercase",strings.Replace(good,\`"kind":\`,\`"Kind":\`,1)},
  {"nested source semantic overwrite",strings.Replace(good,\`"kind":\`,\`"KIND":"glottal_voiced","kind":\`,1)},
  {"unknown nested",strings.Replace(good,\`"kind":\`,\`"unknown_reference":"private","kind":\`,1)},
 }
 for _,tc:=range cases{
  if tc.text==good{t.Fatalf("negative control %s did not change fixture",tc.name)}
  // All cases may be syntactically unambiguous to a plain parser, but must
  // never be silently mapped to a canonical physical state.
  if _,e:=Decode([]byte(tc.text));e==nil{t.Fatalf("%s was accepted",tc.name)}
 }
 if _,e:=Decode(healthy());e!=nil{t.Fatalf("canonical generated fixture refused: %v",e)}
}
