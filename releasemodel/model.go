package releasemodel

import (
 "github.com/sempersupra/stable-character-pipeline/releasegate"
 "github.com/sempersupra/stable-character-pipeline/releaseproof"
)
type OwnerState struct{
 SourceRights bool
 ExecutionAdmitted bool
 VisualQuality bool
 EvidenceCustody bool
 ExplicitApproval bool
}
func (o OwnerState) All()bool{
 return o.SourceRights&&o.ExecutionAdmitted&&o.VisualQuality&&o.EvidenceCustody&&o.ExplicitApproval
}
type Result struct{Status string;Code string}
func Evaluate(m releasegate.Manifest,p releaseproof.TrustPolicy,proofDir,evidenceDir string,o OwnerState)Result{
 x:=releasegate.Validate(m)
 if x.Status=="UNKNOWN"{return Result{"HOLD","DRAFT_UNPROMOTABLE"}}
 if x.Status!="PASS"{return Result{"HOLD","STRUCTURAL_EVIDENCE_NOT_QUALIFIED"}}
 y:=releaseproof.Verify(m,p,proofDir,evidenceDir)
 if y.Status!="PASS"{return Result{"HOLD","INDEPENDENT_EVIDENCE_NOT_QUALIFIED"}}
 if !o.All(){return Result{"HOLD","OWNER_GATES_UNSATISFIED"}}
 // Advisory only: caller-supplied OwnerState cannot authenticate an owner.
 return Result{"READY_FOR_MANUAL_REVIEW_NOT_RELEASED","ADVISORY_GATES_PRESENT"}
}
