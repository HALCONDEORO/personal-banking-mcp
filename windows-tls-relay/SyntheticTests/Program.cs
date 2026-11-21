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
    // Harness entry point and fixture creation are deliberately sequential. Do not parallelize
    // fixture allocation without synchronizing both ownership collections and shutdown.
    private static readonly List<string> ownedKeys = new();
    private static readonly List<CngKey> ownedKeyHandles = new();
    private static T TrackBeforeCreate<T>(ICollection<string> names, string name, Func<T> create)
    {
        names.Add(name);
        return create();
    }

    [System.Runtime.Versioning.SupportedOSPlatform("windows")]
    private static RSA WindowsFixtureKey()
    {
        string name = "personal-banking-synthetic-tls-" + Guid.NewGuid().ToString("N");
        // Track BEFORE Create so partial creation is included in final cleanup.
        var key = TrackBeforeCreate(ownedKeys, name, () => CngKey.Create(CngAlgorithm.Rsa, name, new CngKeyCreationParameters
        {
            Provider = CngProvider.MicrosoftSoftwareKeyStorageProvider,
            KeyCreationOptions = CngKeyCreationOptions.None,
            ExportPolicy = CngExportPolicies.None,
            KeyUsage = CngKeyUsages.Signing,
            Parameters = { new CngProperty("Length", BitConverter.GetBytes(2048), CngPropertyOptions.None) }
        }));
        ownedKeyHandles.Add(key); // Retain the original handle until every certificate/task scope has ended.
        if (key.IsMachineKey || key.IsEphemeral || key.ExportPolicy != CngExportPolicies.None)
            throw new InvalidOperationException();
        return new RSACng(key);
    }

    private static bool CleanupOwnedKeys(Action<string> delete, Func<string, bool> exists,
                                         IEnumerable<string> names)
    {
        bool clean = true;
        foreach (string name in names)
        {
            try { delete(name); }
            catch { clean = false; }
            finally
            {
                try { if (exists(name)) clean = false; }
                catch { clean = false; }
            }
        }
        return clean;
    }

    [System.Runtime.Versioning.SupportedOSPlatform("windows")]
    private static bool CleanupWindowsKeys() => CleanupOwnedKeys(name =>
    {
        var provider = CngProvider.MicrosoftSoftwareKeyStorageProvider;
        if (CngKey.Exists(name, provider, CngKeyOpenOptions.None))
        {
            using var key = CngKey.Open(name, provider, CngKeyOpenOptions.None);
            key.Delete();
        }
    }, name => CngKey.Exists(name, CngProvider.MicrosoftSoftwareKeyStorageProvider,
                             CngKeyOpenOptions.None), ownedKeys);

    private static void CleanupPolicyTests()
    {
        int observed = 0;
        if (CleanupOwnedKeys(_ => throw new IOException(), _ => { observed++; return false; }, new[] { "a", "b" }) || observed != 2)
            throw new InvalidOperationException();
        if (CleanupOwnedKeys(_ => { }, _ => throw new IOException(), new[] { "a" }))
            throw new InvalidOperationException();
        if (CleanupOwnedKeys(_ => { }, _ => true, new[] { "a" }))
            throw new InvalidOperationException();
        if (!CleanupOwnedKeys(_ => { }, _ => false, new[] { "before-create", "after-create" }))
            throw new InvalidOperationException();
        foreach (bool createdBeforeFailure in new[] { false, true })
        {
            var names = new List<string>();
            var fakeStore = new HashSet<string>();
            bool creationFailed = false;
            try
            {
                TrackBeforeCreate<int>(names, "synthetic-test", () =>
                {
                    if (createdBeforeFailure) fakeStore.Add("synthetic-test");
                    throw new IOException();
                });
            }
            catch (IOException) { creationFailed = true; }
            finally
            {
                if (!CleanupOwnedKeys(n => { fakeStore.Remove(n); }, fakeStore.Contains, names))
                    throw new InvalidOperationException();
            }
            if (!creationFailed || names.Count != 1 || fakeStore.Count != 0)
                throw new InvalidOperationException();
        }
        Console.WriteLine("CHECK: synthetic fixture cleanup policy checks");
    }
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
                                                int days = 1, bool expired = false, bool ephemeralOnly = false)
    {
        using var rsa = OperatingSystem.IsWindows() && !ephemeralOnly ? WindowsFixtureKey() : RSA.Create(2048);
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
        Console.WriteLine("STEP: client-connect");
        await tcp.ConnectAsync(IPAddress.Loopback, port, limit.Token);
        using var tls = new SslStream(tcp.GetStream()); // No permissive validation callback.
        Console.WriteLine("STEP: client-handshake");
        try { await tls.AuthenticateAsClientAsync(Options(cert, host), limit.Token); }
        catch (AuthenticationException) { Console.WriteLine("HANDSHAKE: authentication"); throw; }
        catch (IOException) { Console.WriteLine("HANDSHAKE: io"); throw; }
        catch (OperationCanceledException) { Console.WriteLine("HANDSHAKE: canceled"); throw; }
        catch { Console.WriteLine("HANDSHAKE: other"); throw; }
        Console.WriteLine("STEP: client-write");
        await tls.WriteAsync(request, limit.Token);
        Console.WriteLine("STEP: client-response");
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
    // Isolated synthetic handshake probe. No relay changes, private diagnostics
    // or validation callback. Observe both tasks before leaving the test.
    private static async Task ServerHandshakeProbe()
    {
        using var cert = Certificate();
        using var limit = new CancellationTokenSource(TimeSpan.FromSeconds(5));
        var listener = new TcpListener(IPAddress.Loopback, 0);
        Task? server = null;
        Task? client = null;
        try
        {
            listener.Start();
            int port = ((IPEndPoint)listener.LocalEndpoint).Port;
            server = Task.Run(async () =>
            {
                try
                {
                    using var tcp = await listener.AcceptTcpClientAsync(limit.Token);
                    using var tls = new SslStream(tcp.GetStream());
                    await tls.AuthenticateAsServerAsync(new SslServerAuthenticationOptions
                    {
                        ServerCertificate = cert,
                        EnabledSslProtocols = SslProtocols.Tls12 | SslProtocols.Tls13,
                        ClientCertificateRequired = false,
                        ApplicationProtocols = new() { SslApplicationProtocol.Http11 },
                        AllowRenegotiation = false
                    }, limit.Token);
                    Console.WriteLine("PROBE-SERVER: success");
                }
                catch (AuthenticationException) { Console.WriteLine("PROBE-SERVER: authentication"); throw; }
                catch (IOException) { Console.WriteLine("PROBE-SERVER: io"); throw; }
                catch (OperationCanceledException) { Console.WriteLine("PROBE-SERVER: canceled"); throw; }
                catch { Console.WriteLine("PROBE-SERVER: other"); throw; }
            });
            client = Task.Run(async () =>
            {
                using var tcp = new TcpClient(AddressFamily.InterNetwork);
                await tcp.ConnectAsync(IPAddress.Loopback, port, limit.Token);
                using var tls = new SslStream(tcp.GetStream());
                await tls.AuthenticateAsClientAsync(Options(cert), limit.Token);
            });
            await Task.WhenAll(server, client);
        }
        finally
        {
            await FinishOwnedWork(() => { try { limit.Cancel(); } finally { listener.Stop(); } }, server, client);
        }
    }
    private sealed class SocketAudit
    {
        internal bool Joined;
        internal bool ListenerClosed;
        internal bool ScopeExited;
    }
    private static async Task NetworkTests(string? fault = null, SocketAudit? audit = null)
    {
        Console.WriteLine("STEP: network-certificate");
        using var cert = Certificate(ephemeralOnly: fault is not null);
        Console.WriteLine("STEP: network-listeners");
        var backend = new TcpListener(IPAddress.Loopback, 0);
        LocalTlsRelay? relay = null;
        using var cancel = new CancellationTokenSource();
        Task? run = null;
        Task? backendTask = null;
        try
        {
            backend.Start();
            if (fault == "setup") throw new IOException();
            int backendPort = ((IPEndPoint)backend.LocalEndpoint).Port;
            relay = new LocalTlsRelay(cert, 0, backendPort, TimeSpan.FromSeconds(1), TimeSpan.FromSeconds(4));
            run = relay.RunAsync(cancel.Token);
            int port = await Port(relay, run);
            backendTask = Task.Run(async () =>
            {
                using var limit = new CancellationTokenSource(TimeSpan.FromSeconds(3));
                Console.WriteLine("STEP: backend-accept");
                using var tcp = await backend.AcceptTcpClientAsync(limit.Token);
                using var stream = tcp.GetStream();
                using var output = new MemoryStream(); await stream.CopyToAsync(output, limit.Token);
                string expected = "GET " + Target + " HTTP/1.1\r\nHost: 127.0.0.1:8766\r\nConnection: close\r\n\r\n";
                Console.WriteLine("STEP: backend-request-check");
                Check(Encoding.ASCII.GetString(output.ToArray()) == expected);
                Console.WriteLine("STEP: backend-response");
                await stream.WriteAsync(LocalTlsRelay.Response(true), limit.Token);
            });
            if (fault is not null)
            {
                if (fault == "early-client") throw new IOException();
                if (fault == "server-cancel") cancel.Cancel();
                if (fault == "server-fault")
                {
                    // Actual relay accepts a loopback peer that closes without completing TLS.
                    using var brokenPeer = new TcpClient(AddressFamily.InterNetwork);
                    await brokenPeer.ConnectAsync(IPAddress.Loopback, port);
                }
                await run; // The injected server failure/cancellation must remain a failure.
                throw new InvalidOperationException();
            }
            byte[] response = await Client(port, cert, Request(headers: "Host: localhost:8765\r\nCookie: discarded=synthetic\r\n"));
            Console.WriteLine("STEP: network-join");
            await Task.WhenAll(run, backendTask);
            Console.WriteLine("STEP: network-response-check");
            Check(response.SequenceEqual(LocalTlsRelay.Response(true))); Check(relay.BoundPort == 0);
            Console.WriteLine("STEP: network-cleanup-check");
            using var probe = new TcpClient();
            try { await probe.ConnectAsync(IPAddress.Loopback, port); throw new Exception("Listener remained open"); }
            catch (SocketException) { passed++; }
            await ExpectStopped(relay.RunAsync(CancellationToken.None));
            Check(relay.ToString() == "<LocalTlsRelay private>");
        }
        finally
        {
            try
            {
                await FinishOwnedWork(() => { try { cancel.Cancel(); } finally { backend.Stop(); } }, run, backendTask);
            }
            finally
            {
                if (audit is not null)
                {
                    audit.Joined = (run is null || run.IsCompleted) && (backendTask is null || backendTask.IsCompleted);
                    audit.ListenerClosed = backend.Server?.IsBound != true && (relay is null || relay.BoundPort == 0);
                }
                relay?.Dispose();
                if (audit is not null) audit.ScopeExited = true;
            }
        }
    }
    // Only used after normal-path assertions/awaits, or while propagating their failure.
    // Observe completion before leaving relay/certificate scopes; never turn a test failure green.
    private static async Task FinishOwnedWork(Action stop, params Task?[] tasks)
    {
        try { stop(); }
        finally { await ObserveFinished(tasks); }
    }
    private static async Task ObserveFinished(params Task?[] tasks)
    {
        foreach (Task? task in tasks)
        {
            if (task is null) continue;
            try { await task; } catch { /* The original test outcome is preserved. */ }
        }
    }
    private static async Task RejectionTests()
    {
        foreach (string mode in new[] { "malformed", "backend-unavailable", "backend-untrusted", "backend-slow", "slow-header", "wrong-hostname", "slow-handshake", "cancel", "dispose", "idle" })
        {
            using var cert = Certificate();
            var backend = new TcpListener(IPAddress.Loopback, 0);
            LocalTlsRelay? relay = null;
            using var cancel = new CancellationTokenSource();
            Task? run = null;
            Task? responder = null;
            try
            {
                backend.Start();
                int backendPort = ((IPEndPoint)backend.LocalEndpoint).Port;
                if (mode == "backend-unavailable") backend.Stop();
                relay = new LocalTlsRelay(cert, 0, backendPort, TimeSpan.FromMilliseconds(250), TimeSpan.FromMilliseconds(750));
                run = relay.RunAsync(cancel.Token);
                int port = await Port(relay, run);
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
                    responder = mode is not ("backend-untrusted" or "backend-slow") ? null : Task.Run(async () =>
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
            finally
            {
                try { await FinishOwnedWork(() => { try { cancel.Cancel(); } finally { backend.Stop(); } }, run, responder); }
                finally { relay?.Dispose(); }
            }
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
            Task run = relay.RunAsync(deadline.Token);
            try
            {
                int port = await Port(relay, run);
                byte[] response = await Client(port, cert, Request(target));
                await run; await child.WaitForExitAsync(deadline.Token);
                Check(child.ExitCode == 0);
                Check(response.SequenceEqual(LocalTlsRelay.Response(!denial)));
                Check(relay.BoundPort == 0);
            }
            finally
            {
                await FinishOwnedWork(deadline.Cancel, run);
            }
        }
        finally
        {
            try { if (!child.HasExited) child.Kill(true); }
            finally { await child.WaitForExitAsync(); }
        }
    }
    private static async Task SocketFaultTests()
    {
        foreach (string fault in new[] { "setup", "early-client", "server-fault", "server-cancel" })
        {
            var audit = new SocketAudit();
            bool failed = false;
            try { await NetworkTests(fault, audit); }
            catch (IOException) { failed = true; }
            catch (RelayRejectedException) { failed = true; }
            // NetworkTests has returned through its certificate using scope before this assertion.
            if (!failed || !audit.Joined || !audit.ListenerClosed || !audit.ScopeExited)
                throw new InvalidOperationException();
        }
        Console.WriteLine("CHECK: loopback socket fault paths joined and closed");
    }
    private static async Task LifecyclePolicyTests()
    {
        foreach (string mode in new[] { "early-client-failure", "cancel", "server-failure", "cleanup-failure" })
        {
            using var cancel = new CancellationTokenSource();
            var release = new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);
            using var registration = cancel.Token.Register(() => release.TrySetResult(true));
            int active = 0;
            bool fixtureDisposed = false;
            async Task Worker(bool fail)
            {
                Interlocked.Increment(ref active);
                try
                {
                    await release.Task;
                    if (fail) throw new IOException();
                }
                finally { Interlocked.Decrement(ref active); }
            }
            Task server = Worker(mode == "server-failure");
            Task client = Worker(false);
            bool originalFailed = false;
            try
            {
                try
                {
                    if (mode == "early-client-failure") throw new IOException();
                    if (mode == "cancel") throw new OperationCanceledException();
                    release.TrySetResult(true);
                    await Task.WhenAll(server, client);
                }
                finally { await FinishOwnedWork(cancel.Cancel, server, client); }
            }
            catch (IOException) { originalFailed = true; }
            catch (OperationCanceledException) { originalFailed = true; }
            finally { fixtureDisposed = true; } // Model the outer certificate/RSA using scope.
            bool orderCorrect = false;
            bool clean = CleanupOwnedKeys(_ =>
            {
                orderCorrect = fixtureDisposed && active == 0 && server.IsCompleted && client.IsCompleted;
                if (!orderCorrect || mode == "cleanup-failure") throw new IOException();
            }, _ => false, new[] { "synthetic-lifecycle" });
            if (!orderCorrect || originalFailed != (mode != "cleanup-failure") || clean != (mode != "cleanup-failure"))
                throw new InvalidOperationException();
        }
        Console.WriteLine("CHECK: fixture lifecycle failure paths observed");
    }

    private static async Task<int> Main(string[] args)
    {
        if (OperatingSystem.IsWindows() && Environment.GetEnvironmentVariable("GITHUB_ACTIONS") != "true")
        { Console.Error.WriteLine("FAIL: disposable GitHub Actions runner required"); return 1; }
        if (args.Length != 0)
        {
            if (args.Length != 1 || args[0] != "--socket-faults-only") return 1;
            try { await SocketFaultTests(); return 0; }
            catch { Console.Error.WriteLine("FAIL: synthetic socket fault tests"); return 1; }
        }
        int status = 1;
        try
        {
            CleanupPolicyTests();
            await LifecyclePolicyTests();
            await SocketFaultTests();
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
            Console.WriteLine("PHASE: server-handshake-probe");
            await ServerHandshakeProbe();
            Console.WriteLine("PHASE: network");
            await NetworkTests();
            Console.WriteLine("PHASE: rejection");
            await RejectionTests();
            Console.WriteLine("PHASE: python-join-success");
            await PythonJoinTest();
            Console.WriteLine("PHASE: python-join-denial");
            await PythonJoinTest(true);
            status = 0;
        }
        catch { Console.Error.WriteLine("FAIL: synthetic TLS harness. Private diagnostics suppressed."); }
        finally
        {
            if (OperatingSystem.IsWindows())
            {
                bool handlesClosed = true;
                foreach (var key in ownedKeyHandles)
                {
                    try { key.Dispose(); }
                    catch { handlesClosed = false; }
                }
                bool keysAbsent = CleanupWindowsKeys(); // Still attempt every deletion if a handle close failed.
                if (handlesClosed && keysAbsent) Console.WriteLine("TLS-CLEANUP: all named keys absent");
                else { Console.Error.WriteLine("TLS-CLEANUP: failed or unknown"); status = 1; }
            }
        }
        if (status == 0)
            Console.WriteLine($"PASS: {passed} synthetic assertions. No bank/provider/trust-store changes.");
        return status;
    }
}
