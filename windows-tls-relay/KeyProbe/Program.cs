// Synthetic CI-only A/B probe. Never use an owner's key or certificate store.
using System.Net;
using System.Net.Security;
using System.Net.Sockets;
using System.Security.Authentication;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;

internal static class Program
{
    private static X509Certificate2 Certificate(RSA rsa)
    {
        var request = new CertificateRequest("CN=synthetic.invalid", rsa, HashAlgorithmName.SHA256, RSASignaturePadding.Pkcs1);
        request.CertificateExtensions.Add(new X509BasicConstraintsExtension(false, false, 0, true));
        request.CertificateExtensions.Add(new X509KeyUsageExtension(X509KeyUsageFlags.DigitalSignature, true));
        request.CertificateExtensions.Add(new X509EnhancedKeyUsageExtension(
            new OidCollection { new Oid("1.3.6.1.5.5.7.3.1") }, true));
        var san = new SubjectAlternativeNameBuilder(); san.AddDnsName("localhost");
        request.CertificateExtensions.Add(san.Build());
        return request.CreateSelfSigned(DateTimeOffset.UtcNow.AddMinutes(-5), DateTimeOffset.UtcNow.AddDays(1));
    }

    // Both sides use the same options as the existing synthetic TLS harness.
    // No callback or relaxed certificate/hostname validation.
    private static async Task<bool> Handshake(X509Certificate2 cert, bool named)
    {
        using var limit = new CancellationTokenSource(TimeSpan.FromSeconds(5));
        var listener = new TcpListener(IPAddress.Loopback, 0); listener.Start();
        try
        {
            int port = ((IPEndPoint)listener.LocalEndpoint).Port;
            bool serverAuthenticationFailure = false;
            bool clientFinished = false;
            Task server = Task.Run(async () =>
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
                    Console.WriteLine(named ? "AB-B-SERVER: success" : "AB-A-SERVER: success");
                }
                catch (AuthenticationException)
                {
                    serverAuthenticationFailure = true;
                    Console.WriteLine(named ? "AB-B-SERVER: authentication" : "AB-A-SERVER: authentication");
                    if (named) throw;
                }
            });
            Task client = Task.Run(async () =>
            {
                using var tcp = new TcpClient(AddressFamily.InterNetwork);
                await tcp.ConnectAsync(IPAddress.Loopback, port, limit.Token);
                using var tls = new SslStream(tcp.GetStream());
                try
                {
                    await tls.AuthenticateAsClientAsync(new SslClientAuthenticationOptions
                    {
                        TargetHost = "localhost",
                        CertificateChainPolicy = new X509ChainPolicy
                        {
                            TrustMode = X509ChainTrustMode.CustomRootTrust,
                            CustomTrustStore = { cert },
                            RevocationMode = X509RevocationMode.NoCheck
                        },
                        ApplicationProtocols = new() { SslApplicationProtocol.Http11 }
                    }, limit.Token);
                    clientFinished = true;
                }
                catch (IOException) when (!named) { Console.WriteLine("AB-A-CLIENT: io"); }
                catch (AuthenticationException) when (!named) { Console.WriteLine("AB-A-CLIENT: authentication"); }
            });
            await Task.WhenAll(server, client);
            return named ? clientFinished && !serverAuthenticationFailure : serverAuthenticationFailure && !clientFinished;
        }
        finally { listener.Stop(); }
    }

    [System.Runtime.Versioning.SupportedOSPlatform("windows")]
    private static async Task RunWindows()
    {
        using (var rsa = RSA.Create(2048))
        using (var cert = Certificate(rsa))
        {
            if (!await Handshake(cert, false)) throw new InvalidOperationException();
        }
        Console.WriteLine("AB-A: expected ephemeral server authentication failure observed");

        // Explicit temporary named CurrentUser key on the disposable CI runner.
        // No certificate-store installation, export, trust change or machine key.
        string name = "personal-banking-synthetic-ab-" + Guid.NewGuid().ToString("N");
        var provider = CngProvider.MicrosoftSoftwareKeyStorageProvider;
        CngKey? key = null;
        try
        {
            key = CngKey.Create(CngAlgorithm.Rsa, name, new CngKeyCreationParameters
            {
                Provider = provider,
                KeyCreationOptions = CngKeyCreationOptions.None,
                ExportPolicy = CngExportPolicies.None,
                KeyUsage = CngKeyUsages.Signing,
                Parameters = { new CngProperty("Length", BitConverter.GetBytes(2048), CngPropertyOptions.None) }
            });
            if (key.IsMachineKey || key.IsEphemeral || key.ExportPolicy != CngExportPolicies.None)
                throw new InvalidOperationException();
            using var rsa = new RSACng(key);
            using var cert = Certificate(rsa);
            if (!await Handshake(cert, true)) throw new InvalidOperationException();
        }
        finally
        {
            // Recover by the exclusive name even if Create threw after creating.
            CleanupResult result = Cleanup(() =>
            {
                try { key?.Dispose(); }
                finally
                {
                    if (CngKey.Exists(name, provider, CngKeyOpenOptions.None))
                    {
                        using var owned = CngKey.Open(name, provider, CngKeyOpenOptions.None);
                        owned.Delete();
                    }
                }
            }, () => CngKey.Exists(name, provider, CngKeyOpenOptions.None));
            Console.WriteLine(result switch
            {
                CleanupResult.Absent => "AB-CLEANUP: named key absent",
                CleanupResult.Failed => "AB-CLEANUP: failed",
                _ => "AB-CLEANUP: unknown"
            });
            if (result != CleanupResult.Absent) throw new InvalidOperationException();
        }
        Console.WriteLine("PASS: synthetic Windows key A/B; no trust-store changes");
    }

    private enum CleanupResult { Absent, Failed, Unknown }
    private static CleanupResult Cleanup(Action delete, Func<bool> exists)
    {
        bool deletionFailed = false;
        bool? remains = null;
        try { delete(); }
        catch { deletionFailed = true; }
        finally
        {
            try { remains = exists(); }
            catch { /* Absence is unknown, never a successful cleanup. */ }
        }
        return remains is null ? CleanupResult.Unknown :
            deletionFailed || remains.Value ? CleanupResult.Failed : CleanupResult.Absent;
    }

    private static void CleanupTests()
    {
        int checks = 0;
        void Check(bool value) { if (!value) throw new InvalidOperationException(); checks++; }
        Check(Cleanup(() => { }, () => false) == CleanupResult.Absent);
        Check(Cleanup(() => { }, () => true) == CleanupResult.Failed);
        int existenceCalls = 0;
        Check(Cleanup(() => throw new IOException(), () => { existenceCalls++; return false; }) == CleanupResult.Failed);
        Check(existenceCalls == 1);
        Check(Cleanup(() => { }, () => throw new IOException()) == CleanupResult.Unknown);
        Check(Cleanup(() => throw new IOException(), () => throw new IOException()) == CleanupResult.Unknown);
        // Creation can fail before or after creating the owned name: cleanup
        // still attempts deletion and verifies absence in both states.
        foreach (bool created in new[] { false, true })
        {
            bool present = created;
            int attempts = 0;
            Check(Cleanup(() => { attempts++; present = false; }, () => present) == CleanupResult.Absent);
            Check(attempts == 1);
        }
        if (checks != 10) throw new InvalidOperationException();
        Console.WriteLine("PASS: 10 synthetic cleanup checks");
    }

    private static async Task<int> Main()
    {
        if (Environment.GetEnvironmentVariable("GITHUB_ACTIONS") != "true")
        { Console.Error.WriteLine("FAIL: disposable GitHub Actions runner required"); return 1; }
        if (!OperatingSystem.IsWindows()) { Console.Error.WriteLine("FAIL: Windows-only synthetic probe"); return 1; }
        try { CleanupTests(); await RunWindows(); return 0; }
        catch { Console.Error.WriteLine("FAIL: synthetic key A/B; private diagnostics suppressed"); return 1; }
    }
}
