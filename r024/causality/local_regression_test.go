package causality

import "testing"

// Aggregate peak hover remains 80 mm at other stance ticks. A new 30 mm
// floating sole at an otherwise 20 mm tick is still a local regression.
func TestPerTickHoverRegressionHiddenByGlobalPeak(t *testing.T) {
 p:=pairFixture()
 p.Before.Samples[130].EvaluatedSole[2]=.028
 p.After.Samples[130].EvaluatedSole[2]=.038
 c,e:=Compare(p)
 if e!=nil {t.Fatal(e)}
 if c.Before.PeakHoverM!=c.After.PeakHoverM {t.Fatal("fixture did not preserve aggregate peak")}
 if c.Status!="RED_NUMERIC_REGRESSION__NO_PHYSICAL_CONTACT_CLAIM" {t.Fatalf("hidden hover: %+v",c)}
}
// Same total stance coverage can conceal which particular support tick loses
// contact. Local support may not be traded against a different tick.
func TestPerTickCoverageSwapDoesNotPass(t *testing.T) {
 p:=pairFixture()
 p.Before.Samples[130].EvaluatedSole[2]=.008
 p.After.Samples[130].EvaluatedSole[2]=.088
 p.Before.Samples[131].EvaluatedSole[2]=.088
 p.After.Samples[131].EvaluatedSole[2]=.008
 c,e:=Compare(p)
 if e!=nil {t.Fatal(e)}
 if c.Before.ContactCount!=c.After.ContactCount {t.Fatal("fixture changed total coverage")}
 if c.Status!="RED_NUMERIC_REGRESSION__NO_PHYSICAL_CONTACT_CLAIM" {t.Fatalf("hidden local coverage loss: %+v",c)}
}
