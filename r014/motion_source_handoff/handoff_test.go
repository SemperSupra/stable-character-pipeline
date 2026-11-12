package handoff

import (
	"bytes"
	"encoding/json"
	"os"
	"strings"
	"testing"
)

const catalogFile = "existing_sources.catalog.v1.json"

func load(t *testing.T) Packet {
	t.Helper()
	p,b,e:=ReadPacket(catalogFile)
	if e!=nil||len(b)==0 {t.Fatalf("read catalog %v",e)}
	return p
}
func qualifies(t *testing.T,p Packet)Receipt{
	t.Helper()
	b,e:=json.Marshal(p);if e!=nil{t.Fatal(e)}
	r,e:=Evaluate(p,b);if e!=nil{t.Fatal(e)}
	return r
}
func mutatedReject(t *testing.T,change func(*Packet)){
	t.Helper()
	p:=load(t);change(&p);b,_:=json.Marshal(p)
	if _,e:=Evaluate(p,b);e==nil{t.Fatal("unsafe source passed")}
}

func TestKnownRealSourcesStayHeld(t *testing.T){
	p:=load(t)
	r:=qualifies(t,p)
	if r.Status!="HOLD_CINEMATIC_AND_ACTUAL_MOTION_SOURCE_ADMISSION"||r.R014ReleaseStatus!="HOLD"{
		t.Fatalf("synthetic/catalog erroneously promoted: %+v",r)}
	if len(r.SourceDispositions)!=4{t.Fatal("source count")}
	m:=map[string]Disposition{}
	for _,x:=range r.SourceDispositions{m[x.ID]=x}
	for _,name:=range []string{"cmu-07-01-catalog","aist-plusplus-catalog","dancedb-catalog"}{
		if m[name].Status!="HOLD_CATALOG_OR_UNVERIFIED_CAPTURE"||!m[name].RequiresPrivateCompute||len(m[name].AllowedRoles)!=0{
			t.Fatalf("source %s got illegal admission: %+v",name,m[name])
		}
	}
	if m["go-169-original"].Status!="PASS_ORIGINAL_PROCEDURAL_LINEAGE_ONLY"{
		t.Fatal("procedural source lineage mislabeled")
	}
	if len(m["go-169-original"].AllowedRoles)!=5{
		t.Fatal("procedural source never acquired accepted permissions")
	}
	if len(m["cmu-07-01-catalog"].RefusedRoles)!=7{
		t.Fatal("CMU toe/hand negative controls removed")
	}
}
func TestHashAndDeterminism(t *testing.T){
	p,b,e:=ReadPacket(catalogFile);if e!=nil{t.Fatal(e)}
	r,e:=Evaluate(p,b);if e!=nil{t.Fatal(e)}
	r2,e:=Evaluate(p,b);if e!=nil{t.Fatal(e)}
	if r.ManifestSHA256!=r2.ManifestSHA256||len(r.ManifestSHA256)!=64{t.Fatal("manifest changed")}
	if r.ManifestSHA256!=digest(b){t.Fatal("incorrect original catalog digest")}
}
func TestNoCompetingW07CanonicalIR(t *testing.T){
	mutatedReject(t,func(p *Packet){p.Sources[0].ParentSchema="scp.walk_motion.v1"})
}
func TestCMUToeNotObserved(t *testing.T){
	mutatedReject(t,func(p *Packet){p.Sources[0].ObservedJointChannels=[]string{"pelvis","left_toe"}})
}
func TestCMUContactNotObserved(t *testing.T){
	mutatedReject(t,func(p *Packet){p.Sources[0].ObservedContact=true})
}
func TestSourceRightsAndVenue(t *testing.T){
	mutatedReject(t,func(p *Packet){p.Sources[0].Venue="public_github_actions"})
}
func TestNoFabricatedGoDigest(t *testing.T){
	mutatedReject(t,func(p *Packet){p.Sources[1].OriginalSHA256=strings.Repeat("a",64)})
}
func TestNoMisrepresentedGoMoCap(t *testing.T){
	mutatedReject(t,func(p *Packet){p.Sources[1].RawCaptureVerified=true})
}
func TestNoFakeSourceSHA(t *testing.T){
	mutatedReject(t,func(p *Packet){p.Sources[0].OriginalSHA256="garbage"})
}
func TestNoUnownedTake(t *testing.T){
	mutatedReject(t,func(p *Packet){p.Sources[0].PublisherURL="http://example.invalid"})
}
func TestNoMissingDLE(t *testing.T){
	mutatedReject(t,func(p *Packet){p.UpstreamAuthorities=p.UpstreamAuthorities[:4]})
}
func TestNoDuplicateIDs(t *testing.T){
	mutatedReject(t,func(p *Packet){p.Sources[1].ID=p.Sources[0].ID})
}
func TestExternalFakeApprovedDoesNotPromote(t *testing.T){
	p:=load(t)
	p.Sources[0].OriginalSHA256=strings.Repeat("a",64)
	p.Sources[0].SkeletonSHA256=strings.Repeat("b",64)
	p.Sources[0].RawCaptureVerified=true
	p.Sources[0].OwnerAdmissionRef="OWNER_ASSERTED_BUT_NOT_VERIFIED"
	p.Sources[0].LicenseClassification="OWNER_ASSERTED"
	p.Sources[0].SourceFPS=120
	p.Sources[0].SourceFPSObserved=true
	p.Sources[0].SourceUnit="CMU_ASF_0.45"
	p.Sources[0].SourceUnitObserved=true
	r:=qualifies(t,p)
	for _,d:=range r.SourceDispositions{
		if d.ID=="cmu-07-01-catalog"{
			if d.Status!="READY_FOR_INDEPENDENT_PRIVATE_SOURCE_REVIEW_ONLY"||!d.RequiresPrivateCompute{
				t.Fatalf("metadata forged promotion %+v",d)
			}
		}
	}
	if r.R014ReleaseStatus!="HOLD"{t.Fatal("owner metadata forged model promotion")}
}
func TestReadPacketStrictUnknownField(t *testing.T){
	b,e:=os.ReadFile(catalogFile);if e!=nil{t.Fatal(e)}
	b=bytes.Replace(b,[]byte("\"r014_target\":"),[]byte("\"r014_target_typo\": \"forged\", \"r014_target\":"),1)
	tmp:=t.TempDir()+"/forged.json";if e=os.WriteFile(tmp,b,0600);e!=nil{t.Fatal(e)}
	if _,_,e=ReadPacket(tmp);e==nil{t.Fatal("unrecognized fields accepted")}
}
func TestUnrecognizedDatasetDenied(t *testing.T){
	mutatedReject(t,func(p *Packet){p.Sources[0].Dataset="PRIVATE_PERSON_FACE"})
}
