package scenejob

import (
 "context"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "os"
 "os/exec"
 "path/filepath"
 "regexp"
 "strings"
 "sync"
 "time"

 "github.com/sempersupra/stable-character-pipeline/scenecontract"
)
const JobID="w7a-forward-24"
const RequestSchema="scp.native-job-request.v1"
const ResultSchema="scp.native-job-result.v1"
var gitSHA=regexp.MustCompile("^[a-f0-9]{40}$")
var digest=regexp.MustCompile("^[a-f0-9]{64}$")
var cameras=[]string{"OriginalFront","OriginalOblique"}

type Request struct{
 Schema string `json:"schema"`
 JobID string `json:"job_id"`
 Revision string `json:"revision"`
 SourceClass string `json:"source_class"`
}
type Result struct{
 Schema string `json:"schema"`
 JobID string `json:"job_id"`
 Revision string `json:"revision"`
 Rights string `json:"rights"`
 SourceSHA string `json:"source_sha256"`
 GLBSHA string `json:"glb_sha256"`
 BlendSHA string `json:"blend_sha256"`
 Videos map[string]string `json:"video_sha256"`
 FPS int `json:"fps"`
 Frames int `json:"frames"`
 ActorIDs []string `json:"actor_ids"`
 Cameras []string `json:"cameras"`
 SourceClass string `json:"source_class"`
 ObservedVideo string `json:"observed_video"`
 HumanBehavior string `json:"human_behavior"`
 HumanAnatomy string `json:"human_anatomy"`
 Release string `json:"release"`
}
type Engine interface{
 Run(context.Context,string,string) error // trusted output dir, trusted source commit SHA
}
type DockerEngine struct{
 RepoRoot string
 Image string
}
func(e DockerEngine)Run(ctx context.Context,out,revision string)error{
 if e.Image!="scp-native-oci:r9"{return errors.New("IMAGE_NOT_ADMITTED")}
 repo,err:=filepath.Abs(e.RepoRoot);if err!=nil{return err}
 output,err:=filepath.Abs(out);if err!=nil{return err}
 if !gitSHA.MatchString(revision){return errors.New("INVALID_REVISION")}
 cmdCtx,cancel:=context.WithTimeout(ctx,5*time.Minute);defer cancel()
 args:=[]string{"run","--rm","--network=none","--read-only","--cap-drop=ALL",
  "--security-opt=no-new-privileges","--pids-limit=256","--memory=5g","--cpus=2",
  "--tmpfs","/tmp:rw,exec,size=768m",
  "--user",fmt.Sprintf("%d:%d",os.Getuid(),os.Getgid()),
  "-e","HOME=/tmp","-e","XDG_CONFIG_HOME=/tmp/config","-e","XDG_CACHE_HOME=/tmp/cache",
  "-e","LIBGL_ALWAYS_SOFTWARE=1","-e","OMP_NUM_THREADS=2",
  "-v",repo+":/src:ro","-v",output+":/out:rw","--workdir","/src",
  "--entrypoint","python",e.Image,
  "qualification/render_job/native.py","--out","/out","--revision",revision}
 cmd:=exec.CommandContext(cmdCtx,"docker",args...)
 raw,err:=cmd.CombinedOutput()
 if err!=nil{return fmt.Errorf("NATIVE_JOB_FAILED: %s; process=%v",limitedError(raw),err)}
 return nil
}
func limitedError(b []byte)string{
 if len(b)>512 {b=b[len(b)-512:]}
 s:=strings.ReplaceAll(string(b),"\n"," ")
 return s
}
func Admit(r Request,expected string)error{
 if r.Schema!=RequestSchema||r.JobID!=JobID||r.SourceClass!="public-synthetic"{
  return errors.New("UNAUTHORIZED_JOB_CONTRACT")
 }
 if !gitSHA.MatchString(r.Revision)||r.Revision!=expected{return errors.New("SOURCE_REVISION_MISMATCH")}
 return nil
}
func Expected(revision string)Request{
 return Request{Schema:RequestSchema,JobID:JobID,Revision:revision,SourceClass:"public-synthetic"}
}
func regularDigest(path string, maxBytes int64)(string,error){
 info,err:=os.Lstat(path)
 if err!=nil{return "",err}
 if !info.Mode().IsRegular()||info.Size()>maxBytes{return "",errors.New("NOT_BOUNDED_REGULAR_FILE")}
 f,err:=os.Open(path);if err!=nil{return "",err};defer f.Close()
 h:=sha256.New()
 n,err:=io.Copy(h,io.LimitReader(f,maxBytes+1))
 if err!=nil||n>maxBytes{return "",errors.New("ORIGINAL_BYTES_READ_LIMIT")}
 return hex.EncodeToString(h.Sum(nil)),nil
}
func readResult(dir,revision string)(Result,error){
 var r Result
 path:=filepath.Join(dir,"result.json")
 info,err:=os.Lstat(path)
 if err!=nil||!info.Mode().IsRegular()||info.Size()>1<<20{return r,errors.New("JOB_RESULT_ABSENT_OR_UNSAFE")}
 f,err:=os.Open(path);if err!=nil{return r,err};defer f.Close()
 dec:=json.NewDecoder(io.LimitReader(f,(1<<20)+1));dec.DisallowUnknownFields()
 if err:=dec.Decode(&r);err!=nil{return r,err}
 var trailing any
 if dec.Decode(&trailing)!=io.EOF{return r,errors.New("JOB_RESULT_TRAILING_JSON")}
 if r.Schema!=ResultSchema||r.JobID!=JobID||r.Revision!=revision||
  r.SourceClass!="public-synthetic"||r.Rights!="ORIGINAL_SELF_AUTHORED_SYNTHETIC"||
  r.FPS!=12||r.Frames!=24||len(r.ActorIDs)!=2||
  r.ActorIDs[0]!="CobaltOriginal"||r.ActorIDs[1]!="MarigoldOriginal"||
  len(r.Cameras)!=2||r.Cameras[0]!=cameras[0]||r.Cameras[1]!=cameras[1]||
  r.ObservedVideo!="PASS_ALL_REQUIRED_VIEWS_L1_ONLY"||
  r.HumanBehavior!="FAIL_ABSTRACT_LIMBS_ONLY"||
  r.HumanAnatomy!="UNKNOWN_NO_INDEPENDENT_JCS_OR_ROM"||
  r.Release!="HELD_R009_NOT_RUN_NOT_ADMITTED"{
  return r,errors.New("JOB_RECEIPT_CANNOT_PROMOTE_SCIENCE_OR_RIGHTS")
 }
 if len(r.Videos)!=2{return r,errors.New("JOB_CAMERAS_NOT_COMPLETE")}
 for _,field:=range []string{r.SourceSHA,r.GLBSHA,r.BlendSHA,r.Videos[cameras[0]],r.Videos[cameras[1]]}{
  if !digest.MatchString(field){return r,errors.New("JOB_DIGEST_INVALID")}
 }
 files:=map[string]string{
  "forward/source.json":r.SourceSHA,
  "forward/original_synthetic_24frame_skinned.glb":r.GLBSHA,
  "forward/original_source_grounded_24frame_native.blend":r.BlendSHA,
  "forward/rendered/OriginalFront.mp4":r.Videos[cameras[0]],
  "forward/rendered/OriginalOblique.mp4":r.Videos[cameras[1]],
 }
 for name,expected:=range files{
  actual,err:=regularDigest(filepath.Join(dir,name),512<<20)
  if err!=nil||actual!=expected{return r,fmt.Errorf("ORIGINAL_ARTIFACT_DIGEST_MISMATCH: %s",name)}
 }
 scene:=scenecontract.Scene{
  Schema:scenecontract.Schema,Revision:revision,Action:"walk_approach",FPS:12,Frames:24,
  Actors:[]scenecontract.Actor{
   {ID:r.ActorIDs[0],AssetDigest:"sha256:"+r.GLBSHA,SourceClass:"public-synthetic"},
   {ID:r.ActorIDs[1],AssetDigest:"sha256:"+r.GLBSHA,SourceClass:"public-synthetic"}},
  Cameras:r.Cameras,
 }
 if scenecontract.Validate(scene).Status!="PASS"{return r,errors.New("CANONICAL_SCENE_CONTRACT_REJECTED")}
 return r,nil
}
type Manager struct{
 mu sync.Mutex
 revision string
 root string
 engine Engine
 completed *Result
 completeDir string
}
func NewManager(revision,outputRoot string,engine Engine)(*Manager,error){
 if !gitSHA.MatchString(revision){return nil,errors.New("SOURCE_SHA_INVALID")}
 if engine==nil{return nil,errors.New("ENGINE_REQUIRED")}
 p,err:=filepath.Abs(outputRoot);if err!=nil{return nil,err}
 if err:=os.MkdirAll(p,0700);err!=nil{return nil,err}
 stat,err:=os.Lstat(p)
 if err!=nil||!stat.IsDir()||stat.Mode()&os.ModeSymlink!=0{return nil,errors.New("OUTPUT_ROOT_INVALID")}
 return &Manager{revision:revision,root:p,engine:engine},nil
}
func(m *Manager)Run(ctx context.Context,r Request)(Result,error){
 var zero Result
 if err:=Admit(r,m.revision);err!=nil{return zero,err}
 m.mu.Lock();defer m.mu.Unlock()
 if m.completed!=nil{
  verified,err:=readResult(m.completeDir,m.revision)
  if err!=nil{return zero,err}
  return verified,nil
 }
 var path string
 for i:=1;i<=1000;i++{
  path=filepath.Join(m.root,fmt.Sprintf("attempt-%04d",i))
  err:=os.Mkdir(path,0700)
  if os.IsExist(err){continue}
  if err!=nil{return zero,err}
  break
 }
 if _,err:=os.Stat(path);err!=nil{return zero,errors.New("OUTPUT_ATTEMPT_LIMIT")}
 if err:=m.engine.Run(ctx,path,m.revision);err!=nil{
  return zero,err // NEVER delete failed attempt or first failed media
 }
 result,err:=readResult(path,m.revision)
 if err!=nil{return zero,err}
 m.completed=&result;m.completeDir=path
 return result,nil
}
func(m *Manager)Result()(Result,bool,error){
 m.mu.Lock();defer m.mu.Unlock()
 if m.completed==nil{return Result{},false,nil}
 r,err:=readResult(m.completeDir,m.revision)
 return r,true,err
}
func(m *Manager)MediaPath(camera string)(string,error){
 m.mu.Lock();defer m.mu.Unlock()
 if m.completed==nil{return "",errors.New("JOB_NOT_COMPLETE")}
 if camera!=cameras[0]&&camera!=cameras[1]{return "",errors.New("UNAUTHORIZED_CAMERA")}
 if _,err:=readResult(m.completeDir,m.revision);err!=nil{return "",err}
 return filepath.Join(m.completeDir,"forward","rendered",camera+".mp4"),nil
}
