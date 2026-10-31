package main
import "testing"
func fixture() (Source,Policy) {
 a:=[]Actor{}
 for _,id:=range []string{"CobaltOriginal","MarigoldOriginal"} {
  actor:=Actor{ID:id}
  for i:=0;i<24;i++{
   actor.Frames=append(actor.Frames,Frame{Index:i,TimeNum:i,TimeDen:12,Legs:[]Leg{{ID:"Left"},{ID:"Right"}}})
  }
  a=append(a,actor)
 }
 s:=Source{Schema:"scp.walk_w7a_original_approach.v1",Rights:rights,Profile:"forward",
  FPSNum:12,FPSDen:1,Scenario:"ORIGINAL_2ACTOR_WORLD_X_APPROACH_NOT_HUMAN_GAIT",
  KneePoleBasis:"ARTIFICIAL_SAGITTAL_FORWARD_Y_NO_ANATOMICAL_JCS",Actors:a}
 p:=Policy{Schema:"scp.visualqa.w9a_policy.v1",SubjectKind:"human",Action:"walking",Style:"typical",
  NormativeRefIDs:[]string{"ISB_2002_JCS_REFERENCE_ONLY","NMS_VV_2014_VALIDATION_GUIDANCE_ONLY"}}
 return s,p
}
func TestHumanIncompleteRigAbstains(t *testing.T){
 s,p:=fixture();v,e:=Evaluate(s,p,"fixture")
 if e!=nil||v.HumanNaturalGait[:7]!="ABSTAIN"||v.HumanAnatomicalJCS[:7]!="UNKNOWN"||v.SourceGroundTruthIsNormativeOracle {
  t.Fatalf("false admission %+v err=%v",v,e)
 }
}
func TestAnimalDoesNotInheritHumanJCS(t *testing.T){
 s,p:=fixture();p.SubjectKind="animal";v,e:=Evaluate(s,p,"fixture")
 if e!=nil||v.Eligibility!="ABSTAIN_WRONG_TAXON_AND_HOMOLOGY"||v.AnimalBehavior[:7]!="ABSTAIN"{t.Fatalf("%+v %v",v,e)}
}
func TestRobotDoesNotInheritBiologicalThresholds(t *testing.T){
 s,p:=fixture();p.SubjectKind="mechanical";v,e:=Evaluate(s,p,"fixture")
 if e!=nil||v.MechanicalDynamics!="ABSTAIN_NO_JOINT_ACTUATOR_ENVELOPE"{t.Fatalf("%+v %v",v,e)}
}
func TestHostileSourceAndPolicyClaimsRejected(t *testing.T){
 tests:=[]struct{name string;mut func(*Source,*Policy)}{
  {"rights",func(s *Source,p *Policy){s.Rights="PRIVATE"}},
  {"clock",func(s *Source,p *Policy){s.Actors[0].Frames[3].TimeNum=5}},
  {"wrong_side",func(s *Source,p *Policy){s.Actors[1].Frames[3].Legs[0].ID="Right"}},
  {"fake_anatomy",func(s *Source,p *Policy){p.SourceRigHasAnatomicalUpperBody=true}},
  {"human_pole",func(s *Source,p *Policy){p.UseSourcePoleAsAnatomicalJCS=true}},
  {"invented_limit",func(s *Source,p *Policy){p.NumericLimits=map[string]interface{}{"human_knee_max_rad":1.0}}},
  {"invalid_taxon",func(s *Source,p *Policy){p.SubjectKind="alien_unknown"}},
  {"missing_ref",func(s *Source,p *Policy){p.NormativeRefIDs=nil}},
  {"forged_source_jcs",func(s *Source,p *Policy){s.KneePoleBasis="VALID_ISB_JCS"}},
  {"missing_action",func(s *Source,p *Policy){p.Action="unknown"}},
 }
 for _,tt:=range tests{
  t.Run(tt.name,func(t *testing.T){s,p:=fixture();tt.mut(&s,&p);_,e:=Evaluate(s,p,"fixture")
   if e==nil{t.Fatal("false acceptance")}})
 }
}
