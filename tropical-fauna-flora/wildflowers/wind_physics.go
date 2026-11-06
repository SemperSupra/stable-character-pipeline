package main

// Reduced-order wind response qualification, deliberately NOT claimed to be
// calibrated to any plant species or embedded in the exported GLB yet.
// A single laterally deflecting effective mass at the plant tip follows a
// damped spring subject to relative-air-speed quadratic drag. The fixed-step
// semi-implicit integrator is bounded and self-contained (Go stdlib only).
import (
	"encoding/json"
	"fmt"
	"math"
	"os"
)

type WindProbeInput struct {
	Schema               string  `json:"schema"`
	PlantID              string  `json:"plant_id"`
	MassKg               float64 `json:"effective_mass_kg"`
	StiffnessNPerM       float64 `json:"lateral_stiffness_n_per_m"`
	DampingNSPerM        float64 `json:"damping_n_s_per_m"`
	DragCoefficient      float64 `json:"drag_coefficient"`
	ProjectedAreaM2      float64 `json:"projected_area_m2"`
	AirDensityKgPerM3    float64 `json:"air_density_kg_per_m3"`
	WindMeanMPerS        float64 `json:"wind_mean_m_per_s"`
	GustAmplitudeMPerS   float64 `json:"gust_amplitude_m_per_s"`
	GustPeriodS          float64 `json:"gust_period_s"`
	StepS                float64 `json:"time_step_s"`
	DurationS            float64 `json:"duration_s"`
	MaxDisplacementM     float64 `json:"allowed_displacement_m"`
	InitialDisplacementM float64 `json:"initial_displacement_m"`
	InitialVelocityMPerS float64 `json:"initial_velocity_m_per_s"`
}
type WindProbeSample struct {
	TimeS             float64 `json:"time_s"`
	WindMPerS         float64 `json:"wind_m_per_s"`
	TipDisplacementM  float64 `json:"tip_displacement_m"`
	TipVelocityMPerS  float64 `json:"tip_velocity_m_per_s"`
	DragForceN        float64 `json:"drag_force_n"`
	ElasticForceN     float64 `json:"elastic_force_n"`
	MechanicalEnergyJ float64 `json:"mechanical_energy_j"`
}
type WindProbeReceipt struct {
	Schema              string            `json:"schema"`
	ModelStatus         string            `json:"model_status"`
	PlantID             string            `json:"plant_id"`
	Parameters          WindProbeInput    `json:"parameters"`
	MaxAbsDisplacementM float64           `json:"max_abs_displacement_m"`
	MaxAbsVelocityMPerS float64           `json:"max_abs_velocity_m_per_s"`
	Samples             []WindProbeSample `json:"samples"`
}

func finite(x float64) bool { return !math.IsNaN(x) && !math.IsInf(x, 0) }
func ValidateWindProbe(p WindProbeInput) error {
	vals := []float64{p.MassKg, p.StiffnessNPerM, p.DampingNSPerM, p.DragCoefficient, p.ProjectedAreaM2, p.AirDensityKgPerM3, p.WindMeanMPerS, p.GustAmplitudeMPerS, p.GustPeriodS, p.StepS, p.DurationS, p.MaxDisplacementM, p.InitialDisplacementM, p.InitialVelocityMPerS}
	for _, v := range vals {
		if !finite(v) {
			return fmt.Errorf("nonfinite wind parameter")
		}
	}
	if p.PlantID == "" || p.MassKg <= 0 || p.StiffnessNPerM <= 0 || p.DampingNSPerM < 0 || p.DragCoefficient <= 0 || p.DragCoefficient > 4 || p.ProjectedAreaM2 <= 0 || p.AirDensityKgPerM3 <= 0 || p.AirDensityKgPerM3 > 2 || p.WindMeanMPerS < -40 || p.WindMeanMPerS > 40 || p.GustAmplitudeMPerS < 0 || p.GustAmplitudeMPerS > 40 || p.GustPeriodS <= 0 || p.GustPeriodS > 120 || p.StepS <= 0 || p.StepS > .05 || p.DurationS <= 0 || p.DurationS > 20 || p.MaxDisplacementM <= 0 || p.MaxDisplacementM > 20 {
		return fmt.Errorf("wind parameters out of bounded domain")
	}
	n := math.Round(p.DurationS / p.StepS)
	if n < 4 || n > 5000 || math.Abs(n*p.StepS-p.DurationS) > 1e-7 {
		return fmt.Errorf("unbounded or nonintegral simulation step count")
	}
	natural := math.Sqrt(p.StiffnessNPerM / p.MassKg)
	if p.StepS*natural > .2 || p.StepS*p.DampingNSPerM/p.MassKg > .2 {
		return fmt.Errorf("potentially unstable discretization")
	}
	if math.Abs(p.InitialDisplacementM) > p.MaxDisplacementM {
		return fmt.Errorf("initial position outside displacement budget")
	}
	return nil
}
func RunWindProbe(p WindProbeInput) (WindProbeReceipt, error) {
	r := WindProbeReceipt{Schema: "scp.flora.wind-single-mode-qualification.v1", ModelStatus: "synthetic-unmeasured-lumped-mass-drag-not-botanical-physics", PlantID: p.PlantID, Parameters: p, Samples: []WindProbeSample{}}
	if err := ValidateWindProbe(p); err != nil {
		return r, err
	}
	n := int(math.Round(p.DurationS / p.StepS))
	x, v := p.InitialDisplacementM, p.InitialVelocityMPerS
	for k := 0; k <= n; k++ {
		t := float64(k) * p.StepS
		air := p.WindMeanMPerS + p.GustAmplitudeMPerS*math.Sin(2*math.Pi*t/p.GustPeriodS)
		relative := air - v
		drag := .5 * p.AirDensityKgPerM3 * p.DragCoefficient * p.ProjectedAreaM2 * relative * math.Abs(relative)
		elastic := -p.StiffnessNPerM * x
		energy := .5*p.MassKg*v*v + .5*p.StiffnessNPerM*x*x
		if !finite(x) || !finite(v) || !finite(drag) || !finite(energy) {
			return r, fmt.Errorf("nonfinite dynamic state")
		}
		if math.Abs(x) > p.MaxDisplacementM {
			return r, fmt.Errorf("deflection budget exceeded at step %d", k)
		}
		r.Samples = append(r.Samples, WindProbeSample{TimeS: t, WindMPerS: air, TipDisplacementM: x, TipVelocityMPerS: v, DragForceN: drag, ElasticForceN: elastic, MechanicalEnergyJ: energy})
		r.MaxAbsDisplacementM = math.Max(r.MaxAbsDisplacementM, math.Abs(x))
		r.MaxAbsVelocityMPerS = math.Max(r.MaxAbsVelocityMPerS, math.Abs(v))
		if k == n {
			break
		}
		acceleration := (drag + elastic - p.DampingNSPerM*v) / p.MassKg
		v += acceleration * p.StepS
		x += v * p.StepS
	}
	return r, nil
}
func SyntheticWindProfile(s Preset) WindProbeInput {
	// Values are illustrative. They MUST NOT be mistaken for measured allometry.
	mass, k, area := .025, 1., .015
	switch s.Template {
	case "grass", "wheat", "oats":
		mass, k, area = .012, .85, .006
	case "maize":
		mass, k, area = .20, 30, .20
	case "sunflower":
		mass, k, area = .14, 18, .14
	case "grapevine", "shrub":
		mass, k, area = 2, 150, 1.2
	case "bamboo":
		mass, k, area = 1.0, 130, .5
	case "tree", "conifer":
		mass, k, area = 30, 7000, 9
	}
	return WindProbeInput{Schema: "scp.flora.wind-input.synthetic.v1", PlantID: s.ID, MassKg: mass, StiffnessNPerM: k, DampingNSPerM: 2 * .23 * math.Sqrt(mass*k), DragCoefficient: 1.1, ProjectedAreaM2: area, AirDensityKgPerM3: 1.2, WindMeanMPerS: 1.5, GustAmplitudeMPerS: 1., GustPeriodS: 4, StepS: 1. / 120., DurationS: 4, MaxDisplacementM: math.Max(.1, float64(s.Height)*.25)}
}
func writeWindProbe(path string, r WindProbeReceipt) error {
	b, err := json.MarshalIndent(r, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(path, append(b, '\n'), 0644)
}
