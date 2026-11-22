// Package offlinecontrol bridges a prepared Audio Foundry scene to its
// existing FFmpeg renderer. It is an experimental *offline* effect adapter,
// NOT an audio device, durable idempotency service, or production controller.
package offlinecontrol

import (
 "errors"
 "fmt"
 "os"
 "path/filepath"
 "reflect"

 "example.invalid/audio-foundry-fixture/scene"
)

var ErrUnsafeOutput = errors.New("offlinecontrol: unsafe output path")
var ErrInputChanged = errors.New("offlinecontrol: source plan/asset changed since preparation")
var ErrOutputExists = errors.New("offlinecontrol: output already exists; do not replay effect")

// Prepared is immutable outside this package, with the original scene custody
// receipt pinned before any FFmpeg effect is admitted.
type Prepared struct {
 manifest scene.Manifest
 assetRoot string
 outputPath string
 source scene.Receipt
}
func Prepare(m scene.Manifest, root, output string)(*Prepared,error){
 if output==""||filepath.Clean(output)!=output||!filepath.IsAbs(output)||filepath.Ext(output)!=".wav" {
  return nil,ErrUnsafeOutput
 }
 if stat,err:=os.Lstat(output);err==nil||stat!=nil{
  return nil,ErrOutputExists
 }else if !os.IsNotExist(err){return nil,err}
 dir:=filepath.Dir(output)
 realDir,err:=filepath.EvalSymlinks(dir)
 if err!=nil{return nil,err}
 if realDir!=dir{return nil,ErrUnsafeOutput}
 if st,err:=os.Stat(realDir);err!=nil||!st.IsDir(){return nil,ErrUnsafeOutput}
 receipt,err:=m.Plan(root,false) // Reuse native source hash/path/privacy checks.
 if err!=nil{return nil,err}
 realRoot,err:=filepath.EvalSymlinks(root)
 if err!=nil{return nil,err}
 return &Prepared{manifest:m,assetRoot:realRoot,outputPath:output,source:receipt},nil
}
func (p *Prepared) Fingerprint()string{
 if p==nil{return ""}
 return p.source.ManifestSHA256
}
func (p *Prepared) Execute()(scene.Receipt,error){
 if p==nil{return scene.Receipt{},errors.New("offlinecontrol: missing prepared plan")}
 // Re-validate the same immutable asset set immediately before the effect.
 now,err:=p.manifest.Plan(p.assetRoot,false)
 if err!=nil{return scene.Receipt{},err}
 if !reflect.DeepEqual(now,p.source){return scene.Receipt{},ErrInputChanged}
 if _,err:=os.Lstat(p.outputPath);err==nil{return scene.Receipt{},ErrOutputExists
 }else if !os.IsNotExist(err){return scene.Receipt{},err}
 r,err:=p.manifest.Render(p.assetRoot,p.outputPath,false)
 if err!=nil{return r,err}
 if r.OutputSHA256==""||r.OutputBytes==0 {return r,errors.New("offlinecontrol: renderer did not return verified output")}
 return r,nil
}
func VerifyOutput(path,digest string)(bool,error){
 if len(digest)!=64||path==""{return false,errors.New("offlinecontrol: invalid digest/path")}
 got,_,err:=scene.Hash(path);if err!=nil{return false,err}
 if got!=digest{return false,fmt.Errorf("offlinecontrol: output digest mismatch")}
 return true,nil
}
