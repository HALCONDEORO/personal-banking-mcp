// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Marco Antonio Tevar Asensio
// Synthetic parser/data-pipe child ONLY. No socket, store, key, bank or TLS host.
using System.Buffers.Binary;
using System.Text;
using PersonalBanking.LocalTls;

internal static class Program
{
    private static readonly HashSet<string> Modes = new(StringComparer.Ordinal)
    {
        "complete", "early", "bad-magic", "oversize", "truncated", "duplicate",
        "trailing", "nonzero", "hold", "flood", "wrong-state", "bad-ascii"
    };

    private static byte[] Frame(byte[] payload)
    {
        var result = new byte[8 + payload.Length];
        "PBD1"u8.CopyTo(result);
        BinaryPrimitives.WriteUInt32BigEndian(result.AsSpan(4, 4), (uint)payload.Length);
        payload.CopyTo(result, 8);
        return result;
    }

    private static int Main(string[] args)
    {
        try
        {
            if (args.Length != 1 || !Modes.Contains(args[0])) return 2;
            string mode = args[0];
            if (mode == "early") return 3;
            using var input = Console.OpenStandardInput();
            using var output = Console.OpenStandardOutput();
            var header = new byte[8];
            input.ReadExactly(header);
            uint size = BinaryPrimitives.ReadUInt32BigEndian(header.AsSpan(4));
            if (!header.AsSpan(0, 4).SequenceEqual("PBI1"u8) || size is 0 or > 12288) return 2;
            var raw = new byte[(int)size];
            input.ReadExactly(raw);
            if (input.ReadByte() != -1) return 2; // exact one frame and stdin EOF
            // Actual relay parser, not a duplicate or a mock. Never open a relay.
            string target = LocalTlsRelay.ParseBrowserRequest(raw);
            if (mode == "wrong-state") target = "/callback?state=synthetic-wrong-state&code=synthetic-private-code";
            byte[] payload = Encoding.ASCII.GetBytes(target);
            byte[] frame = Frame(payload);
            if (mode == "bad-magic") frame[0] = 0;
            if (mode == "oversize")
            {
                BinaryPrimitives.WriteUInt32BigEndian(frame.AsSpan(4, 4), 8193);
                output.Write(frame.AsSpan(0, 8));
                return 0;
            }
            if (mode == "bad-ascii") frame[8] = 255;
            if (mode == "truncated") output.Write(frame.AsSpan(0, frame.Length - 1));
            else output.Write(frame);
            if (mode == "duplicate") output.Write(frame);
            if (mode == "trailing") output.WriteByte(0);
            if (mode == "flood")
                for (int i = 0; i < 1024; i++) output.Write(frame);
            output.Flush();
            if (mode == "hold") Thread.Sleep(Timeout.Infinite);
            return mode == "nonzero" ? 3 : 0;
        }
        catch { return 2; } // no parser exception, callback or diagnostic on stderr
    }
}
