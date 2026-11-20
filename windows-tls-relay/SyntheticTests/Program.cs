// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Marco Antonio Tevar Asensio
// No bank traffic or persisted certificate. Keys/callbacks below are synthetic.
using System.Diagnostics;
using System.Text.Json;
using System.Net;
using System.Net.Security;
using System.Net.Sockets;
using System.Security.Authentication;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Text;
using PersonalBanking.LocalTls;

internal static class Program
{
    private static int passed;
    private const string Target = "/callback?state=SYNTHETIC-STATE&code=SYNTHETIC-CODE";
    private static byte[] Request(string target = Target, string headers = "Host: localhost:8765\r\n") =>
        Encoding.ASCII.GetBytes("GET " + target + " HTTP/1.1\r\n" + headers + "\r\n");
    private static void Check(bool condition) { if (!condition) throw new Exception("Synthetic assertion failed"); passed++; }
    private static void Reject(Action action)
    {
        try { action(); } catch (RelayRejectedException e) { Check(e.Message == "Local TLS relay stopped"); return; }
        throw new Exception("Expected generic rejection");
    }
    private static X509Certificate2 Certificate(bool ca = false, string dns = "localhost", bool eku = true,
                                                int days = 1, bool expired = false)
    {
        using var rsa = RSA.Create(2048);
        var request = new CertificateRequest("CN=synthetic.invalid", rsa, HashAlgorithmName.SHA256, RSASignaturePadding.Pkcs1);
        request.CertificateExtensions.Add(new X509BasicConstraintsExtension(ca, false, 0, true));
        request.CertificateExtensions.Add(new X509KeyUsageExtension(X509KeyUsageFlags.DigitalSignature, true));
        if (eku) request.CertificateExtensions.Add(new X509EnhancedKeyUsageExtension(
            new OidCollection { new Oid("1.3.6.1.5.5.7.3.1") }, true));
        var san = new SubjectAlternativeNameBuilder(); san.AddDnsName(dns);
        request.CertificateExtensions.Add(san.Build());
        var start = DateTimeOffset.UtcNow.AddMinutes(-5);
        return request.CreateSelfSigned(expired ? start.AddDays(-3) : start,
            expired ? start.AddDays(-2) : start.AddDays(days));
    }
    private static void ParserTests()
    {
        Check(LocalTlsRelay.ParseBrowserRequest(Request()) == Target);
        Check(LocalTlsRelay.ParseBrowserRequest(Request(headers: "Host: localhost:8765\r\nUser-Agent: synthetic\r\nCookie: synthetic=discarded\r\n")) == Target);
        Check(LocalTlsRelay.ParseBrowserRequest(Request("/callback?state=SYNTHETIC-STATE&error=denied&error_description=synthetic" )).Contains("error=denied"));
        foreach (string target in new[] { "https://localhost:8765" + Target, "//localhost/callback?state=s&code=c", "/wrong?state=s&code=c",
            "/callback?state=s&state=s&code=c", "/callback?state=s&%63ode=c&code=c", "/callback?state=s&code=c&error=e",
            "/callback?state=s&code=", "/callback?state=s&code=%FF", "/callback?state=s&code=%", "/callback?state=s&code=%0D%0A",
            "/callback?state=s&code=c#fragment", "/callback?state=s&code=c&unknown=x", "/callback?state=s&error_description=e",
            "/callback?state=s&code=c\\suffix", "/callback?state=s&code=" + new string('a', 4097) })
            Reject(() => LocalTlsRelay.ParseBrowserRequest(Request(target)));
        foreach (string headers in new[] { "Host: 127.0.0.1:8765\r\n", "Host: localhost:8765\r\nHost: localhost:8765\r\n",
            "Host : localhost:8765\r\n", "Host: localhost:8765\r\nContent-Length: 0\r\n", "Host: localhost:8765\r\nTransfer-Encoding: chunked\r\n",
            "Host: localhost:8765\r\n folded\r\n", "Host: localhost:8765\r\nAuthorization: synthetic\r\n",
            "Host: localhost:8765\r\nX-Forwarded-Host: synthetic.invalid\r\n", "Host: localhost:8765\r\nOrigin: https://other.invalid\r\n",
            "Host: localhost:8765\r\nUpgrade: websocket\r\n", "" })
            Reject(() => LocalTlsRelay.ParseBrowserRequest(Request(headers: headers)));
        Reject(() => LocalTlsRelay.ParseBrowserRequest(Encoding.ASCII.GetBytes("POST " + Target + " HTTP/1.1\r\nHost: localhost:8765\r\n\r\n")));
        Reject(() => LocalTlsRelay.ParseBrowserRequest(Request().Concat(Encoding.ASCII.GetBytes("body")).ToArray()));
        Reject(() => LocalTlsRelay.ParseBrowserRequest(Request().Concat(Request()).ToArray()));
        Reject(() => LocalTlsRelay.ParseBrowserRequest(new byte[12289]));
        Check(!Encoding.ASCII.GetString(LocalTlsRelay.Response(true)).Contains("SYNTHETIC"));
        Check(Encoding.ASCII.GetString(LocalTlsRelay.Response(true)).Contains("Bank session is not confirmed"));
    }
    private static async Task<int> Port(LocalTlsRelay relay, Task running)
    {
        using var deadline = new CancellationTokenSource(TimeSpan.FromSeconds(3));
        while (relay.BoundPort == 0)
        {
            if (running.IsCompleted) await running;
            await Task.Delay(1, deadline.Token);
        }
        return relay.BoundPort;
    }
    private static SslClientAuthenticationOptions Options(X509Certificate2 cert, string host = "localhost") => new()
    {
        TargetHost = host,
        CertificateChainPolicy = new X509ChainPolicy
        {
            TrustMode = X509ChainTrustMode.CustomRootTrust,
            CustomTrustStore = { cert },
            RevocationMode = X509RevocationMode.NoCheck // Ephemeral synthetic leaf has no CRL/OCSP.
        },
        ApplicationProtocols = new() { SslApplicationProtocol.Http11 }
    };
    private static async Task<byte[]> Client(int port, X509Certificate2 cert, byte[] request, string host = "localhost")
    {
        using var limit = new CancellationTokenSource(TimeSpan.FromSeconds(3));
        using var tcp = new TcpClient(AddressFamily.InterNetwork);
        await tcp.ConnectAsync(IPAddress.Loopback, port, limit.Token);
        using var tls = new SslStream(tcp.GetStream()); // No permissive validation callback.
        await tls.AuthenticateAsClientAsync(Options(cert, host), limit.Token);
        await tls.WriteAsync(request, limit.Token);
        using var output = new MemoryStream();
        var buffer = new byte[1024];
        while (true)
        {
            int count = await tls.ReadAsync(buffer, limit.Token);
            if (count == 0) return output.ToArray();
            await output.WriteAsync(buffer.AsMemory(0, count), limit.Token);
        }
    }
    private static async Task ExpectStopped(Task run)
    {
        try { await run; } catch (RelayRejectedException e) { Check(e.Message == "Local TLS relay stopped"); return; }
        throw new Exception("Expected bounded shutdown");
    }
    private static async Task NetworkTests()
    {
        using var cert = Certificate();
        var backend = new TcpListener(IPAddress.Loopback, 0); backend.Start();
        int backendPort = ((IPEndPoint)backend.LocalEndpoint).Port;
        using var relay = new LocalTlsRelay(cert, 0, backendPort, TimeSpan.FromSeconds(1), TimeSpan.FromSeconds(4));
        Task run = relay.RunAsync(CancellationToken.None); int port = await Port(relay, run);
        var backendTask = Task.Run(async () =>
        {
            using var limit = new CancellationTokenSource(TimeSpan.FromSeconds(3));
            using var tcp = await backend.AcceptTcpClientAsync(limit.Token);
            using var stream = tcp.GetStream();
            using var output = new MemoryStream(); await stream.CopyToAsync(output, limit.Token);
            string expected = "GET " + Target + " HTTP/1.1\r\nHost: 127.0.0.1:8766\r\nConnection: close\r\n\r\n";
            Check(Encoding.ASCII.GetString(output.ToArray()) == expected);
            await stream.WriteAsync(LocalTlsRelay.Response(true), limit.Token);
        });
        byte[] response = await Client(port, cert, Request(headers: "Host: localhost:8765\r\nCookie: discarded=synthetic\r\n"));
        await Task.WhenAll(run, backendTask); backend.Stop();
        Check(response.SequenceEqual(LocalTlsRelay.Response(true))); Check(relay.BoundPort == 0);
        using var probe = new TcpClient();
        try { await probe.ConnectAsync(IPAddress.Loopback, port); throw new Exception("Listener remained open"); }
        catch (SocketException) { passed++; }
        await ExpectStopped(relay.RunAsync(CancellationToken.None));
        Check(relay.ToString() == "<LocalTlsRelay private>");
    }
    private static async Task RejectionTests()
    {
        foreach (string mode in new[] { "malformed", "backend-unavailable", "backend-untrusted", "backend-slow", "slow-header", "wrong-hostname", "slow-handshake", "cancel", "dispose", "idle" })
        {
            using var cert = Certificate();
            var backend = new TcpListener(IPAddress.Loopback, 0); backend.Start();
            int backendPort = ((IPEndPoint)backend.LocalEndpoint).Port;
            if (mode == "backend-unavailable") backend.Stop();
            using var relay = new LocalTlsRelay(cert, 0, backendPort, TimeSpan.FromMilliseconds(250), TimeSpan.FromMilliseconds(750));
            using var cancel = new CancellationTokenSource();
            Task run = relay.RunAsync(cancel.Token); int port = await Port(relay, run);
            try
            {
                if (mode is "cancel" or "dispose" or "idle")
                {
                    if (mode == "cancel") cancel.Cancel();
                    if (mode == "dispose") relay.Dispose();
                    await ExpectStopped(run);
                }
                else if (mode == "slow-handshake")
                {
                    using var tcp = new TcpClient(); await tcp.ConnectAsync(IPAddress.Loopback, port);
                    await ExpectStopped(run);
                }
                else if (mode == "wrong-hostname")
                {
                    try { await Client(port, cert, Request(), "wrong.invalid"); throw new Exception("Name mismatch accepted"); }
                    catch (AuthenticationException) { passed++; }
                    await ExpectStopped(run);
                }
                else
                {
                    Task? responder = mode is not ("backend-untrusted" or "backend-slow") ? null : Task.Run(async () =>
                    {
                        using var limit = new CancellationTokenSource(TimeSpan.FromSeconds(2));
                        using var tcp = await backend.AcceptTcpClientAsync(limit.Token);
                        using var stream = tcp.GetStream(); await stream.CopyToAsync(Stream.Null, limit.Token);
                        if (mode == "backend-slow") await Task.Delay(500, limit.Token);
                        else await stream.WriteAsync(Encoding.ASCII.GetBytes("HTTP/1.1 200 OK\r\n\r\nSYNTHETIC-PRIVATE-BACKEND"), limit.Token);
                    });
                    var response = await Client(port, cert, mode == "malformed" ? Request("/bad") :
                        mode == "slow-header" ? Encoding.ASCII.GetBytes("GET ") : Request());
                    await run; if (responder is not null) await responder;
                    Check(response.SequenceEqual(LocalTlsRelay.Response(false)));
                }
                Check(relay.BoundPort == 0);
            }
            finally { backend.Stop(); }
        }
    }
    private static async Task PythonJoinTest(bool denial = false)
    {
        string fixture = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,
            "../../../../SyntheticTests/python_receiver_fixture.py"));
        var start = new ProcessStartInfo(OperatingSystem.IsWindows() ? "python" : "python3")
        { RedirectStandardOutput = true, RedirectStandardError = true, UseShellExecute = false };
        start.ArgumentList.Add(fixture);
        if (denial) start.ArgumentList.Add("denial");
        using var child = Process.Start(start) ?? throw new Exception("Synthetic child unavailable");
        try
        {
            using var deadline = new CancellationTokenSource(TimeSpan.FromSeconds(12));
            string line = await child.StandardOutput.ReadLineAsync(deadline.Token) ?? "";
            using var metadata = JsonDocument.Parse(line);
            int backendPort = metadata.RootElement.GetProperty("port").GetInt32();
            string target = metadata.RootElement.GetProperty("target").GetString() ?? "";
            using var cert = Certificate();
            using var relay = new LocalTlsRelay(cert, 0, backendPort, TimeSpan.FromSeconds(2), TimeSpan.FromSeconds(5));
            Task run = relay.RunAsync(deadline.Token); int port = await Port(relay, run);
            byte[] response = await Client(port, cert, Request(target));
            await run; await child.WaitForExitAsync(deadline.Token);
            Check(child.ExitCode == 0);
            Check(response.SequenceEqual(LocalTlsRelay.Response(!denial)));
            Check(relay.BoundPort == 0);
        }
        finally { if (!child.HasExited) { child.Kill(true); await child.WaitForExitAsync(); } }
    }
    private static async Task<int> Main()
    {
        try
        {
            Console.WriteLine("PHASE: parser");
            ParserTests();
            Console.WriteLine("PHASE: leaf-policy");
            using (var valid = Certificate()) { LocalTlsRelay.ValidateLeaf(valid); passed++; }
            using (var ca = Certificate(ca:true)) Reject(() => LocalTlsRelay.ValidateLeaf(ca));
            using (var san = Certificate(dns:"other.invalid")) Reject(() => LocalTlsRelay.ValidateLeaf(san));
            using (var eku = Certificate(eku:false)) Reject(() => LocalTlsRelay.ValidateLeaf(eku));
            using (var longLife = Certificate(days:32)) Reject(() => LocalTlsRelay.ValidateLeaf(longLife));
            using (var expired = Certificate(expired:true)) Reject(() => LocalTlsRelay.ValidateLeaf(expired));
            Reject(() => LocalTlsRelay.FromCurrentUserStore("invalid"));
            if (!OperatingSystem.IsWindows()) Reject(() => LocalTlsRelay.FromCurrentUserStore(new string('A',40)));
            Console.WriteLine("PHASE: network");
            await NetworkTests();
            Console.WriteLine("PHASE: rejection");
            await RejectionTests();
            Console.WriteLine("PHASE: python-join-success");
            await PythonJoinTest();
            Console.WriteLine("PHASE: python-join-denial");
            await PythonJoinTest(true);
            Console.WriteLine($"PASS: {passed} synthetic assertions. No bank/provider/store changes."); return 0;
        }
        catch { Console.Error.WriteLine("FAIL: synthetic TLS harness. Private diagnostics suppressed."); return 1; }
    }
}
