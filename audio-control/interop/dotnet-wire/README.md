# Audio Control R2 — .NET 10 wire contract interoperability

**Nonproduction / no device access.** This workcell is stacked on the *existing* portable protocol + host boundary source [PR #729](https://github.com/SemperSupra/stable-character-pipeline/pull/729). It does not alter source `audio_control.r0.schema.json`, vectors, Aural's C# DSP/QuietSearch, Go reducer or local actor's CLI patches. It qualifies whether a small .NET 10 program can read the **same** JSON envelope/receipt format and reject the original 13 positive/negative fixtures plus seven independently classified host-channel cases.

It uses .NET's built-in `System.Text.Json` and a **test-only interpreter for exactly the reviewed JSON Schema R0 keyword subset**. It is not an endorsed general-purpose JSON Schema implementation. Unknown schema keywords throw rather than being silently ignored; changing the schema must trigger independent requalification. It also tests absent/null principal and unrecognized host privilege properties as negative cases.

`dotnet run --project audio-control/interop/dotnet-wire/Probe.csproj --configuration Release -- .` from repository root. Public GitHub Actions qualifies on Windows/macOS/Ubuntu without NuGet dependencies. This is **shape/wire compatibility**, not runtime state-machine semantic equivalence, verified host identity, OS-native mobile binding, actual physical audio STOP, or clinical safety. Host-only JSON is not authenticated simply because the schema accepts it.

Portability conclusion is to share the **protocol and test fixtures**, not automatically embed a Go/Python control runtime into Android, Windows or Apple interfaces. Product-owned adapters and user authorization remain authority. Draft only; no merge, production deployment, real data or release.
