// Actual cross-language process transport: .NET native client drives the
// existing Go control-probe -- no second reducer or audio device is created.
using System.Diagnostics;
using System.Text.Json;

static class Program
{
    static void Require(bool ok, string why)
    {
        if (!ok) throw new InvalidOperationException(why);
    }

    static string RunGo(string exe, string mode, string input = "")
    {
        var psi = new ProcessStartInfo(exe)
        {
            UseShellExecute = false,
            RedirectStandardInput = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            CreateNoWindow = true,
        };
        psi.ArgumentList.Add(mode);
        using var process = Process.Start(psi)
            ?? throw new InvalidOperationException("No Go control-probe process");
        process.StandardInput.Write(input);
        process.StandardInput.Close();
        var output = process.StandardOutput.ReadToEnd();
        var error = process.StandardError.ReadToEnd();
        Require(process.WaitForExit(10000), "Go probe process hung");
        Require(process.ExitCode == 0, "Go probe rejected a valid client: " + error);
        return output;
    }

    static string JsonCommand(string op, string action, int expectedRevision,
        string? digest = null, int? epoch = null)
    {
        var c = new Dictionary<string, object>
        {
            ["schema_version"] = "audio_control.r0",
            ["principal_id"] = "synthetic_human",
            ["session_id"] = "synthetic_session",
            ["target_id"] = "selected_synthetic_headphones",
            ["operation_id"] = op,
            ["action"] = action,
            ["expected_revision"] = expectedRevision,
        };
        if (digest != null) c["config_digest"] = digest;
        if (epoch.HasValue) c["epoch"] = epoch.Value;
        return JsonSerializer.Serialize(c);
    }

    static JsonElement Receipt(JsonElement envelope) =>
        envelope.GetProperty("receipt");
    static string Status(JsonElement element) =>
        Receipt(element).GetProperty("status").GetString()
            ?? throw new InvalidOperationException("Missing receipt status");

    static void Main(string[] args)
    {
        Require(args.Length == 1, "Pass exactly one compiled native Go control-probe executable path.");
        var exe = Path.GetFullPath(args[0]);
        Require(File.Exists(exe), "Compiled Go probe missing.");
        using var capabilities = JsonDocument.Parse(RunGo(exe, "capabilities"));
        var d = capabilities.RootElement;
        Require(d.GetProperty("schema_version").GetString() == "audio_control.r0",
            "Contract version mismatch");
        Require(!d.GetProperty("is_production").GetBoolean() &&
                !d.GetProperty("can_play_physical_audio").GetBoolean() &&
                d.GetProperty("requires_trusted_host_for_effects").GetBoolean(),
            "Client must not infer physical authorization from capabilities");

        var plan = new string('a', 64);
        var configure = JsonCommand("configure_1", "configure", 0, plan);
        var start = JsonCommand("start_1", "request_start", 1);
        var forgedHost = JsonCommand("forged_1", "host_started", 2, epoch: 1);
        var stop = JsonCommand("stop_1", "stop", 0); // Deliberately stale CAS; STOP preempts.
        var collision = JsonCommand("start_1", "stop", 3);
        var input = string.Join("\n",
            configure, start, start, forgedHost, stop, stop, collision) + "\n";
        var output = RunGo(exe, "simulate", input);
        var lines = output.Split('\n', StringSplitOptions.RemoveEmptyEntries);
        Require(lines.Length == 7, "Go probe returned unexpected receipt count");

        using var received = JsonDocument.Parse("[" + string.Join(",", lines) + "]");
        var a = received.RootElement;
        Require(Status(a[0]) == "accepted" &&
                Receipt(a[0]).GetProperty("state").GetString() == "configured",
            "C# configure rejected by Go");
        Require(Status(a[1]) == "accepted" &&
                Receipt(a[1]).GetProperty("state").GetString() == "start_pending" &&
                Receipt(a[1]).GetProperty("epoch").GetUInt64() == 1,
            "Go START approval incorrectly treated as audible playback");
        Require(a[1].GetProperty("effect_intents")[0].GetProperty("kind").GetString()
                == "host_authorize_then_start", "Missing host authorization effect");
        Require(a[2].GetProperty("replayed").GetBoolean() &&
                a[2].GetProperty("effect_intents").ValueKind == JsonValueKind.Undefined,
            "Go replay dispatched a duplicate effect intent");
        Require(Receipt(a[1]).GetRawText() == Receipt(a[2]).GetRawText(),
            "Go replay did not preserve original immutable receipt");
        Require(Status(a[3]) == "host_observation_requires_trusted_adapter" &&
                Receipt(a[3]).GetProperty("state").GetString() == "start_pending",
            "Forged host event escaped client ingress");
        Require(Status(a[4]) == "accepted" &&
                Receipt(a[4]).GetProperty("state").GetString() == "stop_pending" &&
                a[4].GetProperty("effect_intents")[0].GetProperty("kind").GetString()
                    == "host_stop_now", "Stale-revision STOP was dropped");
        Require(a[5].GetProperty("replayed").GetBoolean() &&
                !a[5].TryGetProperty("effect_intents", out _) &&
                Receipt(a[4]).GetRawText() == Receipt(a[5]).GetRawText(),
            "STOP replay mutated original receipt or repeated physical intent");
        Require(Status(a[6]) == "operation_id_reused_with_different_payload",
            "Conflicting replay accepted");
        Console.WriteLine("PASS .NET10 -> actual Go CLI: 7 commands, replay/STOP/fake-host/alias assertions");
        Console.WriteLine("Nonproduction: no network, physical audio device, authenticated principal, or trusted host.");
    }
}
