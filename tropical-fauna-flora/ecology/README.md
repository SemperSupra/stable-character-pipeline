# Ecological state / rule-sweep workcell — phase E0

This is an **experimental Go reference contract**, not an ecological model accepted against real observations. It does not replace OpenAlea, Helios, Blender, SLEAP, or other qualified domain backends.

- `scp.ecology.v1` JSON contract is independent of the renderer.
- Plant patches conserve biomass in integer grams across regrowth and grazing events. The update clock is an arbitrary bounded decision tick, **not** physical simulation time.
- Buffalo choose the highest-biomass patch, consume bounded available forage, and never consume negative biomass.
- Egrets deterministically follow the patch chosen by a buffalo without consuming plant biomass.
- The simulation emits every tick's states, events, resource ledger, and stable trace digest.
- Scenario fields include `fidelity`: `earth_prototype` or `speculative`. They are labels, **not scientific realism claims**. A hypothetical high-light/high-growth scenario is provided to begin rule-sweep qualification.
- As a first example, changing the light multiplier changes regrowth and resource balances; gravity, atmosphere, physiology, phenotypic plant changes, mechanics and bird feeding are **not modeled** yet and must not be inferred from these results.

Run in this subproject (from the parent `tropical-fauna-flora` directory):

```bash
go test -race ./...
go run ./cmd/ecologyprobe -config examples/earth.json -out out/earth_ecology.json
go run ./cmd/ecologyprobe -config examples/alien.json -out out/alien_ecology.json
```

Acceptance: deterministic same-seed trace, order-independent patch and animal fixtures, nonnegative bounded biomass, accounted resources, egret following, positive and negative rule controls, JSON result with digest.

**Next integration:** derive animator/bender/driving motion from `scp.ecology.v1` events with explicit mapping of the arbitrary decision tick to scene seconds, and qualify plant physical growth using dedicated botanically grounded backends. Do not display this as a scientifically validated Earth ecology or as alien life prediction.
