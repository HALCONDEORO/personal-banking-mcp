> Estado actual: solo datos sintéticos. Las variables y el adaptador bancario descritos como futuros no se leen ni activan en esta versión.

# Configuration without exposing keys (English summary)

Full guide: `CONFIGURACION.md` (Spanish). Short version:

- **Fixtures mode needs no keys.** With no banking environment variables set, the server must serve only the repo's test data.
- **When the Enable Banking adapter lands:** the RSA private key lives outside the repo (e.g. `~/.config/personal-banking-mcp/enable-banking.key.pem`, `chmod 600`); the repo references its path via `ENABLE_BANKING_KEY_PATH`, never its contents.
- `.env` stays local and git-ignored from the first commit; the repo may carry a `.env.example` with empty values.
- No secrets in the MCP client JSON config; pass environment variables or inherit the environment.
- Never log secret values; check the first real-mode startup logs.
- If a key leaks: rotate it in the Enable Banking console, rewrite git history if it reached a commit, and review logs and screenshots.

## Planned environment variables

| Variable | Meaning | Secret |
| --- | --- | --- |
| `BANKING_ADAPTER` | `fixtures` (default) or `enablebanking` | No |
| `ENABLE_BANKING_APP_ID` | Application ID from the console | Treat as private |
| `ENABLE_BANKING_KEY_PATH` | Absolute path to the RSA private key (outside the repo) | The path is not; the file is |
| `ENABLE_BANKING_SANDBOX` | `true`/`false`: sandbox console or production | No |

## Run and test the synthetic server

Python 3.10 or newer. From the repository root:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip check
python -m unittest -v
python -O -m unittest -v
python test_server.py --demo
```

The demo starts a real local MCP client/server session over stdio and prints invented data. It needs no bank credentials. To start only the server, run `python server.py`; it waits for an MCP client, not an interactive terminal command.

Example client configuration, replace both absolute paths with your checkout location:

```json
{
  "mcpServers": {
    "personal-banking-demo": {
      "command": "/absolute/path/personal-banking-mcp/.venv/bin/python",
      "args": ["/absolute/path/personal-banking-mcp/server.py"]
    }
  }
}
```

No environment variables or API keys belong in this example. The server entry point works independently of the client's working directory.
