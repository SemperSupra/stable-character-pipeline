package motion

import "math"

// SyntheticReference is an independently authored TEST oracle, not an
// attestation of camera provenance or a replacement for real-world calibration.
// A production actor must supply independently authenticated witness custody.
type SyntheticReference struct {
    Camera Stereo
    Actors [2]Prior
    NoiseSigmaUpperBoundPixels float64
    MaxActorErrorMeters float64
    Calibrated bool
    ActorPositionsMeasured bool
    NoiseDistributionMeasured bool
}

// IndependentSyntheticAdmission is intentionally FAIL-CLOSED. Existing v10
// Association can ACCEPT false priors/camera focal under self-consistency.
// This additional research-only observer checks against independent synthetic
// ground truth; real camera/actor/sigma claims require a separate authority.
func (s Stereo) IndependentSyntheticAdmission(left,right [2]Detection, prior [2]Prior, ref SyntheticReference) Result {
    abstain:=Result{Status:Abstain}
    bad:=Result{Status:Reject}
    if !ref.Calibrated || !ref.ActorPositionsMeasured || !ref.NoiseDistributionMeasured {
        return abstain
    }
    if s.validate()!=nil || ref.Camera.validate()!=nil ||
        !finite(ref.NoiseSigmaUpperBoundPixels,ref.MaxActorErrorMeters) ||
        ref.NoiseSigmaUpperBoundPixels<=0 || ref.MaxActorErrorMeters<=0 {
        return bad
    }
    // This exact synthetic reference fixture has frozen calibration values.
    // An epsilon here is only floating-point representation precision, NOT
    // a real-world calibration error budget.
    if math.Abs(s.FocalPixels-ref.Camera.FocalPixels)>1e-10 ||
       math.Abs(s.BaselineMeters-ref.Camera.BaselineMeters)>1e-10 {
        return bad
    }
    for _,a:=range ref.Actors {
        if !finite(a.X,a.Z) || a.Z<=0 {return bad}
    }
    candidate:=s.AssociateWithNoiseWitness(left,right,prior,
        ref.MaxActorErrorMeters, .15,ref.NoiseSigmaUpperBoundPixels,3)
    if candidate.Status!=Accept {return candidate}
    for i,p:=range candidate.Pairs {
        truth:=ref.Actors[i]
        if !finite(p.X,p.Z) || math.Hypot(p.X-truth.X,p.Z-truth.Z)>ref.MaxActorErrorMeters {
            return bad
        }
    }
    return candidate
}
