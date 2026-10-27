// Package g10bridge binds ACTUAL, immutable public G10a/b/c/d receipts and source
// bytes into W02 evidence. It does not solve IK, establish person identity or
// assert ground-contact physics or an MMD-native CCD reference.
package g10bridge

import (
    "bytes"
    "encoding/json"
    "errors"
    "fmt"
    "math"
    "os"
    "path/filepath"
    "strconv"

    "github.com/SemperSupra/stable-character-pipeline/mmd/roadmap/envelope"
)

const (
    fixtureRun = "https://github.com/SemperSupra/stable-character-pipeline/actions/runs/40455687379"
    directRun = "https://github.com/SemperSupra/stable-character-pipeline/actions/runs/40456000406"
    blenderRun = "https://github.com/SemperSupra/stable-character-pipeline/actions/runs/40456662219"
    parityRun = "https://github.com/SemperSupra/stable-character-pipeline/actions/runs/40456784554"
)
type Paths struct {
    Model, Motion, FixtureReceipt, IKGLB, NoIKGLB, DirectReceipt, BlenderReceipt, ParityReceipt string
}
type fixture struct {
    Schema string `json:"schema"`
    Status string `json:"status"`
    BoneNames []string `json:"bone_names"`
    SourceGoalFrames []int `json:"source_goal_frames"`
    Hashes map[string]string `json:"hashes"`
    Rights string `json:"rights"`
}
type sample struct { Error float64 `json:"error"` }
type direct struct {
    Schema string `json:"schema"`
    Status string `json:"status"`
    GatePass bool `json:"gate_pass"`
    IKEnabled map[string]sample `json:"ik_enabled"`
    IKDisabled map[string]sample `json:"ik_disabled"`
    SourceIKSHA string `json:"source_ik_glb_sha256"`
    SourceFKSHA string `json:"source_fk_glb_sha256"`
}
type blender struct {
    Schema string `json:"schema"`
    Status string `json:"status"`
    Blender string `json:"blender"`
    MMDTools string `json:"mmd_tools"`
    RealIKConstraintCount int `json:"real_ik_constraint_count"`
    Samples map[string]sample `json:"samples"`
}
type frame struct {
    BlenderError float64 `json:"blender_error"`
    IndependentError float64 `json:"independent_error"`
    AbsoluteErrorDelta float64 `json:"absolute_error_delta"`
    Passed bool `json:"passed"`
}
type parity struct {
    Schema string `json:"schema"`
    Status string `json:"status"`
    Passes bool `json:"passes"`
    Frames map[string]frame `json:"frames"`
    AcceptanceMaxError float64 `json:"acceptance_max_error"`
    AcceptanceMaxDelta float64 `json:"acceptance_max_delta"`
}
func read(path string,max int64)([]byte,error){
    st,err:=os.Lstat(path);if err!=nil{return nil,err}
    if !st.Mode().IsRegular() || st.Size()<1 || st.Size()>max{return nil,fmt.Errorf("not bounded regular input: %s",filepath.Base(path))}
    return os.ReadFile(path)
}
func load[T any](p string)(T,[]byte,error){
    var v T
    b,err:=read(p,2<<20);if err!=nil{return v,nil,err}
    // Upstream receipts can have additional fields not consumed here; reject
    // duplicate keys, but do not discard legitimate unrelated source metadata.
    if err:=envelope.RejectDuplicateJSONKeys(b);err!=nil{return v,nil,fmt.Errorf("ambiguous source receipt %s: %w",filepath.Base(p),err)}
    if err=json.Unmarshal(b,&v);err!=nil{return v,nil,err}
    return v,b,nil
}
func near(x,y float64)bool{
    return !math.IsNaN(x)&&!math.IsInf(x,0)&&!math.IsNaN(y)&&!math.IsInf(y,0)&&math.Abs(x-y)<1e-8
}
func Build(paths Paths)(envelope.ProofBundle,error){
    var empty envelope.ProofBundle
    mb,err:=read(paths.Model,20<<20);if err!=nil{return empty,fmt.Errorf("PMX %w",err)}
    vb,err:=read(paths.Motion,20<<20);if err!=nil{return empty,fmt.Errorf("VMD %w",err)}
    if !bytes.HasPrefix(mb,[]byte("PMX ")) || !bytes.HasPrefix(vb,[]byte("Vocaloid Motion Data")) ||
       len(mb)<64 || len(vb)<64 {return empty,errors.New("native source format magic or size invalid")}
    pmxHash,vmdHash:=envelope.ContentDigest(mb),envelope.ContentDigest(vb)
    f,fb,err:=load[fixture](paths.FixtureReceipt);if err!=nil{return empty,err}
    if f.Schema!="scp.mmd.ik.fixture.v1"||f.Status!="PASS_ORIGINAL_TWO_LINK_IK_PMX_AND_SOURCE_VMD"||
      len(f.BoneNames)!=4||f.BoneNames[0]!="腰"||f.BoneNames[1]!="ひざ"||
      f.BoneNames[2]!="足首"||f.BoneNames[3]!="足ＩＫ"||
      len(f.SourceGoalFrames)!=2||f.SourceGoalFrames[0]!=0||f.SourceGoalFrames[1]!=30||
      f.Hashes["synthetic_two_link_ik.pmx"]!=pmxHash||
      f.Hashes["synthetic_foot_goal.vmd"]!=vmdHash||
      f.Rights!="synthetic self-authored IK rig, no third-party dancers or scans" {
        return empty,errors.New("source receipts, native Japanese bones, byte hashes or original rights mismatch")
    }
    ib,err:=read(paths.IKGLB,20<<20);if err!=nil{return empty,err}
    nb,err:=read(paths.NoIKGLB,20<<20);if err!=nil{return empty,err}
    if !bytes.HasPrefix(ib,[]byte("glTF")) || !bytes.HasPrefix(nb,[]byte("glTF")) ||
       len(ib)<20 || len(nb)<20 {return empty,errors.New("actual IK/FK GLB magic or size invalid")}
    d,db,err:=load[direct](paths.DirectReceipt);if err!=nil{return empty,err}
    b,bb,err:=load[blender](paths.BlenderReceipt);if err!=nil{return empty,err}
    p,pb,err:=load[parity](paths.ParityReceipt);if err!=nil{return empty,err}
    if d.Schema!="scp.mmd.ik.contact.v1"||d.Status!="PASS_IK_TARGET_TRACKING"||!d.GatePass||
       d.SourceIKSHA!=envelope.ContentDigest(ib)||d.SourceFKSHA!=envelope.ContentDigest(nb)||
       b.Schema!="scp.mmd.ik.blender.v1"||b.Status!="PASS_REAL_BLENDER_MMD_IK_CONSTRAINT_AND_GOAL_MOTION"||
       b.RealIKConstraintCount<1||b.Blender==""||b.MMDTools==""||
       p.Schema!="scp.mmd.ik.two-engine-contact.v1"||p.Status!="PASS_BLENDER_VS_DIRECT_IK_CONTACT_PARITY"||
       !p.Passes||!near(p.AcceptanceMaxError,.05)||!near(p.AcceptanceMaxDelta,.05) {
        return empty,errors.New("source-linked engine receipt versions, status, thresholds or GLB bytes mismatch")
    }
    f0:=0
    result:=envelope.ProofBundle{
        Schema:envelope.Schema,
        Fixture: envelope.FixtureSpec{
            ID:"g10a-original-source-ik",SourceURI:fixtureRun+"/artifacts/12711259553",
            SourceSHA256:pmxHash,FrameCount:31,
            Inputs:[]envelope.SourceInput{{
                Role:"motion",NativeFormat:"VMD",
                SourceURI:fixtureRun+"/artifacts/12711259553/synthetic_foot_goal.vmd",
                SourceSHA256:vmdHash,
                Rights:envelope.SourceRights{AssetRights:"ORIGINAL_SYNTHETIC",
                    EvidenceURI:"https://github.com/SemperSupra/stable-character-pipeline/blob/15eb289cd7079f8d789f5b19537827dfd635068b/mmd/qualification/ik_fixture.py",
                    CloudAllowed:true,RedistributeAllowed:true},
            }},
            Semantics:envelope.SourceSemantics{
                NativeFormat:"PMX",NativeBoneLabels:append([]string(nil),f.BoneNames...),
                NativeMorphLabels:[]string{},Units:"source_unit",MetersPerUnit:nil,
                Axes:"LH_Y_UP",FPSNumerator:30,FPSDenominator:1,FrameOrigin:&f0,
                Rights:envelope.SourceRights{AssetRights:"ORIGINAL_SYNTHETIC",
                  EvidenceURI:"https://github.com/SemperSupra/stable-character-pipeline/blob/15eb289cd7079f8d789f5b19537827dfd635068b/mmd/qualification/ik_fixture.py",
                  CloudAllowed:true,RedistributeAllowed:true},
            },
        },
        Observations:[]envelope.EngineObservation{},
        Metrics:[]envelope.MetricEvidence{},
        Verdict:"PASS",
    }
    // G10b direct-converter and G10c native Blender reports are independent
    // runtime sources; parity report is a third reference but not an
    // independent MMD engine. No literal values may stand in for measured data.
    for _,i:=range []int{0,15,30}{
        key:=strconv.Itoa(i)
        dv,okd:=d.IKEnabled[key];bv,okb:=b.Samples[key];pv,okp:=p.Frames[key]
        if !okd||!okb||!okp||!pv.Passed||!near(dv.Error,pv.IndependentError)||
           !near(bv.Error,pv.BlenderError)||!near(math.Abs(bv.Error-dv.Error),pv.AbsoluteErrorDelta)||
           dv.Error<0||bv.Error<0||dv.Error>=.05||bv.Error>=.05||
           math.Abs(bv.Error-dv.Error)>=.05 {
            return empty,fmt.Errorf("frame %d data, solver or parity witness mismatch",i)
        }
        if i>0 {
            off,ok:=d.IKDisabled[key]
            if !ok||!near(off.Error,off.Error)||off.Error<=0||dv.Error>=.5*off.Error {
                return empty,fmt.Errorf("frame %d genuine IK benefit not observed",i)
            }
        }
        for _,e:=range []struct{
            id,engine,version,uri,hash,metric string
            value float64
        }{
            {id:"blender-"+key,engine:"blender-mmd-tools",version:b.Blender+" mmd-tools "+b.MMDTools,
                uri:blenderRun+"/artifacts/12712981080/blender_ik_receipt.json",
                hash:envelope.ContentDigest(bb),metric:"ankle_to_ik_goal",value:bv.Error},
            {id:"direct-"+key,engine:"mmd2gltf",version:"b86ef4c2b103dd01130f68ede625d35633b9e5ff",
                uri:directRun+"/artifacts/12712169140/ik_contact_receipt.json",
                hash:envelope.ContentDigest(db),metric:"ankle_to_ik_goal",value:dv.Error},
        } {
            x:=e.value
            time:=float64(i)/30
            result.Observations=append(result.Observations,envelope.EngineObservation{
                ID:e.id,Engine:e.engine,EngineVersion:e.version,
                EvidenceURI:e.uri,EvidenceSHA256:e.hash,
                FixtureSHA256:pmxHash,Frame:i,TimeSeconds:&time,
                Status:"PASS",Measured:map[string]float64{e.metric:x},
                DeclaredLoss:[]string{"full-joint-curve-parity-NOT_TESTED",
                     "native-MMD-CCD-NOT_TESTED","foot-ground-physics-NOT_TESTED"},
            })
            result.Metrics=append(result.Metrics,envelope.MetricEvidence{
                ID:"goal-error-"+e.id,ObservationID:e.id,MeasuredKey:e.metric,
                Oracle:parityRun+"/artifacts/12712661688;parity_sha256="+envelope.ContentDigest(pb),
                Status:"PASS",Units:"source_unit",Value:&x,
            })
        }
    }
    if err:=envelope.Validate(result);err!=nil{return empty,fmt.Errorf("W02 typed envelope: %w",err)}
    _=fb // read and authenticated through source hashes & metadata, not version promotion
    _=vb // VMD original bytes are independently matched to the fixture's VMD hash
    return result,nil
}
