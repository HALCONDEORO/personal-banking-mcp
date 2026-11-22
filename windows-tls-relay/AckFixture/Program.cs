// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Marco Antonio Tevar Asensio
// Duplex fixture ONLY: no sockets, certificates, stores, bank or TLS host.
using System.Buffers.Binary;
using System.Text;
using PersonalBanking.LocalTls;

internal static class Program
{
    private static readonly HashSet<string> Modes = new(StringComparer.Ordinal)
    { "complete", "early", "bad-magic", "oversize", "truncated", "bad-ascii",
      "wrong-state", "hold-before-data", "hold-after-ack", "nonzero", "trailing", "wrong-reply" };

    private static void WriteFrame(Stream output, string magic, byte[] value)
    {
        var header = new byte[8];
        Encoding.ASCII.GetBytes(magic).CopyTo(header, 0);
        BinaryPrimitives.WriteUInt32BigEndian(header.AsSpan(4), (uint)value.Length);
        output.Write(header); output.Write(value); output.Flush();
    }

    private static int Main(string[] args)
    {
        try
        {
            if (args.Length != 1 || !Modes.Contains(args[0])) return 2;
            var mode = args[0];
            if (mode == "early") return 3;
            using var input = Console.OpenStandardInput();
            using var output = Console.OpenStandardOutput();
            var header = new byte[8]; input.ReadExactly(header);
            uint size = BinaryPrimitives.ReadUInt32BigEndian(header.AsSpan(4));
            if (!header.AsSpan(0, 4).SequenceEqual("PAI1"u8) || size is 0 or > 12288) return 2;
            var request = new byte[(int)size]; input.ReadExactly(request);
            string target = LocalTlsRelay.ParseBrowserRequest(request);
            if (mode == "wrong-state") target = "/callback?state=synthetic-wrong-state&code=synthetic-private-code";
            if (mode == "hold-before-data") Thread.Sleep(Timeout.Infinite);
            var payload = Encoding.ASCII.GetBytes(target);
            if (mode == "bad-ascii") payload[0] = 255;
            if (mode == "oversize")
            {
                output.Write(new byte[] { 80, 65, 68, 49, 255, 255, 255, 255 }); output.Flush(); return 2;
            }
            if (mode == "truncated")
            {
                output.Write("PAD1\0\0\0\x10"u8); output.WriteByte(47); output.Flush(); return 2;
            }
            WriteFrame(output, mode == "bad-magic" ? "BAD!" : "PAD1", payload);
            // Do not produce even the synthetic browser response until exact ACK+EOF.
            var ack = new byte[5]; input.ReadExactly(ack);
            if (!ack.AsSpan(0, 4).SequenceEqual("PAA1"u8) || ack[4] > 1 || input.ReadByte() != -1) return 2;
            if (mode == "hold-after-ack") Thread.Sleep(Timeout.Infinite);
            bool accepted = ack[4] == 1;
            var response = LocalTlsRelay.Response(mode == "wrong-reply" ? !accepted : accepted);
            WriteFrame(output, "PAR1", response);
            if (mode == "trailing") output.WriteByte(0);
            output.Flush();
            return mode == "nonzero" ? 3 : 0;
        }
        catch { return 2; } // Fixed exit only, never callback/diagnostic output.
    }
}
