// E2E MCP client check, real product contract (PR #1: list_accounts,
// get_balance, get_transactions with start/end + offset pagination).
// Spawns the product via SERVER_CMD (required). Shape discovered live.
// v4: every data check FAILS when the field is absent - no vacuous passes.
import { connect, connectPatched, CANARY, ADVERSARIAL } from "./product.mjs";

const results = [];
const check = (name, cond, detail = "") => {
  results.push({ ok: !!cond });
  console.log(`${cond ? "PASS" : "FAIL"}  ${name}${detail ? "  -- " + detail : ""}`);
};

const P = await connect();
const { call, payload, txArgs, balArgs, collectAll } = P;
const isErr = r => r.isError === true;

const asOf = P.asOf || "2026-01-05";
const y = asOf.slice(0, 4), m = asOf.slice(5, 7);
const WIN = { start: `${y}-${m}-01`, end: `${y}-${m}-31` };

// A. tool surface
check("A1 tool surface is exactly list_accounts/get_balance/get_transactions",
  JSON.stringify(P.names) === JSON.stringify(["get_balance", "get_transactions", "list_accounts"]), P.names.join(","));
check("A2 no payment/transfer/http/fetch/write tool", !P.names.some(t => /pay|transfer|http|fetch|request|send|delete|post|write|create/i.test(t)));
const toolObjs = (await P.client.listTools()).tools;
check("A3 every tool is annotated read-only (readOnlyHint, not destructive, idempotent, closed world)",
  toolObjs.every(t => t.annotations?.readOnlyHint === true && t.annotations?.destructiveHint === false
    && t.annotations?.idempotentHint === true && t.annotations?.openWorldHint === false),
  toolObjs.map(t => `${t.name}:${JSON.stringify(t.annotations || {})}`).join(" "));

// B. happy path - every assertion requires the datum to be present
check("B1 list_accounts returns accounts with ids", P.knownId != null, P.knownId);
const bal = payload(await call("get_balance", balArgs(P.knownId)));
const balData = bal.data || {};
check("B2 get_balance succeeds and includes a decimal amount and currency",
  !bal.code && typeof balData.amount === "string" && /^-?\d+\.\d{2}$/.test(balData.amount) && typeof balData.currency === "string",
  JSON.stringify(balData).slice(0, 80));
check("B3 get_balance fails for an unknown account", isErr(await call("get_balance", balArgs("zz-no-such-account-9"))));

const paged = await collectAll(txArgs(P.knownId, WIN), 1);
const whole = await collectAll(txArgs(P.knownId, WIN), 100);
check("B4 offset pagination terminates with null next_offset, strictly increasing",
  !paged.code, paged.code || `${paged.pages} pages, ${paged.transactions.length} tx`);
check("B5 window contains fixture data (non-vacuous run)", !paged.code && paged.transactions.length > 0,
  `${paged.transactions?.length ?? 0} tx in ${WIN.start}..${WIN.end}`);
check("B6 paginated concat equals single big-page fetch, order-stable",
  !paged.code && !whole.code && paged.transactions.length > 0 && JSON.stringify(paged.transactions) === JSON.stringify(whole.transactions));
check("B7 every transaction has an id and ids are unique across pages",
  !paged.code && paged.transactions.every(t => (t.id || t.transaction_id) !== undefined)
    && new Set(paged.transactions.map(t => t.id || t.transaction_id)).size === paged.transactions.length);
check("B8 every transaction has a date field inside the window",
  !paged.code && paged.transactions.every(t => {
    const d = t.date || t.booking_date || t.transaction_date;
    return typeof d === "string" && d >= WIN.start && d <= WIN.end;
  }));
check("B9 every transaction has a finite signed-decimal amount field",
  !paged.code && paged.transactions.every(t => {
    const a = typeof t.amount === "string" ? t.amount : t.transaction_amount?.amount;
    return typeof a === "string" && /^-?\d+\.\d{2}$/.test(a) && Number.isFinite(Number(a));
  }));
const sub = { start: `${y}-${m}-02`, end: `${y}-${m}-28` };
const ranged = await collectAll(txArgs(P.knownId, sub), 100);
check("B10 start/end filter: dates present and inside [start, end]",
  !ranged.code && ranged.transactions.every(t => {
    const d = t.date || t.booking_date || t.transaction_date;
    return typeof d === "string" && d >= sub.start && d <= sub.end;
  }));

// B11: list_accounts must not leak balances
const accList = payload(await call("list_accounts"));
const accEntries = accList.data || accList.accounts || [];
check("B11 list_accounts exposes id/name/currency but never balance amounts",
  accEntries.length > 0 && accEntries.every(a => a.id && !("balance" in a) && !("amount" in a)));

// B12: complete flag consistency
const flagProbe = await collectAll(txArgs(P.knownId, WIN), 2);
check("B12 complete flag equals (next_offset === null) on the final page",
  !flagProbe.code && flagProbe.raw.complete === true && flagProbe.raw.next_offset === null);

// B13: default limit equals explicit limit=20
const defPage = payload(await call("get_transactions", txArgs(P.knownId, { ...WIN })));
const expPage = payload(await call("get_transactions", txArgs(P.knownId, { ...WIN, limit: 20 })));
check("B13 default limit behaves as limit=20", !defPage.code && JSON.stringify(defPage) === JSON.stringify(expPage));

// C. pagination/offset negatives (start/end valid so the tested arg fails)
check("C1 negative offset rejected", isErr(await call("get_transactions", txArgs(P.knownId, { ...WIN, offset: -1 }))));
check("C2 float offset rejected", isErr(await call("get_transactions", txArgs(P.knownId, { ...WIN, offset: 1.5 }))));
check("C3 string offset rejected", isErr(await call("get_transactions", txArgs(P.knownId, { ...WIN, offset: "0" }))));
check("C4 NaN limit rejected", isErr(await call("get_transactions", txArgs(P.knownId, { ...WIN, limit: NaN }))));
check("C5 zero/negative limit rejected", isErr(await call("get_transactions", txArgs(P.knownId, { ...WIN, limit: 0 }))));
const huge = payload(await call("get_transactions", txArgs(P.knownId, { ...WIN, limit: 1e9 })));
check("C6 enormous limit rejected or clamped", huge.code ? true : (huge.data || []).length <= 100);

const totalCount = whole.transactions.length;
const edge = payload(await call("get_transactions", txArgs(P.knownId, { ...WIN, offset: totalCount, limit: 100 })));
check("C7 offset == result size returns empty complete page, not an error",
  !edge.code && Array.isArray(edge.data) && edge.data.length === 0 && (edge.next_offset === null || edge.next_offset === undefined));

// D. date/account negatives
check("D1 inverted period rejected", isErr(await call("get_transactions", txArgs(P.knownId, { start: "2026-11-30", end: "2026-11-01" }))));
check("D2 month 13 rejected", isErr(await call("get_transactions", txArgs(P.knownId, { start: "2026-13-01", end: WIN.end }))));
check("D3 Feb 30 rejected (no date normalization)", isErr(await call("get_transactions", txArgs(P.knownId, { start: "2026-02-30", end: "2026-03-01" }))));
check("D4 NaN date rejected", isErr(await call("get_transactions", txArgs(P.knownId, { start: "NaN", end: WIN.end }))));
check("D5 datetime-with-timezone rejected where date expected", isErr(await call("get_transactions", txArgs(P.knownId, { start: "2026-11-01T00:00:00Z", end: WIN.end }))));
check("D6 URL as account rejected", isErr(await call("get_balance", balArgs("https://evil.example/x"))));
check("D7 localhost URL as account rejected", isErr(await call("get_balance", balArgs("http://127.0.0.1/"))));
check("D8 private-IP URL as account rejected", isErr(await call("get_balance", balArgs("http://10.0.0.1/"))));
check("D9 userinfo URL as account rejected", isErr(await call("get_balance", balArgs("https://u:p@evil.example/"))));
check("D10 SQL-ish account rejected", isErr(await call("get_balance", balArgs("' OR '1'='1"))));
check("D11 shell-ish account rejected", isErr(await call("get_balance", balArgs("acc;id"))));
check("D12 traversal account rejected", isErr(await call("get_balance", balArgs("../../etc/passwd"))));
check("D13 file:// account rejected", isErr(await call("get_balance", balArgs("file:///etc/passwd"))));

check("D14 missing start rejected", isErr(await call("get_transactions", txArgs(P.knownId, { end: WIN.end }))));
check("D15 missing end rejected", isErr(await call("get_transactions", txArgs(P.knownId, { start: WIN.start }))));
check("D16 missing account rejected", isErr(await call("get_transactions", { start: WIN.start, end: WIN.end })));
check("D17 null start rejected", isErr(await call("get_transactions", txArgs(P.knownId, { start: null, end: WIN.end }))));
check("D18 array as start rejected", isErr(await call("get_transactions", txArgs(P.knownId, { start: ["2026-01-01"], end: WIN.end }))));
check("D19 span of 366 inclusive days allowed", !isErr(await call("get_transactions", txArgs(P.knownId, { start: "2026-01-01", end: "2027-01-01" }))));
check("D20 span of 367 inclusive days rejected", isErr(await call("get_transactions", txArgs(P.knownId, { start: "2026-01-01", end: "2027-01-02" }))));
check("D21 5000-char account rejected cleanly", isErr(await call("get_balance", balArgs("a".repeat(5000)))));
check("D22 unicode account rejected", isErr(await call("get_balance", balArgs("cuenta-\u00f1\u{1F600}"))));

// E. protocol robustness
let unkErr = false;
try { unkErr = isErr(await call("no_such_tool", {})); }
catch (e) { unkErr = /MCP error|Error/.test(e.message); }
const health = payload(await call("list_accounts"));
check("E1 unknown tool -> error and server healthy afterwards", unkErr && !health.code);

// H. read-only idempotence
const r1 = JSON.stringify(payload(await call("get_transactions", txArgs(P.knownId, { ...WIN, limit: 100 }))));
const r2 = JSON.stringify(payload(await call("get_transactions", txArgs(P.knownId, { ...WIN, limit: 100 }))));
check("H1 repeated identical reads are identical", r1 === r2 && !JSON.parse(r1).code);

await P.client.close();

// F. real canary + adversarial fixture (patched copy of the product server).
// Fails loudly if the patch anchor is missing; never vacuous.
let f1 = false, f2 = false, fDetail = "";
let C;
try {
  C = await connectPatched();
  const accs = JSON.parse((await C.client.callTool({ name: "list_accounts", arguments: {} })).content[0].text);
  const aid = (accs.data || accs)[0].id;
  const resp = await C.client.callTool({ name: "get_transactions",
    arguments: { [P.accountParam]: aid, start: WIN.start, end: WIN.end, limit: 100 } });
  const body = JSON.parse(resp.content[0].text);
  const blob = JSON.stringify(body.data || []);
  f1 = blob.includes(CANARY) && blob.includes("https://evil.example/claim");
  f2 = !C.stderr().includes(CANARY);
  fDetail = f1 ? "canary+URL present in data as inert string" : "canary missing from data";
} catch (e) { fDetail = "canary run failed: " + e.message; }
finally { if (C) await C.cleanup(); }
check("F1 injected instruction/URL canary flows through tool output verbatim as inert data", f1, fDetail);
check("F2 injected canary never reaches server stderr/logs", f2);

const failed = results.filter(r => !r.ok).length;
console.log(`\n${results.length - failed}/${results.length} checks passed`);
process.exit(failed ? 1 : 0);
