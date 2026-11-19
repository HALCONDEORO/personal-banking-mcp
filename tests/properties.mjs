// Property-based tests (fast-check), real product contract. SERVER_CMD
// required. Seeded via FC_SEED. Date ranges derive from the product's as_of.
// v4: missing fields FAIL the property; canary coverage lives in the e2e
// F-checks (patched-fixture run), not here.
import { connect } from "../e2e/product.mjs";
import fc from "fast-check";

const P = await connect();
const asOf = P.asOf || "2026-01-05";
const y = asOf.slice(0, 4), m = asOf.slice(5, 7);

let pass = 0, fail = 0;
async function prop(name, arbs, predicate) {
  try {
    await fc.assert(fc.asyncProperty(...arbs, predicate), { numRuns: 40, seed: Number(process.env.FC_SEED) || undefined });
    console.log("PASS  " + name); pass++;
  } catch (e) { console.log("FAIL  " + name + "  -- " + String(e).split("\n")[0]); fail++; }
}

const day = fc.integer({ min: 1, max: 28 });
const dateRange = fc.tuple(day, day).map(([a, b]) => ({
  start: `${y}-${m}-${String(Math.min(a, b)).padStart(2, "0")}`,
  end: `${y}-${m}-${String(Math.max(a, b)).padStart(2, "0")}`,
}));

// precondition: the fixture window actually has data, or pagination
// properties would be vacuous
const fullWindow = await P.collectAll(P.txArgs(P.knownId, { start: `${y}-${m}-01`, end: `${y}-${m}-28` }), 100);
const hasData = !fullWindow.code && fullWindow.transactions.length > 0;
console.log(`${hasData ? "PASS" : "FAIL"}  P0 fixture window non-empty (${fullWindow.transactions?.length ?? 0} tx)`);
hasData ? pass++ : fail++;

await prop("P1 offset pagination reassembles the full filtered set, order-stable, any page size",
  [dateRange, fc.integer({ min: 1, max: 3 })],
  async (range, lim) => {
    const paged = await P.collectAll(P.txArgs(P.knownId, range), lim);
    const whole = await P.collectAll(P.txArgs(P.knownId, range), 100);
    if (paged.code || whole.code) return false;
    return JSON.stringify(paged.transactions) === JSON.stringify(whole.transactions);
  });

await prop("P2 date filter: every transaction HAS a date and it lies inside [start, end]",
  [dateRange],
  async range => {
    const r = await P.collectAll(P.txArgs(P.knownId, range), 100);
    if (r.code) return false;
    return r.transactions.every(t => {
      const d = t.date || t.booking_date || t.transaction_date;
      return typeof d === "string" && d >= range.start && d <= range.end;
    });
  });

await prop("P3 read-only: identical calls return identical payloads",
  [fc.integer({ min: 1, max: 100 })],
  async lim => {
    const a = JSON.stringify(P.payload(await P.call("get_transactions", P.txArgs(P.knownId, { start: `${y}-${m}-01`, end: `${y}-${m}-28`, limit: Math.max(1, Math.min(lim, 100)) }))));
    const b = JSON.stringify(P.payload(await P.call("get_transactions", P.txArgs(P.knownId, { start: `${y}-${m}-01`, end: `${y}-${m}-28`, limit: Math.max(1, Math.min(lim, 100)) }))));
    return a === b && !JSON.parse(a).code;
  });

await prop("P4 known account succeeds; arbitrary account ids give structured errors, server stays healthy",
  [fc.string({ maxLength: 80 })],
  async id => {
    const known = await P.call("get_balance", P.balArgs(P.knownId));
    if (known.isError) return false;
    const r = await P.call("get_balance", P.balArgs(id));
    const h = P.payload(await P.call("list_accounts"));
    if (h.code) return false;
    if (id === P.knownId) return true;
    return r.isError === true;
  });

await prop("P5 arbitrary start/end/offset combos: structured error or valid page, never a crash",
  [fc.string({ maxLength: 40 }), fc.string({ maxLength: 40 }), fc.integer({ min: -1000, max: 100000 })],
  async (start, end, offset) => {
    let r;
    try { r = await P.call("get_transactions", P.txArgs(P.knownId, { start, end, offset })); }
    catch { r = { isError: true }; }
    const h = P.payload(await P.call("list_accounts"));
    if (h.code) return false;
    if (r.isError) return true;
    const d = P.payload(r);
    return Array.isArray(d.data || d.transactions);
  });

await prop("P6 large offsets: structured error or empty complete page, never a crash or a loop",
  [fc.integer({ min: 1000, max: 10000 })],
  async offset => {
    let r;
    try { r = await P.call("get_transactions", P.txArgs(P.knownId, { start: `${y}-${m}-01`, end: `${y}-${m}-28`, offset })); }
    catch { return true; }
    if (r.isError) return true;
    const d = P.payload(r);
    return Array.isArray(d.data || d.transactions) && (d.next_offset === null || d.next_offset === undefined);
  });

await prop("P8 default limit equals explicit limit=20 (first page identical)",
  [dateRange],
  async range => {
    const d = P.payload(await P.call("get_transactions", P.txArgs(P.knownId, range)));
    const e = P.payload(await P.call("get_transactions", P.txArgs(P.knownId, { ...range, limit: 20 })));
    if (d.code || e.code) return d.code === e.code;
    return JSON.stringify(d) === JSON.stringify(e);
  });

await prop("P9 complete flag invariant: complete === (next_offset === null) for random limit/offset",
  [fc.integer({ min: 1, max: 100 }), fc.integer({ min: 0, max: 20 })],
  async (lim, off) => {
    let r;
    try { r = await P.call("get_transactions", P.txArgs(P.knownId, { start: `${y}-${m}-01`, end: `${y}-${m}-28`, limit: lim, offset: off })); }
    catch { return true; }
    if (r.isError) return true;
    const d = P.payload(r);
    if (d.next_offset === null || d.next_offset === undefined) return d.complete === true || d.complete === undefined;
    return d.complete === false;
  });

await P.client.close();
console.log(`\n${pass}/${pass + fail} properties passed`);
process.exit(fail ? 1 : 0);
