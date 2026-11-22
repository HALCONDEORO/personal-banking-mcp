# Related banking implementations: license-first review

Read-only source/documentation review, 22 November 2026. No code copied,
dependencies installed, application registered, account connected or credentials
requested. This is not a security audit or endorsement. README claims are
attributed project claims, not verified live-bank behavior.

| Project and pinned commit | License observed before code review | Useful idea and cautions |
| --- | --- | --- |
| [noskillish/bankmcp](https://github.com/noskillish/bankmcp/), `12b2a8a30b7c8b7d46dd1d0dd44cebde2f89be6a` | [MIT](https://github.com/noskillish/bankmcp/blob/main/LICENSE), copyright2026Nils Smed | Read-only tools and bounded unattended monitoring; watcher expiry warnings. Its README describes at-most-four daily checks. Different deployment, key and redirect model; do not import public hosting, registrations or optional attestations into the Windows-local plan. |
| [giovamuge/fine](https://github.com/giovamuge/fine), `e942903de7360f555035e834269a52d6f8eda17b` | [MIT](https://github.com/giovamuge/fine/blob/main/LICENSE), copyright2026Giovanni Mugelli and contributors | Local analysis/sync separation; actual assistant code warns at14days. README proposes6-hour sync/4daily reads. Its SQLite history, FX conversion, external notifications and model use are separate disclosures/retention decisions, not adopted here. |
| [ngoldack/fin-mcp](https://github.com/ngoldack/fin-mcp), `724b83dc27b3a901eaa2c4f26dd1d591d4fcf6eb` | No license recognized by repository API; license endpoint404 and inspected recursive tree has no license file. Permission unresolved. | Documentation describes pluggable cache and expiry UI. Do not copy/adapt source without a license grant. Toolset includes payments/write modes, which are outside this project. Only generic design concepts considered. |
| [jitheshb83/jb_gateway_mcp](https://github.com/jitheshb83/jb_gateway_mcp), `3f73b2c7abaebdec3a482e7fa44aaafcb0cf28ec` | [MIT](https://github.com/jitheshb83/jb_gateway_mcp/blob/main/LICENSE), copyright2026Jithesh Bharathan | Explicit deny-by-default caller/tool policy, consent separate from read tools. Broader Google gateway and browser-key setup are not this project's scope. Policy idea does not authenticate a caller by itself. |
| [Algiras/enable-banking-mcp](https://github.com/Algiras/enable-banking-mcp), `d23eadb65ff1e2d619537d7e58e9e3aa18ff3f5f` | [MIT](https://github.com/Algiras/enable-banking-mcp/blob/main/LICENSE), copyright2026Algiras | Session/expiry UX as a reference. README includes payment tools, automatic key registration and a hosted callback default. Do not transplant those flows; current Windows design deliberately differs. Unix0600 code is not Windows ACL proof. |
| [borgels/mcp-server-enablebanking](https://github.com/borgels/mcp-server-enablebanking), `ef446c284fe0ea31a63eb5bd40866b615d6b04dd` | [FSL-1.1-ALv2](https://github.com/borgels/mcp-server-enablebanking/blob/main/LICENSE), copyright2026Borgels Services ApS. Current terms restrict competing commercial use; future Apache2.0 grant applies only under the license's second-anniversary condition. Not a present blanket Apache/MIT grant. | Read-only construction, company/account scoping, cache freshness and expiry display are useful comparisons. Its multi-company/hosted transport/notification/storage design is not this personal Windows-local deployment. Do not copy source into MIT without separate license review. |

Repository HEADs can change. The license texts were read at the listed snapshot;
links to default-branch license pages are convenient entry points, not a promise
that their future contents remain unchanged. A repository-level license is not a
file-by-file dependency/license audit. Before any source reuse, reopen the exact
source and its applicable notices, retain required copyright/permission texts,
record adaptations in THIRD_PARTY_NOTICES and review compatibility. No source
reuse is made by this plan; attribution here identifies design references only.

## Specific source evidence inspected

- [bankmcp watcher](https://github.com/noskillish/bankmcp/blob/12b2a8a30b7c8b7d46dd1d0dd44cebde2f89be6a/src/watcher.ts): expiry notice currently≤7days, polling interval and per-watch behavior. This is not the source for our proposed14-day notice.
- [fine assistant](https://github.com/giovamuge/fine/blob/e942903de7360f555035e834269a52d6f8eda17b/src/domain/assistant.rs): expired-session alert and≤14-day consent notice. [fine sync](https://github.com/giovamuge/fine/blob/e942903de7360f555035e834269a52d6f8eda17b/src/services/sync.rs): history windows and fallback behavior; do not adopt automatic fallback/retry into a first-failure-stop trial.
- [Gateway policy](https://github.com/jitheshb83/jb_gateway_mcp/blob/3f73b2c7abaebdec3a482e7fa44aaafcb0cf28ec/src/jb_gateway_mcp/policy.py) and [initial policy](https://github.com/jitheshb83/jb_gateway_mcp/blob/3f73b2c7abaebdec3a482e7fa44aaafcb0cf28ec/policy.yaml): unlisted callers/tools denied. Our requirements additionally deny malformed/expired/conflicting policy and bind the account allowlist, not just a tool name.
- [fin-mcp config](https://github.com/ngoldack/fin-mcp/blob/724b83dc27b3a901eaa2c4f26dd1d591d4fcf6eb/internal/config/config.go): current cache TTL default5minutes. Read only to assess behavior; no licensed reuse permission established. [Repository README](https://github.com/ngoldack/fin-mcp/blob/main/README.md) describes cache modes and payment access modes.
- [Algiras session storage](https://github.com/Algiras/enable-banking-mcp/blob/d23eadb65ff1e2d619537d7e58e9e3aa18ff3f5f/src/sessions.rs): local file-mode handling; it does not qualify this project's Windows nonexportable-key/DPAPI/ACL design.
- [borgels README](https://github.com/borgels/mcp-server-enablebanking/blob/main/README.md): read-only claim, company scoping, expiry days and default300-second cache. Documentation review only; no runtime security guarantee inferred.

## Decisions for our original implementation

1. **Deny by default:** only explicitly approved local caller/account/read tool
   combinations. Consent/admin work remains separate; payments absent rather
   than merely disabled by a configurable write mode.
2. **Expiry warning≤14days:** calculate from actual locally stored expiry without
   querying the bank for a reminder. Warn immediately for a shorter consent;
   stop at expiry/revocation. User renews official consent, no automatic login.
3. **Cache as a deliberate privacy trade-off:** propose60-minute local freshness
   only for a later approved retention design. This is our chosen candidate TTL,
   not a claim that all six projects use it. At present fin-mcp defaults5minutes
   and borgels documents300seconds. A cache is neither a bank read budget nor a
   substitute for checking authorization. Do not label old data current.
4. **Background budget:** a conservative4refreshes per rolling24h per selected
   account/endpoint/consent, with durable restart-safe counters and coalescing,
   only if background operation is separately chosen. Pagination/presence
   exceptions need explicit accounting. The first trial starts no scheduler.

A60-minute TTL could lead to24daily fetches if used as the only limit. Therefore
freshness and bank-call budget must be enforced independently. A budget-exhausted
answer may return only clearly dated authorized cache under an approved policy,
or say fresh data is unavailable. No fake presence, new consent or cache flush
may bypass a bank limit. The first trial keeps no persistent financial cache.

Official bank/provider limits, not other repositories, control access. See
[the first-trial plan](PERSONAL_READ_TRIAL_PLAN.md) for the5-minute/90-day history
boundary, session expiry, owner steps and remaining integration gates. No plan
or borrowed idea connects a real account.
