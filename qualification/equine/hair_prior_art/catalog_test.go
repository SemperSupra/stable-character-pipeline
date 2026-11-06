package main

import (
  "encoding/json"
  "os"
  "strings"
  "testing"
)

type Candidate struct {
  ID string `json:"id"`
  Role string `json:"role"`
  License string `json:"license"`
  CodeImport string `json:"code_import"`
  Status string `json:"status"`
  Source string `json:"source"`
  Evidence string `json:"evidence"`
  Hold string `json:"hold"`
}
type Catalog struct {
  Schema string `json:"schema"`
  Reviewed string `json:"reviewed_on"`
  Candidates []Candidate `json:"candidates"`
  Admission struct {
    ThirdPartyCode bool `json:"source_code_from_third_party_imported"`
    ThirdPartyMedia bool `json:"reference_models_or_photos_imported"`
    ProductionUnchanged bool `json:"existing_blender_4_5_15_production_pin_unchanged"`
    ScienceAccepted bool `json:"scientific_model_accepted"`
    ReleaseApproved bool `json:"merge_or_release_approved"`
    NextGate string `json:"next_gate"`
  } `json:"admission"`
}
func TestPriorArtCatalogRightsAndOwnerGate(t *testing.T){
  b,e:=os.ReadFile("decision_catalog.v1.json");if e!=nil{t.Fatal(e)}
  var c Catalog;if e:=json.Unmarshal(b,&c);e!=nil{t.Fatal(e)}
  if c.Schema!="equine.hair.prior_art.v1"||c.Reviewed!="2026-11-06" {t.Fatal("catalog identity")}
  if len(c.Candidates)<10 {t.Fatal("shallow prior art")}
  a:=c.Admission
  if a.ThirdPartyCode||a.ThirdPartyMedia||!a.ProductionUnchanged||a.ScienceAccepted||a.ReleaseApproved||a.NextGate==""{
    t.Fatal("unsafe implicit admission of vendor rights/science")
  }
  seen:=map[string]bool{}
  for _,x:=range c.Candidates{
    if x.ID==""||seen[x.ID]||x.Hold==""||x.Role==""||x.License==""||x.Status==""{
      t.Fatalf("unreviewable catalog row %+v",x)
    }
    seen[x.ID]=true
    if !strings.HasPrefix(x.Source,"https://")||!strings.HasPrefix(x.Evidence,"https://"){
      t.Fatalf("unverified external source: %s",x.ID)
    }
    if x.CodeImport=="YES" {t.Fatalf("unapproved third party code imported: %s",x.ID)}
    if x.License=="Unity Companion License" && (x.Status!="REFERENCE_ONLY"||x.CodeImport!="NO"){
      t.Fatal("Unity Companion License must remain reference only")
    }
  }
  if !seen["blender52_gn_xpbd"]||!seen["position_based_dynamics"]||!seen["tressfx"]||!seen["openusd_basis_curves"]{
    t.Fatal("missing critical reusable primitive")
  }
}
