package admission

import(
 "encoding/json"
 "errors"
 "fmt"
 "reflect"
 "strings"

 "github.com/SemperSupra/stable-character-pipeline/research/respiratory-vocal/behavior"
)

// checkCanonicalFields rejects case-insensitive JSON aliases, including
// "Schema" vs "schema" and "Kind" vs "kind", which encoding/json would
// otherwise map to the same struct field. Use declared versioned JSON tags as
// the exact wire spelling; don't silently normalize unknown field names.
func checkCanonicalFields(data []byte)error{
 return checkShape(json.RawMessage(data),reflect.TypeOf(behavior.Performance{}),0)
}
func checkShape(raw json.RawMessage, typ reflect.Type, depth int)error{
 if depth>MaxDepth{return errors.New("noncanonical JSON nesting")}
 for typ.Kind()==reflect.Pointer{typ=typ.Elem()}
 if len(raw)==0||string(raw)=="null"{return nil}
 switch typ.Kind(){
 case reflect.Struct:
  var obj map[string]json.RawMessage
  if e:=json.Unmarshal(raw,&obj);e!=nil{return fmt.Errorf("invalid typed JSON object: %w",e)}
  if obj==nil{return errors.New("expected object")}
  fields:=make(map[string]reflect.Type,typ.NumField())
  for i:=0;i<typ.NumField();i++{
   f:=typ.Field(i)
   if f.PkgPath!=""{continue}
   name:=strings.Split(f.Tag.Get("json"),",")[0]
   if name=="-"{continue};if name==""{name=f.Name}
   fields[name]=f.Type
  }
  for name,child:=range obj{
   ft,ok:=fields[name]
   if !ok{return fmt.Errorf("noncanonical/unknown JSON field %q (exact field spelling required)",name)}
   if e:=checkShape(child,ft,depth+1);e!=nil{return fmt.Errorf("%s: %w",name,e)}
  }
 case reflect.Slice,reflect.Array:
  var arr []json.RawMessage
  if e:=json.Unmarshal(raw,&arr);e!=nil{return fmt.Errorf("invalid typed JSON array: %w",e)}
  if arr==nil{return errors.New("expected array")}
  if len(arr)>MaxItemsPerContainer{return errors.New("typed JSON array exceeds bound")}
  for i,child:=range arr{
   if e:=checkShape(child,typ.Elem(),depth+1);e!=nil{return fmt.Errorf("[%d]: %w",i,e)}
  }
 }
 return nil
}
