// R051 validates one bounded independent work batch. It is a source-safe,
// standard-library-only command-line projection of a DLE—not a scheduler.
package main

import (
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"os"
	"path"
	"slices"
	"strings"
)

const Schema = "scp.r051.batch-rep.v1"

type Packet struct {
	ID string `json:"id"`
	Owner string `json:"owner"`
	State string `json:"state"`
	Venue string `json:"venue"`
	AssetClass string `json:"asset_class"`
	SourceDLE string `json:"source_dle"`
	OwnedPaths []string `json:"owned_paths"`
	Branch string `json:"branch"`
	Requires []string `json:"requires"`
	Deliverable string `json:"deliverable"`
	Oracle string `json:"oracle"`
	Negative string `json:"negative"`
	Fallback string `json:"fallback"`
	MaxCorrectiveCycles int `json:"max_corrective_cycles"`
}
type Admission struct {
	NoPrivateGitHubActions bool `json:"no_private_github_actions"`
	NoProtectedMediaInPublic bool `json:"no_protected_media_in_public"`
	NoMergeReleaseOrAdmission bool `json:"no_merge_release_or_admission"`
	DoNotMutateExistingOwnerPRs bool `json:"do_not_mutate_existing_owner_prs"`
}
type Batch struct {
	Schema string `json:"schema"`
	Authority map[string]string `json:"authority"`
	Scope string `json:"scope"`
	MaxConcurrent int `json:"max_concurrent"`
	MinEligible int `json:"min_eligible"`
	Admission Admission `json:"admission"`
	Packets []Packet `json:"packets"`
	RepReceiptRequired []string `json:"rep_receipt_required"`
	StopRule string `json:"stop_rule"`
	Reconciliation string `json:"reconciliation"`
}
type Receipt struct {
	Schema string `json:"schema"`
	Status string `json:"status"`
	Packets int `json:"packets"`
	Eligible int `json:"eligible"`
	Gated int `json:"gated"`
	IndependentPairs int `json:"independent_pairs"`
	MaxConcurrent int `json:"max_concurrent"`
	Limits string `json:"limits"`
}

func cleanPath(s string) error {
	if s==""||strings.HasPrefix(s,"/")||strings.Contains(s,"\")||strings.Contains(s,":") {return errors.New("invalid owned path")}
	t:=strings.TrimSuffix(s,"/**")
	if t==""||t=="."||path.Clean(t)!=t {
		return fmt.Errorf("unsafe path %q",s)
	}
	for _,part:=range strings.Split(t,"/") {if part==".."||part==""{return fmt.Errorf("unsafe traversal %q",s)}}
	return nil
}
func overlap(a,b string) bool {
	a=strings.TrimSuffix(a,"/**")
	b=strings.TrimSuffix(b,"/**")
	return a==b||strings.HasPrefix(a,b+"/")||strings.HasPrefix(b,a+"/")
}

func Validate(batch Batch) (Receipt,error) {
	r:=Receipt{Schema:"r051.batch-validator-receipt.v1",Packets:len(batch.Packets),
		MaxConcurrent:batch.MaxConcurrent,
		Limits:"Manifest structural independence only; no actual runner admission, concurrency, local actor work, rights or acceptance established"}
	fail:=func(msg string)(Receipt,error){r.Status="REJECTED";return r,fmt.Errorf("R051_BATCH_HOLD %s",msg)}
	if batch.Schema!=Schema||batch.Scope==""||len(batch.Authority)<3 {return fail("missing authority/schema/scope")}
	if !batch.Admission.NoPrivateGitHubActions||!batch.Admission.NoProtectedMediaInPublic||
	   !batch.Admission.NoMergeReleaseOrAdmission||!batch.Admission.DoNotMutateExistingOwnerPRs {
		return fail("required authority and data-custody boundaries missing")
	}
	if batch.MaxConcurrent<2||batch.MaxConcurrent>4||batch.MinEligible<2||
		batch.MinEligible>batch.MaxConcurrent||len(batch.Packets)<3||
		len(batch.Packets)>8{return fail("invalid bounded 2+1 batch sizing")}
	if len(batch.RepReceiptRequired)<8||batch.StopRule==""||batch.Reconciliation=="" {
		return fail("missing executable one-rep evidence and stop rule")
	}
	ids:=map[string]bool{}
	branches:=map[string]bool{}
	for _,p:=range batch.Packets {
		if p.ID==""||ids[p.ID]||p.Owner==""||p.SourceDLE==""||
			p.Branch==""||branches[p.Branch]||p.Deliverable==""||p.Oracle==""||
			p.Negative==""||p.Fallback==""||p.MaxCorrectiveCycles!=1 {
			return fail("duplicate/underbounded packet or branch "+p.ID)
		}
		ids[p.ID]=true
		branches[p.Branch]=true
		if len(p.OwnedPaths)==0 {return fail("unscoped writable paths "+p.ID)}
		for _,owned:=range p.OwnedPaths{
			if err:=cleanPath(owned);err!=nil{return fail(p.ID+" "+err.Error())}
		}
		if strings.HasPrefix(p.Venue,"PUBLIC")&&(p.AssetClass=="PRIVATE"||p.AssetClass=="RESTRICTED") {
			return fail("restricted content routed to public venue "+p.ID)
		}
		if !slices.Contains([]string{"SOURCE_ONLY","PRIVATE","RESTRICTED"},p.AssetClass) {
			return fail("unknown privacy class "+p.ID)
		}
		switch p.State {
		case "READY":
			if len(p.Requires)>0{return fail("pretending gated packet is READY "+p.ID)}
			r.Eligible++
		case "GATED":
			if len(p.Requires)==0{return fail("gated packet has no stated requirement "+p.ID)}
			r.Gated++
		default:return fail("unrecognized state "+p.ID)
		}
	}
	for i,a:=range batch.Packets {
		for _,b:=range batch.Packets[i+1:] {
			for _,x:=range a.OwnedPaths{
				for _,y:=range b.OwnedPaths{
					if overlap(x,y){return fail("cross-lane file ownership conflict "+a.ID+"/"+b.ID)}
				}
			}
			if a.State=="READY"&&b.State=="READY"{r.IndependentPairs++}
		}
	}
	if r.Eligible<batch.MinEligible||r.IndependentPairs<1 {
		return fail("not enough eligible independent work; do not misstate parallelism")
	}
	r.Status="VALID_SOURCE_SAFE_CONTRACT_ONLY"
	return r,nil
}

func main() {
	file:=flag.String("manifest","","JSON batch manifest, private bytes stay local")
	flag.Parse()
	if *file==""{fmt.Fprintln(os.Stderr,"R051_BATCH_HOLD --manifest required");os.Exit(12)}
	f,err:=os.Open(*file)
	if err!=nil{fmt.Fprintln(os.Stderr,"R051_BATCH_HOLD",err);os.Exit(12)}
	defer f.Close()
	raw,err:=io.ReadAll(io.LimitReader(f,1<<20))
	if err!=nil||len(raw)>=(1<<20){fmt.Fprintln(os.Stderr,"R051_BATCH_HOLD invalid bounded JSON length");os.Exit(12)}
	var b Batch
	if err:=json.Unmarshal(raw,&b);err!=nil{fmt.Fprintln(os.Stderr,"R051_BATCH_HOLD",err);os.Exit(12)}
	r,err:=Validate(b)
	if err!=nil {fmt.Fprintln(os.Stderr,err);os.Exit(12)}
	data,_:=json.Marshal(r)
	fmt.Println("R051_BATCH_CONTRACT_RECEIPT",string(data))
}
