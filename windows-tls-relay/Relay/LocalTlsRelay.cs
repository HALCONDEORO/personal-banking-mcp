// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Marco Antonio Tevar Asensio
using System.Net;
using System.Net.Security;
using System.Net.Sockets;
using System.Security.Authentication;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Text;

namespace PersonalBanking.LocalTls;

// No CLI, provider transport, certificate installation, logging or MCP exposure.
// The only executable in this directory is a synthetic test harness.
public sealed class RelayRejectedException : Exception
{
    public RelayRejectedException() : base("Local TLS relay stopped") { }
}

public sealed class LocalTlsRelay : IDisposable
{
    internal const string Origin = "https://localhost:8765";
    private const int MaxRequest = 12288;
    private readonly X509Certificate2 certificate;
    private readonly int listenPort;
    private readonly int backendPort;
    private readonly TimeSpan phaseLimit;
    private readonly TimeSpan lifetime;
    private readonly CancellationTokenSource stop = new();
    private int started;
    private int disposed;

    private LocalTlsRelay(X509Certificate2 certificate)
        : this(certificate, 8765, 8766, TimeSpan.FromSeconds(2), TimeSpan.FromMinutes(5)) { }

    // Test-only port/deadline substitution. Never a generic proxy destination.
    internal LocalTlsRelay(X509Certificate2 certificate, int listenPort, int backendPort,
                           TimeSpan phaseLimit, TimeSpan lifetime)
    {
        ValidateLeaf(certificate);
        if (listenPort < 0 || listenPort > 65535 || backendPort < 1 || backendPort > 65535 ||
            phaseLimit <= TimeSpan.Zero || phaseLimit > TimeSpan.FromSeconds(2) ||
            lifetime <= TimeSpan.Zero || lifetime > TimeSpan.FromMinutes(5)) throw new RelayRejectedException();
        this.certificate = certificate;
        this.listenPort = listenPort; this.backendPort = backendPort;
        this.phaseLimit = phaseLimit; this.lifetime = lifetime;
    }

    // Opens an existing store READ ONLY. No import, generation, trust changes or export.
    // Caller owns certificate trust approval; this checks custody, not browser trust.
    public static LocalTlsRelay FromCurrentUserStore(string exactThumbprint)
    {
        if (!OperatingSystem.IsWindows() || exactThumbprint is null || exactThumbprint.Length != 40 ||
            exactThumbprint.Any(c => !Uri.IsHexDigit(c))) throw new RelayRejectedException();
        X509Certificate2? chosen = null;
        try
        {
            using var store = new X509Store(StoreName.My, StoreLocation.CurrentUser);
            store.Open(OpenFlags.ReadOnly | OpenFlags.OpenExistingOnly);
            foreach (var candidate in store.Certificates)
            {
                if (string.Equals(candidate.Thumbprint, exactThumbprint, StringComparison.OrdinalIgnoreCase))
                {
                    if (chosen is not null) { candidate.Dispose(); throw new RelayRejectedException(); }
                    chosen = candidate;
                }
                else candidate.Dispose();
            }
            if (chosen is null) throw new RelayRejectedException();
            using var key = chosen.GetRSAPrivateKey();
            if (key is not RSACng native || native.Key.IsMachineKey ||
                native.Key.ExportPolicy != CngExportPolicies.None) throw new RelayRejectedException();
            var result = new LocalTlsRelay(chosen); chosen = null;
            return result;
        }
        catch { throw new RelayRejectedException(); }
        finally { chosen?.Dispose(); }
    }

    internal static void ValidateLeaf(X509Certificate2 cert)
    {
        try
        {
            var now = DateTime.UtcNow;
            if (!cert.HasPrivateKey || cert.NotBefore.ToUniversalTime() > now ||
                cert.NotAfter.ToUniversalTime() <= now ||
                cert.NotAfter.ToUniversalTime() - cert.NotBefore.ToUniversalTime() > TimeSpan.FromDays(31))
                throw new RelayRejectedException();
            var constraints = cert.Extensions.OfType<X509BasicConstraintsExtension>().ToArray();
            var usages = cert.Extensions.OfType<X509EnhancedKeyUsageExtension>().ToArray();
            var keys = cert.Extensions.OfType<X509KeyUsageExtension>().ToArray();
            var sans = cert.Extensions.OfType<X509SubjectAlternativeNameExtension>().ToArray();
            if (constraints.Length != 1 || constraints[0].CertificateAuthority || usages.Length != 1 ||
                !usages[0].EnhancedKeyUsages.Cast<Oid>().Any(o => o.Value == "1.3.6.1.5.5.7.3.1") ||
                keys.Length != 1 || (keys[0].KeyUsages & X509KeyUsageFlags.DigitalSignature) == 0 ||
                sans.Length != 1 || !sans[0].EnumerateDnsNames().SequenceEqual(new[] { "localhost" }) ||
                sans[0].EnumerateIPAddresses().Any()) throw new RelayRejectedException();
        }
        catch { throw new RelayRejectedException(); }
    }

    public override string ToString() => "<LocalTlsRelay private>";

    // One TCP connection only, including malformed traffic or a failed handshake.
    // Caller must start the independent admin receiver first and close it afterwards.
    public async Task RunAsync(CancellationToken cancellationToken)
    {
        if (Volatile.Read(ref disposed) != 0 || Interlocked.Exchange(ref started, 1) != 0)
            throw new RelayRejectedException();
        using var total = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken, stop.Token);
        total.CancelAfter(lifetime);
        var listener = new TcpListener(IPAddress.Loopback, listenPort);
        try
        {
            listener.Start(1);
            BoundPort = ((IPEndPoint)listener.LocalEndpoint).Port;
            using var client = await listener.AcceptTcpClientAsync(total.Token);
            listener.Stop(); // Close accept socket before doing any private work.
            using var tls = new SslStream(client.GetStream(), false);
            using (var phase = Phase(total.Token))
                await tls.AuthenticateAsServerAsync(new SslServerAuthenticationOptions
                {
                    ServerCertificate = certificate,
                    EnabledSslProtocols = SslProtocols.Tls12 | SslProtocols.Tls13,
                    ClientCertificateRequired = false,
                    ApplicationProtocols = new() { SslApplicationProtocol.Http11 },
                    AllowRenegotiation = false
                }, phase.Token);
            bool accepted = false;
            try
            {
                using var phase = Phase(total.Token);
                var raw = await ReadHeaders(tls, phase.Token);
                var target = ParseBrowserRequest(raw);
                accepted = await Forward(target, total.Token);
            }
            catch { /* Fixed rejection page only. Never exception or URL text. */ }
            using (var phase = Phase(total.Token))
                await tls.WriteAsync(Response(accepted), phase.Token);
        }
        catch { throw new RelayRejectedException(); }
        finally { listener.Stop(); BoundPort = 0; }
    }
    internal int BoundPort { get; private set; }
    private CancellationTokenSource Phase(CancellationToken total)
    {
        var source = CancellationTokenSource.CreateLinkedTokenSource(total);
        source.CancelAfter(phaseLimit); return source;
    }
    private static async Task<byte[]> ReadHeaders(Stream stream, CancellationToken token)
    {
        // Read one byte at a time to avoid forwarding buffered body/pipeline bytes.
        // HTTP bodies are forbidden; extra bytes are never processed as another request.
        var buffer = new byte[MaxRequest]; var size = 0;
        while (size < buffer.Length)
        {
            if (await stream.ReadAsync(buffer.AsMemory(size, 1), token) == 0) throw new RelayRejectedException();
            size++;
            if (size >= 4 && buffer[size-4] == 13 && buffer[size-3] == 10 && buffer[size-2] == 13 && buffer[size-1] == 10)
                return buffer[..size];
        }
        throw new RelayRejectedException();
    }
    internal static string ParseBrowserRequest(byte[] raw)
    {
        try
        {
            if (raw.Length == 0 || raw.Length > MaxRequest || raw.Any(c => c > 126 || (c < 32 && c != 13 && c != 10)))
                throw new RelayRejectedException();
            string text = Encoding.ASCII.GetString(raw);
            if (!text.EndsWith("\r\n\r\n", StringComparison.Ordinal)) throw new RelayRejectedException();
            var lines = text[..^4].Split("\r\n");
            var request = lines[0].Split(' ');
            if (request.Length != 3 || request[0] != "GET" || request[2] != "HTTP/1.1") throw new RelayRejectedException();
            string target = request[1];
            if (!target.StartsWith("/callback?", StringComparison.Ordinal) || target.Length + Origin.Length > 8192 ||
                target.Contains('#') || target.Contains('\\') || target.Any(c => c < 33 || c > 126)) throw new RelayRejectedException();
            var headers = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            foreach (string line in lines.Skip(1))
            {
                int colon = line.IndexOf(':');
                if (colon < 1 || !line[..colon].All(IsToken) || line[(colon+1)..].Any(c => c < 32 || c > 126) ||
                    !headers.TryAdd(line[..colon], line[(colon+1)..].Trim(' '))) throw new RelayRejectedException();
            }
            if (!headers.TryGetValue("Host", out var host) || host != "localhost:8765" ||
                headers.ContainsKey("Content-Length") || headers.ContainsKey("Transfer-Encoding") ||
                headers.ContainsKey("Expect") || headers.ContainsKey("Upgrade") ||
                headers.ContainsKey("Authorization") || headers.ContainsKey("Proxy-Authorization") ||
                headers.Keys.Any(k => k.StartsWith("X-Forwarded-", StringComparison.OrdinalIgnoreCase)) ||
                headers.ContainsKey("Forwarded") ||
                (headers.TryGetValue("Origin", out var origin) && origin != Origin)) throw new RelayRejectedException();
            var pairs = target[10..].Split('&');
            if (pairs.Length < 2 || pairs.Length > 3) throw new RelayRejectedException();
            var data = new Dictionary<string, string>(StringComparer.Ordinal);
            foreach (string pair in pairs)
            {
                int equal = pair.IndexOf('=');
                if (equal < 1) throw new RelayRejectedException();
                string key = Decode(pair[..equal]), value = Decode(pair[(equal+1)..]);
                if (key is not ("state" or "code" or "error" or "error_description") || !data.TryAdd(key, value))
                    throw new RelayRejectedException();
            }
            if (!data.TryGetValue("state", out var state) || state.Length < 1 || state.Length > 256 ||
                state.Any(c => c < 33 || c > 126)) throw new RelayRejectedException();
            if (data.TryGetValue("code", out var code))
            {
                if (data.Count != 2 || code.Length < 1 || code.Length > 4096 || code.Any(c => c < 33 || c > 126))
                    throw new RelayRejectedException();
            }
            else if (!data.ContainsKey("error") || (data.Count == 3 && !data.ContainsKey("error_description")))
                throw new RelayRejectedException();
            return "/callback?" + string.Join('&', data.Select(p => Uri.EscapeDataString(p.Key) + "=" + Uri.EscapeDataString(p.Value)));
        }
        catch { throw new RelayRejectedException(); }
    }
    private static bool IsToken(char c) => char.IsAsciiLetterOrDigit(c) || "!#$%&'*+-.^_`|~".Contains(c);
    private static string Decode(string value)
    {
        var bytes = new List<byte>();
        for (int i = 0; i < value.Length; i++)
        {
            char c = value[i];
            if (c == '%')
            {
                if (i + 2 >= value.Length || !Uri.IsHexDigit(value[i+1]) || !Uri.IsHexDigit(value[i+2])) throw new RelayRejectedException();
                bytes.Add(Convert.ToByte(value.Substring(i+1, 2), 16)); i += 2;
            }
            else bytes.Add((byte)(c == '+' ? ' ' : c));
        }
        return new UTF8Encoding(false, true).GetString(bytes.ToArray());
    }
    private async Task<bool> Forward(string target, CancellationToken total)
    {
        using var phase = Phase(total);
        using var backend = new TcpClient(AddressFamily.InterNetwork);
        await backend.ConnectAsync(IPAddress.Loopback, backendPort, phase.Token);
        using var stream = backend.GetStream();
        byte[] request = Encoding.ASCII.GetBytes("GET " + target + " HTTP/1.1\r\nHost: 127.0.0.1:8766\r\nConnection: close\r\n\r\n");
        await stream.WriteAsync(request, phase.Token);
        backend.Client.Shutdown(SocketShutdown.Send); // Existing receiver requires EOF.
        var reply = new byte[1025]; int size = 0;
        while (size < reply.Length)
        {
            int count = await stream.ReadAsync(reply.AsMemory(size), phase.Token);
            if (count == 0) return reply.AsSpan(0, size).SequenceEqual(Response(true));
            size += count;
        }
        return false; // Never reflect arbitrary backend response bytes.
    }
    internal static byte[] Response(bool accepted)
    {
        string body = accepted ? "Callback validated locally. Bank session is not confirmed.\n" :
            "Callback not accepted. Close this window and restart setup if needed.\n";
        return Encoding.ASCII.GetBytes("HTTP/1.1 " + (accepted ? "200 OK" : "400 Bad Request") +
            "\r\nContent-Type: text/plain; charset=utf-8\r\nCache-Control: no-store\r\nReferrer-Policy: no-referrer\r\n" +
            "Content-Security-Policy: default-src 'none'; frame-ancestors 'none'\r\nX-Content-Type-Options: nosniff\r\n" +
            "Connection: close\r\nContent-Length: " + Encoding.ASCII.GetByteCount(body) + "\r\n\r\n" + body);
    }
    public void Dispose()
    {
        if (Interlocked.Exchange(ref disposed, 1) == 0)
        {
            stop.Cancel();
            // Leave the CTS alive while an in-flight RunAsync unwinds its linked token.
            certificate.Dispose();
        }
    }
}
