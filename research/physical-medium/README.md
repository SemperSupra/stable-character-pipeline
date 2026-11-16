# Physical medium research oracle — draft, CPU only

Independent synthetic-only Go 1.23 standard-library model for gas-mixture acoustic properties. This is a small mathematical *oracle* for [future DLE #529](https://github.com/SemperSupra/stable-character-pipeline/issues/529), **not** a clinical breathing-safety evaluator, a true vocal-tract acoustics engine, or a deployment. Nothing here decides whether an alien atmosphere is breathable.

Run `go test -race -count=1 ./... && go vet ./...` and `go run ./cmd/gasprobe` from this module.

Mixture properties use constant molar heat capacities at roughly room temperature, ideal gas, no chemical reactions/humidity, no temperature-dependent thermodynamics or losses. The one-ended uniform-tube quarter-wave formula is a simplified independent check. Published or measured external reference data and a Cantera/CoolProp bakeoff are needed before physical qualification. No mixing of private engine code or changes to historical fixtures. No hosted runner, merge, deployment or release implied.
