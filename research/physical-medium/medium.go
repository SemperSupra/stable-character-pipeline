// Package medium contains a deliberately bounded, ideal-gas acoustic oracle.
// It is NOT a breathing-safety model or a validated human-voice synthesizer.
package medium

import (
    "errors"
    "math"
)

const R = 8.31446261815324 // J/(mol K)
const tolerance = 1e-9

// Species is a fixed-temperature gas-property approximation. Cp is J/(mol K).
type Species struct {
    Name string `json:"name"`
    MoleFraction float64 `json:"mole_fraction"`
    MolarMass float64 `json:"molar_mass_kg_per_mol"`
    CpMolar float64 `json:"cp_j_per_mol_k"`
}

type State struct {
    PressurePa float64 `json:"pressure_pa"`
    TemperatureK float64 `json:"temperature_k"`
    Species []Species `json:"species"`
}

type Properties struct {
    MolarMass float64 `json:"molar_mass_kg_per_mol"`
    Gamma float64 `json:"gamma"`
    Density float64 `json:"density_kg_per_m3"`
    SoundSpeed float64 `json:"sound_speed_m_per_s"`
    Impedance float64 `json:"specific_acoustic_impedance_pa_s_per_m"`
}

func finite(x float64) bool { return !math.IsNaN(x) && !math.IsInf(x, 0) }

func (s State) Evaluate() (Properties, error) {
    var out Properties
    if !finite(s.PressurePa) || !finite(s.TemperatureK) || s.PressurePa <= 0 || s.TemperatureK <= 0 || len(s.Species) == 0 || len(s.Species) > 32 {
        return out, errors.New("invalid gas state: pressure, temperature or species count")
    }
    var fraction, cp float64
    seen := map[string]bool{}
    for _, sp := range s.Species {
        if sp.Name == "" || seen[sp.Name] || !finite(sp.MoleFraction) || !finite(sp.MolarMass) || !finite(sp.CpMolar) || sp.MoleFraction < 0 || sp.MoleFraction > 1 || sp.MolarMass <= 0 || sp.CpMolar <= R {
            return out, errors.New("invalid or duplicate gas species")
        }
        seen[sp.Name] = true
        fraction += sp.MoleFraction
        cp += sp.MoleFraction * sp.CpMolar
        out.MolarMass += sp.MoleFraction * sp.MolarMass
    }
    if !finite(fraction) || math.Abs(fraction-1) > tolerance || !(cp > R) || !(out.MolarMass > 0) {
        return Properties{}, errors.New("gas fractions must sum to one and have valid heat capacity")
    }
    out.Gamma = cp/(cp-R)
    out.Density = s.PressurePa*out.MolarMass/(R*s.TemperatureK)
    out.SoundSpeed = math.Sqrt(out.Gamma*R*s.TemperatureK/out.MolarMass)
    out.Impedance = out.Density*out.SoundSpeed
    if !finite(out.SoundSpeed) || !finite(out.Impedance) || !finite(out.Gamma) || !finite(out.Density) || out.SoundSpeed <= 0 {
        return Properties{}, errors.New("gas properties overflow")
    }
    return out, nil
}

// QuarterWave returns a *uniform, one-ended* tube's (odd) resonance estimate.
// It is an independent illustrative check, NOT a human vocal tract model.
func QuarterWave(n int, lengthMeters, soundSpeed float64) (float64, error) {
    if n < 1 || n > 100 || !finite(lengthMeters) || lengthMeters <= 0 || !finite(soundSpeed) || soundSpeed <= 0 { return 0, errors.New("invalid quarter-wave arguments") }
    f:=float64(2*n-1)*soundSpeed/(4*lengthMeters);if !finite(f)||f<=0 {return 0,errors.New("invalid or overflowing quarter-wave resonance")};return f,nil
}

func Earthlike() State {
    return State{PressurePa:101325, TemperatureK:293.15, Species: []Species{
        {"nitrogen",0.78,0.0280134,29.124},
        {"oxygen",0.21,0.0319988,29.376},
        {"argon",0.01,0.039948,20.786},
    }}
}
