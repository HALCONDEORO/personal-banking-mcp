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
