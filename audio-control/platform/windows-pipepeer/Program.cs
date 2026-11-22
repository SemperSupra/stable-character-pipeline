// Windows-only kernel-origin named-pipe peer identity witness. No audio devices,
// client-supplied authority, network service or physical STOP capability.
using System.Diagnostics;
using System.IO.Pipes;
using System.Runtime.InteropServices;
using System.Security.Principal;
using System.Text.Json;
using Microsoft.Win32.SafeHandles;

static class Program
{
    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool GetNamedPipeClientProcessId(SafePipeHandle pipe, out uint clientPid);

    private static void Require(bool ok, string why)
    {
        if (!ok) throw new InvalidOperationException(why);
    }

    private static async Task<int> Child(string name)
    {
        using var client = new NamedPipeClientStream(".", name, PipeDirection.Out,
            PipeOptions.Asynchronous, TokenImpersonationLevel.Impersonation);
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(10));
        await client.ConnectAsync(cts.Token);
        using var writer = new StreamWriter(client) { AutoFlush = true };
        // Deliberately malicious host event identity; the privileged server
        // must ignore these claims and use the OS authenticated client token.
        await writer.WriteLineAsync(
            "{\"action\":\"host_stopped\",\"host_authorized\":true," +
            "\"principal_id\":\"claimed_admin\",\"pid\":987654321,\"sid\":\"S-1-5-18\"}");
        return 0;
    }

    private static async Task Main(string[] args)
    {
        Require(OperatingSystem.IsWindows(), "Windows kernel peer test requires Windows");
        if (args.Length == 2 && args[0] == "--child")
        {
            Environment.ExitCode = await Child(args[1]);
            return;
        }
        Require(args.Length == 0, "unexpected command line");
        var pipeName = "aural-synthetic-peer-" + Guid.NewGuid().ToString("N");
        await using var server = new NamedPipeServerStream(pipeName, PipeDirection.In, 1,
            PipeTransmissionMode.Byte, PipeOptions.Asynchronous);
        var childDll = typeof(Program).Assembly.Location;
        var start = new ProcessStartInfo("dotnet")
        {
            UseShellExecute = false,
            RedirectStandardError = true,
            RedirectStandardOutput = true,
            CreateNoWindow = true
        };
        start.ArgumentList.Add(childDll);
        start.ArgumentList.Add("--child");
        start.ArgumentList.Add(pipeName);
        using var child = Process.Start(start)
            ?? throw new InvalidOperationException("subprocess could not launch");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(15));
        await server.WaitForConnectionAsync(cts.Token);
        Require(GetNamedPipeClientProcessId(server.SafePipeHandle, out var kernelPid),
            "kernel GetNamedPipeClientProcessId failed: " + Marshal.GetLastWin32Error());
        Require(kernelPid == (uint)child.Id,
            "host peer PID must equal actual child process, not JSON claim");
        Require(kernelPid != 987654321, "forged JSON process identity accepted");

        // With the client's impersonation level explicitly set, Windows
        // supplies the real client token to RunAsClient, not caller JSON.
        string? kernelSid = null;
        server.RunAsClient(() => kernelSid = WindowsIdentity.GetCurrent().User?.Value);
        Require(!string.IsNullOrWhiteSpace(kernelSid), "missing impersonated client SID");
        Require(kernelSid != "S-1-5-18", "forged SYSTEM sid must not control host authority");
        using var reader = new StreamReader(server);
        var message = await reader.ReadLineAsync(cts.Token);
        Require(message != null, "no child JSON payload");
        using var document = JsonDocument.Parse(message);
        Require(document.RootElement.GetProperty("pid").GetInt64() == 987654321,
            "negative fixture missing forged process ID");
        Require(document.RootElement.GetProperty("sid").GetString() == "S-1-5-18",
            "negative fixture missing forged SYSTEM SID");
        Require(document.RootElement.GetProperty("host_authorized").GetBoolean(),
            "negative fixture missing forged host permission");
        await child.WaitForExitAsync(cts.Token);
        Require(child.ExitCode == 0,
            "child failed: " + await child.StandardError.ReadToEndAsync(cts.Token));
        Console.WriteLine("PASS native Windows NamedPipeClientProcessId + RunAsClient SID; " +
            "actual child PID/OS identity overrides forged client JSON. No audio device.");
        Console.WriteLine("LIMIT: same-user peer, PID reuse, pipe ACLs, host lease and physical STOP unqualified.");
    }
}
