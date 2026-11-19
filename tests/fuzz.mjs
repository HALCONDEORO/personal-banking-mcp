// Fuzz runner, real product contract (3 tools). SERVER_CMD required.
// Corpus uses "account_id"; keys are remapped to the server's discovered
// account parameter. Liveness = successful list_accounts with parsed payload.
import { connect, connectPatched, CANARY } from "../e2e/product.mjs";
import fs from "node:fs";
import path from "node:path";

const ROOT = path.resolve(new URL("..", import.meta.url).pathname);
const CORPUS = path.join(ROOT, "fuzz-corpus");
const P = await connect();

let pass = 0, fail = 0;
const files = fs.readdirSync(CORPUS).filter(f => f.endsWith(".json")).sort();
for (const f of files) {
  const cases = JSON.parse(fs.readFileSync(path.join(CORPUS, f), "utf8"));
  for (const c of cases) {
    let args = JSON.parse(JSON.stringify(c.arguments).replaceAll("{KNOWN}", P.knownId));
    if ("account_id" in args && P.accountParam !== "account_id") {
      args[P.accountParam] = args.account_id; delete args.account_id;
    }
    let ok = true, detail = "";
    try {
      const r = await P.call(c.tool, args);
      const text = r.content?.[0]?.text ?? "";
      if (!r.isError) JSON.parse(text);
      if (c.expect_error && !r.isError) { ok = false; detail = "expected error, got success"; }
      if (c.expect_error && text.includes(CANARY)) { ok = false; detail = "canary in error payload"; }
    } catch (e) {
      if (c.expect_error && /MCP error|validation|Error/.test(e.message)) { /* protocol-level error counts */ }
      else { ok = false; detail = "transport-level failure: " + e.message; }
    }
    try {
      const h = await P.call("list_accounts", {});
      if (h.isError) throw new Error("liveness list_accounts returned isError");
      const hp = JSON.parse(h.content[0].text);
      if (!(hp.data || hp.accounts || hp).length) throw new Error("liveness payload empty");
    } catch (e) { ok = false; detail = "server unhealthy after case: " + e.message; }
    console.log(`${ok ? "PASS" : "FAIL"}  ${f}: ${c.name}${detail ? " -- " + detail : ""}`);
    ok ? pass++ : fail++;
  }
}
await P.client.close();
// real canary: patched-fixture run (the product fixtures carry no canary, so
// checking the unpatched server would be vacuous)
let cOk = false, cDetail = "";
let C;
try {
  C = await connectPatched();
  const accs = JSON.parse((await C.client.callTool({ name: "list_accounts", arguments: {} })).content[0].text);
  const aid = (accs.data || accs)[0].id;
  const resp = await C.client.callTool({ name: "get_transactions", arguments: { [P.accountParam]: aid, start: "2026-01-01", end: "2026-01-31", limit: 100 } });
  const blob = JSON.stringify(JSON.parse(resp.content[0].text).data || []);
  cOk = blob.includes(CANARY) && !C.stderr().includes(CANARY);
  cDetail = "canary in data, absent from stderr";
} catch (e) { cDetail = "canary run failed: " + e.message; }
finally { if (C) await C.cleanup(); }
console.log(`${cOk ? "PASS" : "FAIL"}  injected canary flows as data, never in stderr/logs -- ${cDetail}`);
if (!cOk) fail++;
console.log(`\n${pass}/${pass + fail} fuzz cases passed`);
process.exit(fail ? 1 : 0);
