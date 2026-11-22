// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Marco Antonio Tevar Asensio
// Synthetic control-pipe fixture ONLY. No relay, TLS, certificate or bank code.
using System.Text;

internal static class Program
{
    // Read at most one tiny fixed ASCII frame. Never echo malformed input.
    private static string Frame(Stream input)
    {
        var bytes = new List<byte>();
        while (bytes.Count < 32)
        {
            int value = input.ReadByte();
            if (value < 0) return "EOF";
            if (value == '\n') return Encoding.ASCII.GetString(bytes.ToArray());
            if (value < 32 || value > 126) throw new IOException();
            bytes.Add((byte)value);
        }
        throw new IOException();
    }

    private static int Main(string[] args)
    {
        try
        {
            if (args.Length != 1) return 1;
            string mode = args[0];
            if (mode is not ("complete" or "hold" or "early" or "extra" or "flood" or "reject-stop")) return 1;
            using Stream input = Console.OpenStandardInput();
            if (Frame(input) != "START 1") return 1;
            if (mode == "early") return 1;
            Console.Write("READY 1\n");
            Console.Out.Flush();
            if (mode == "flood")
            {
                for (int i = 0; i < 128; i++)
                {
                    Console.Write(new string('X', 4096));
                    Console.Out.Flush();
                }
                Thread.Sleep(Timeout.Infinite);
                return 1;
            }
            if (mode is "hold" or "reject-stop")
            {
                if (Frame(input) is not ("STOP 1" or "EOF")) return 1;
                if (mode == "reject-stop") Thread.Sleep(Timeout.Infinite);
                return 1; // A cancelled synthetic attempt never reports completion.
            }
            Console.Write("DONE 1\n");
            if (mode == "extra") Console.Write("EXTRA\n");
            Console.Out.Flush();
            return 0;
        }
        catch { return 1; }
    }
}
