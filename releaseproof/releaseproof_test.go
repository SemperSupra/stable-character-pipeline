package releaseproof
import(
 "bytes"
 "crypto/ed25519"
 "crypto/sha256"
 "encoding/base64"
 "encoding/hex"
 "encoding/json"
 "os"
 "path/filepath"
 "strings"
 "testing"
 "github.com/sempersupra/stable-character-pipeline/releasegate"
)
func fixture(t *testing.T)(releasegate.Manifest,TrustPolicy,string,string){
 t.Helper();base:=t.TempDir();pdir:=filepath.Join(base,"proofs");edir:=filepath.Join(base,"evidence")
 if err:=os.MkdirAll(pdir,0700);err!=nil{t.Fatal(err)}
 if err:=os.MkdirAll(edir,0700);err!=nil{t.Fatal(err)}
 m:=releasegate.Manifest{Schema:releasegate.Schema,Phase:"candidate",Scope:"public-synthetic",SourceSHA:strings.Repeat("a",40),
    ImageDigest:"sha256:"+strings.Repeat("b",64),Gates:map[string]releasegate.Evidence{}}
 policy:=TrustPolicy{Schema:PolicySchema,Assignments:map[string]string{},Keys:map[string]string{}}
 for _,gate:=range releasegate.RequiredGates{
  issuer:="qa_"+gate
  seed:=sha256.Sum256([]byte("synthetic-only-test-key-NEVER-PRODUCTION:"+gate))
  private:=ed25519.NewKeyFromSeed(seed[:])
  policy.Keys[issuer]=hex.EncodeToString(private.Public().(ed25519.PublicKey))
  policy.Assignments[gate]=issuer
  content:=[]byte("original synthetic evidence for "+gate+"\n")
  if err:=os.WriteFile(filepath.Join(edir,gate+".bin"),content,0600);err!=nil{t.Fatal(err)}
  proof:=Proof{Schema:Schema,Gate:gate,SourceSHA:m.SourceSHA,ImageDigest:m.ImageDigest,Scope:m.Scope,
    EvidenceSHA:Digest(content),Issuer:issuer}
  proof.Signature=base64.StdEncoding.EncodeToString(ed25519.Sign(private,Payload(proof)))
  raw,err:=json.Marshal(proof);if err!=nil{t.Fatal(err)}
  if err:=os.WriteFile(filepath.Join(pdir,gate+".json"),raw,0600);err!=nil{t.Fatal(err)}
  m.Gates[gate]=releasegate.Evidence{Status:"PASS",ReceiptSHA:Digest(raw)}
 }
 return m,policy,pdir,edir
}
func TestPositiveSignedExactByteEvidence(t *testing.T){
 m,p,d,e:=fixture(t)
 if v:=Verify(m,p,d,e);v.Status!="PASS"{t.Fatalf("%+v",v)}
}
func TestNoUnsignedManifestFalsePass(t *testing.T){
 m,p,d,e:=fixture(t)
 if v:=releasegate.Validate(m);v.Status!="PASS"{t.Fatal(v)}
 p.Keys["qa_behavior"]=strings.Repeat("a",64)
 if v:=Verify(m,p,d,e);v.Code!="ISSUER_SIGNATURE_INVALID_BEHAVIOR"{t.Fatal(v)}
}
func TestProofTamperAndEvidenceSwap(t *testing.T){
 for _,which:=range []string{"proof","evidence","missing"}{t.Run(which,func(t *testing.T){
  m,p,d,e:=fixture(t)
  path:=filepath.Join(d,"behavior.json")
  if which=="evidence"{path=filepath.Join(e,"behavior.bin")}
  if which=="missing"{_ = os.Remove(path)}else{_ = os.WriteFile(path,[]byte("wrong"),0600)}
  v:=Verify(m,p,d,e)
  if v.Status!="FAIL"{t.Fatal(v)}
 })}
}
func TestIndependenceAndSourceDrift(t *testing.T){
 m,p,d,e:=fixture(t)
 p.Assignments["behavior"]=p.Assignments["build"]
 if v:=Verify(m,p,d,e);v.Code!="INDEPENDENCE_VIOLATION"{t.Fatal(v)}
 m,p,d,e=fixture(t)
 m.SourceSHA=strings.Repeat("c",40)
 if v:=Verify(m,p,d,e);v.Code!="PROOF_BINDING_MISMATCH_BUILD"{t.Fatal(v)}
}
func TestDraftCannotPromote(t *testing.T){m,p,d,e:=fixture(t);m.Phase="draft";if v:=Verify(m,p,d,e);v.Status!="UNKNOWN"{t.Fatal(v)}}
func TestMalformedAndDuplicateStrictJSON(t *testing.T){
 raws:=[]string{
  `{"schema":"scp.release-proof.v1","schema":"hijack"}`,
  `{"unknown":true}`,
  `{"gate":"build"}{"gate":"render"}`,
  strings.Repeat(" ",MaximumJSON+1),
 }
 for i,s:=range raws{var proof Proof;if err:=DecodeStrict(bytes.NewBufferString(s),&proof);err==nil{t.Fatalf("bad %d accepted",i)}}
}
func TestSymlinkEvidenceRejected(t *testing.T){
 m,p,d,e:=fixture(t)
 bad:=filepath.Join(e,"behavior.bin")
 real:=bad+".real"
 if err:=os.Rename(bad,real);err!=nil{t.Fatal(err)}
 if err:=os.Symlink(real,bad);err!=nil{t.Fatal(err)}
 if v:=Verify(m,p,d,e);v.Code!="EVIDENCE_UNAVAILABLE_BEHAVIOR"{t.Fatal(v)}
}

func TestUndeclaredGateCannotLaunderUnsignedClaim(t *testing.T){
 m,p,d,e:=fixture(t)
 m.Gates["unreviewed_quality"]=releasegate.Evidence{Status:"PASS",ReceiptSHA:"sha256:"+strings.Repeat("d",64)}
 if v:=releasegate.Validate(m);v.Status!="PASS"{t.Fatalf("raw R0 behavior changed: %+v",v)}
 if v:=Verify(m,p,d,e);v.Code!="UNDECLARED_GATE"{t.Fatalf("unsigned extra gate accepted: %+v",v)}
}
