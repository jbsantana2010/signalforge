# Sprint 3 — Pilot Hardening (Tech Lead Decision Doc)

**Author:** Tech Lead
**Supersedes:** prior SPRINT_3.md draft (13-ticket plan)
**Duration:** 2 weeks, one developer
**Sprint question:** "Can Warder safely handle real pilot traffic from a paying agency?"

---

## TL;DR — what changed vs. the draft

As tech lead I am rejecting three framings in the earlier draft and adding five items it missed. Decisions up front so there's no ambiguity during execution:

**Demoted from P0:**
- **Rebrand** → P1 cleanup. Inconsistent naming is embarrassing, not unsafe. Ship the pilot first.
- **Full durable job queue** → scoped down to *call-retry durability only*. The engagement worker is already DB-backed (it reads scheduled rows from `leads`/`engagement_steps`, APScheduler just drives the tick). The actual durability hole is the `asyncio.sleep` in `call_service`. Fix that surgically; don't build a generic queue we don't need yet.
- **hCaptcha** → P1. Rate limit + honeypot is sufficient for first-pilot volume. Add CAPTCHA only if abuse is observed.
- **Real-time SSE** → deferred to Sprint 4. Manual refresh is ugly, not unsafe.
- **Timezone-aware working hours** → P1. Workaround for first pilot: run the server in the pilot's TZ. Proper fix when we onboard a second TZ.

**Added as P0 (missing from the draft):**
1. **TLS termination.** `KNOWN_ISSUES.md #10` — HTTP only. Cannot take real traffic. JWT over HTTP = instant compromise. Twilio refuses non-HTTPS callbacks. Non-negotiable.
2. **Error monitoring (Sentry).** Without this we don't know when prod breaks. A pilot without observability is not a pilot, it's a prayer.
3. **Automated Postgres backups off-box.** A Docker volume with no backup is one `docker volume prune` away from losing pilot data. A paying customer will not forgive that.
4. **Idempotent public lead submission.** Network retries + double-taps create duplicate leads and duplicate SMS. A 30-line fix that prevents a painful class of bugs.
5. **Twilio status callback ingestion.** When SMS fails (carrier block, landline, invalid number), we need to know. Otherwise we look broken to the agency while silently burning money on undeliverable messages.

**Rationale:** The earlier draft optimized for closing items in `KNOWN_ISSUES.md`. That's necessary but insufficient. A pilot-ready system also needs ops primitives (TLS, monitoring, backups) that the code author rarely thinks of. That's my job.

---

## 1. Final Sprint Scope

### P0 — Must ship for pilot

| ID | Title | Est | Domain |
|----|-------|-----|--------|
| INF-01 | TLS termination via Caddy reverse proxy | 0.5d | Infra |
| INF-02 | Sentry wired to backend + frontend with PII scrubbing | 0.5d | Infra |
| INF-03 | Automated `pg_dump` → off-box (S3 or Backblaze), daily cron, 14-day retention | 0.5d | Infra |
| INF-04 | Secrets hygiene audit: rotate `JWT_SECRET`, verify no `.env` in git history, document secret ownership | 0.25d | Infra |
| SEC-01 | Twilio webhook signature validation on every Twilio route | 1d | Backend/Security |
| SEC-02 | Rate limit middleware on `/api/public/leads` (token bucket, per funnel + IP) | 0.5d | Backend/Security |
| SEC-03 | Login bruteforce protection (5 failed → 15-min lockout per account) | 0.25d | Backend/Security |
| BE-01 | Durable call retry — `scheduled_jobs` table scoped *only* to call retries | 1d | Backend |
| BE-02 | SMS consent: migration, enforcement in 4 services, STOP/UNSUBSCRIBE handling | 1.5d | Backend |
| BE-03 | Idempotency key on `POST /api/public/leads` (client-supplied UUID, 24h TTL) | 0.5d | Backend |
| BE-04 | Twilio message status callback ingestion → `message_events` table | 0.5d | Backend |
| FE-01 | SMS consent checkbox in `FunnelWizard` (gated by funnel config) | 0.5d | Frontend |
| FE-02 | Generate + send idempotency key on public submit | 0.25d | Frontend |
| QA-01 | Org-isolation integration test across every admin list endpoint | 0.5d | QA |
| QA-02 | Pilot dry-run: RUNBOOK_PILOT end-to-end with live creds, documented pass | 1d | QA |

**P0 total: ~9 days.** Fits in a 10-day sprint with 1 day buffer.

### P1 — Ship if time permits

| ID | Title | Est | Domain |
|----|-------|-----|--------|
| SEC-04 | hCaptcha on public submit (funnel-toggleable) | 0.5d | Backend + Frontend |
| SEC-05 | Admin audit log (who did what, when) | 1d | Backend |
| BE-05 | Timezone-aware working hours + org TZ setting | 1d | Backend |
| QA-03 | Twilio signature validation tests | 0.25d | QA |
| QA-04 | SMS consent + STOP tests | 0.5d | QA |
| QA-05 | Durable call retry test (kill-and-restart fixture) | 0.5d | QA |
| QA-06 | Playwright smoke: public submit + admin leads list | 1d | QA |
| CLN-01 | Rebrand pass: SignalForge / LeadForge → Warder AI | 1d | Cleanup |
| CLN-02 | Per-service `/health` deep-check (DB, Twilio reachability, SMTP noop, Claude ping) | 0.5d | Backend |

### Deferred (Sprint 4+)

Explicitly **not** shipping this sprint. Don't sneak these in.

- Full generic durable job queue (revisit when we have >1 worker host or >1 retry type)
- Real-time SSE admin leads list
- Funnel builder UI
- JWT refresh tokens, password reset, user management UI
- HTML email templates
- CSV export, outbound webhook integrations
- Funnel A/B testing
- Routing rule preview UI
- Exponential backoff retry policy tuning
- Horizontal scale / multiple backend replicas
- SOC2-grade audit trail

---

## 2. Execution Plan

Execution order is not arbitrary — it follows dependency chains and front-loads the items that unblock testing.

### Week 1

**Day 1 — Infra foundation (cannot test anything else until this lands)**
1. `INF-01` TLS via Caddy. HTTPS URL confirmed reachable from Twilio.
2. `INF-04` Secrets audit. `git log -p | grep -E "AUTH_TOKEN|SECRET|API_KEY"` — any hit triggers rotation + history rewrite.
3. `INF-02` Sentry DSN in backend + frontend, PII scrubber configured (scrub `phone`, `email`, `message_body`, JWT contents).

**Day 2 — Security quick wins (parallel-safe)**
4. `SEC-01` Twilio signature validation. Reconfigure Twilio console webhooks to HTTPS URL. Verify in sandbox before prod.
5. `SEC-02` Rate limit middleware. In-process token bucket keyed by `(funnel_slug, client_ip)`, 10/min, 100/hr, per-funnel override.
6. `SEC-03` Login lockout. Track failed logins in `auth_attempts` table, reject after 5 within 15 min.

**Day 3–4 — SMS consent end-to-end (highest compliance risk)**
7. `BE-02` migration `018_sms_consent.sql`; enforcement in `engagement_service`, `sequence_service`, `automation_service`, `call_service`; STOP handler in inbound SMS route.
8. `FE-01` consent checkbox in `FunnelWizard.tsx`, gated by `funnel.sms_consent_required` (default `true` for new funnels, `false` for grandfathered pilot funnels).

**Day 5 — Backend durability + idempotency**
9. `BE-01` `scheduled_jobs` table narrowly scoped to call retries. `SELECT ... FOR UPDATE SKIP LOCKED`. Test: kill backend mid-retry, restart, retry still fires.
10. `BE-03` idempotency key: new `lead_idempotency` table (`key TEXT PRIMARY KEY, lead_id UUID, created_at`), 24h TTL cleanup job. Return existing lead on duplicate key.
11. `BE-04` Twilio status callback route, persist to `message_events`, surface failure count on `/admin/ops`.
12. `FE-02` generate UUID in `FunnelWizard` submit, send as `Idempotency-Key` header.

### Week 2

**Day 6 — Infra finalization**
13. `INF-03` backup cron. `pg_dump | gzip | aws s3 cp` or equivalent. Cron runs 03:00 UTC daily. Retention: 14 daily + 4 weekly.
14. **Restore drill** (not a ticket, a ritual): pull yesterday's dump, restore to a throwaway container, verify row counts. Do this before pilot. A backup you haven't restored is not a backup.

**Day 7 — Correctness gate**
15. `QA-01` org-isolation test. Two orgs, two JWTs, assert every admin list endpoint returns only the owning org's rows. This is the one test we cannot pilot without.

**Day 8 — P1 pull-ins (in priority order)**
16. `CLN-01` rebrand pass (parallelizable with P1 test work).
17. `BE-05` timezone-aware working hours (only if pilot org is not in server TZ).
18. `QA-03` through `QA-06` — fill in tests as time allows.
19. `SEC-04` hCaptcha (only if we have evidence of abuse, otherwise skip).

**Day 9 — Pilot dry-run**
20. `QA-02` full RUNBOOK_PILOT walkthrough against production with live creds. Submit real leads, verify signature-validated webhooks, consent-gated SMS, durable retry under restart, org isolation, Sentry alerts firing on injected errors, backup ran, restore verified.

**Day 10 — Buffer / punch list**
- Fix whatever QA-02 surfaced.
- Update `RUNBOOK.md` and `RUNBOOK_PILOT.md` to reflect new reality (HTTPS URLs, Sentry DSN config, backup location, rate-limit behavior, consent flow).
- Tag release, cut pilot branch.

### Dependency graph (what blocks what)

```
INF-01 (TLS) ──► SEC-01 (Twilio sig needs HTTPS) ──► QA-03
INF-02 (Sentry) ─── (no downstream blockers, but pilot needs it)
BE-02 (consent schema) ──► FE-01 (checkbox) ──► QA-04
BE-03 (idempotency backend) ──► FE-02 (client key)
BE-01 (durable retry) ──► QA-05
Everything P0 ──► QA-02 (pilot dry-run is the gate)
```

---

## 3. Agent Assignment

Simulated team of four specialists plus tech-lead-me. Each agent owns a ticket family end-to-end.

### Infra Agent
**Owns:** INF-01, INF-02, INF-03, INF-04, CLN-02
**Deliverables:** Caddy config, Sentry SDKs initialized with scrubbers, backup cron + S3 bucket + retention policy, secrets audit report with remediation.
**Blocks:** Security Agent (TLS must land before Twilio signature validation is testable).

### Security Agent
**Owns:** SEC-01, SEC-02, SEC-03, BE-03 (idempotency), SEC-04 (P1), SEC-05 (P1)
**Deliverables:** signed-webhook middleware, rate-limit middleware, login-lockout table + logic, idempotency handler.
**Blocks:** QA-03 (signature tests).

### Backend Agent
**Owns:** BE-01, BE-02, BE-04, BE-05 (P1)
**Deliverables:** durable call-retry queue, SMS consent migration + enforcement + STOP handler, Twilio status callback ingestion, TZ-aware working hours.
**Blocks:** Frontend Agent on BE-02 (schema must land before checkbox).

### Frontend Agent
**Owns:** FE-01, FE-02, CLN-01
**Deliverables:** consent checkbox with configurable copy, idempotency key generation, rebrand string sweep.
**Blocks:** none once BE-02/BE-03 land.

### QA Agent
**Owns:** QA-01 (P0), QA-02 (P0 dry-run), QA-03 through QA-06 (P1)
**Deliverables:** org-isolation integration test, full pilot dry-run report, per-feature tests as capacity allows.
**Blocks:** sprint sign-off. QA-02 is the gate.

### Tech Lead (me)
**Owns:** architecture decisions, scope enforcement, this doc, risk triage.
**Specifically does not own implementation.** If a ticket slips, I re-prioritize; I don't code around it.

---

## 4. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| TLS cert provisioning fails day-1 → blocks signature validation testing | Medium | High | Use Caddy (auto-cert via Let's Encrypt, least fragile option). Have a self-signed fallback documented for local. |
| Twilio signature rollout breaks prod webhooks | Medium | High | Stage in Twilio sandbox subaccount first. Deploy signature code behind a `TWILIO_SIG_ENFORCED=false` flag; flip to `true` only after a clean green run against sandbox. |
| SMS consent retrofit breaks existing pilot data (no opt-in recorded historically) | High | Medium | Grandfather existing funnels with `sms_consent_required=false`. New funnels default to `true`. Decision: back-fill consent on legacy leads = NO (legally safer to treat them as unknown). |
| Durable call-retry scope creep into generic queue | High | Medium | Named and bounded: "this table is for call retries only." Any other use case goes to Sprint 4. Code review gate enforces this. |
| Sentry leaks PII (phone numbers, SMS bodies) | Medium | High (GDPR / legal) | `before_send` hook scrubs `phone`, `email`, `message_body`, `authorization`, JWT claims. Verified with an intentional error containing PII before pilot. |
| Backups exist but are never tested → false confidence | Very High | Catastrophic | Mandatory restore drill in Day 6. "Backup" does not count until restored and row-counts verified. |
| Rate limiter false positives block legit traffic | Low | Medium | Default 10/min/100/hr is forgiving. Log all 429s. Review after 48h of pilot traffic and tune. |
| In-process rate limiter state lost on restart → burst through | Low | Low | Acceptable for single-node pilot. If horizontal scaling arrives, move to Redis or DB-backed. |
| Idempotency key collision (client reuses UUID) | Very Low | Low | 24h TTL, UUID v4. Astronomically unlikely; if it happens, second submit returns first lead, which is the right behavior. |
| Pilot dry-run (Day 9) fails and buffer is consumed | Medium | High | Day 10 buffer exists for exactly this. If buffer exhausted, sprint extends rather than pilot launches on an untested build. **No pilot without a green QA-02.** |
| Secrets leaked in git history | Low | Very High | Audit day 1. `git log --all -p` through a secret-scanning tool. Any finding triggers rotation + potentially history rewrite on pilot branch. |
| Pilot traffic exceeds rate limit defaults | Medium | Medium | Per-funnel override available from day one; ops can raise without code change. |

### What I am choosing NOT to defend against

Calling these out explicitly so we don't pretend they're handled:

- **Multi-region failure.** Single node, single region. If the box or region dies, we're down. Acceptable for pilot.
- **DDoS.** Caddy + rate limiter is enough for opportunistic traffic, not a determined attack. Pilot's not worth DDoSing.
- **Advanced persistent threat / insider risk.** No audit log in P0 (SEC-05 is P1). Acceptable for ~5 pilot users.
- **Zero-downtime deploys.** Deploys require a brief restart. Pilot can live with a 30-second window during maintenance.
- **SOC2 / HIPAA / enterprise compliance.** Not relevant for this stage.

---

## 5. Definition of Done

The pilot launches when and only when all of the following are true. No individual item is negotiable.

**Code + infra**
- [ ] All P0 tickets merged to `main` and deployed to production.
- [ ] `pytest backend/tests -v` green.
- [ ] `npm run build` produces a clean production bundle.
- [ ] Production traffic served over HTTPS only (HTTP redirects to HTTPS; plain HTTP does not accept JWT).

**Verification**
- [ ] `GET https://<prod>/health` returns `{status: "ok", database: "connected"}` with expected service flags.
- [ ] Twilio signature test: crafted request with invalid signature returns 403 and logs a WARNING.
- [ ] SMS consent test: lead submission without opt-in does not trigger any outbound SMS; `sms_blocked_no_consent` event logged.
- [ ] STOP keyword test: inbound `STOP` from a lead phone → `sms_opt_in_at` cleared → next worker run does not send to that lead.
- [ ] Rate limit test: 11 submissions in 60 seconds from the same IP to the same funnel → 429 with `Retry-After`.
- [ ] Idempotency test: two `POST /api/public/leads` with the same `Idempotency-Key` → one lead created, one SMS fired.
- [ ] Durable retry test: backend killed mid-retry, restarted, retry fires at original `run_at` without manual intervention.
- [ ] Org isolation test: QA-01 passes; regression check (temporarily drop an `org_id` filter) fails the test loudly.

**Ops readiness**
- [ ] Sentry receiving events from backend + frontend; test error on staging fires an alert to the on-call email.
- [ ] Sentry PII scrubbing verified: an intentional error containing a phone number shows `[Filtered]` in Sentry UI.
- [ ] Daily backup cron has executed at least once successfully; artifact present in off-box storage.
- [ ] Restore drill completed: yesterday's dump restored to a throwaway container, row counts match production within tolerance.
- [ ] `RUNBOOK.md` + `RUNBOOK_PILOT.md` updated to match new HTTPS URLs, Sentry config, backup location, rate-limit thresholds, consent flow, and durable-retry behavior.
- [ ] Twilio console webhooks pointed at HTTPS URLs.
- [ ] `TWILIO_SIG_ENFORCED=true` in production.

**Pilot dry-run (QA-02)**
- [ ] Submit a real lead via the public funnel. SMS received on a real phone within 60 seconds. Email received. AI score populated. Call bridge connected end-to-end (if working hours permit).
- [ ] Admin login works, lead appears in list, stage transitions work, org-switch preserves isolation.
- [ ] No WARNING or ERROR in Sentry during the dry-run beyond pre-documented expected entries.
- [ ] Full dry-run report filed (pass/fail per RUNBOOK_PILOT step).

**Governance**
- [ ] Sprint demo to stakeholders with the dry-run evidence.
- [ ] Go/no-go decision recorded in writing. "Go" requires all above checked.

---

## Decisions log (so there's no re-litigating during execution)

1. **Postgres is our queue.** Not Celery, not Redis-backed. Single node pilot.
2. **Caddy, not nginx.** Auto-cert, one-file config. Less to go wrong.
3. **Consent defaults to required on new funnels; grandfathered on existing.** Legally defensible, operationally manageable.
4. **Rate limiter lives in-process.** Not Redis. If we horizontal-scale, we revisit.
5. **Rebrand is cleanup, not a blocker.** Pilot can ship with mixed naming; customers see "Warder AI" via branding config.
6. **No CAPTCHA in P0.** Add only if abuse is observed. Friction vs. risk tradeoff favors honeypot + rate limit for first pilot.
7. **SSE real-time is Sprint 4.** F5 is fine for a pilot. Not fine for GA.
8. **Scope of durable retry is call retries only.** Engagement worker already reads from DB; don't over-refactor.
9. **Sentry is mandatory.** Observability is not optional for a pilot.
10. **Backups are not optional, and restore drill is the actual test.**

---

## What I need from you

1. Confirm the pilot agency's timezone — if it's not ours, `BE-05` promotes to P0.
2. Confirm we have an S3/Backblaze/equivalent bucket for `INF-03`. If not, create one before Day 6.
3. Confirm Sentry account + project (free tier is fine for pilot volume).
4. Confirm the pilot domain name so TLS cert can be provisioned.
5. Green-light the scope above or push back on specific calls. I'd rather defend a decision now than discover disagreement at Day 9.

Silence = approval. I'll kick off with `INF-01` when you confirm or after 24h.

---

## Day 1 execution log

Kicked off after scope approval. Three tickets delivered.

### Shipped today

**BE-01 — Minimal call-retry persistence** [COMPLETE]
- `backend/migrations/018_call_retry_jobs.sql` — narrow-scope table, claim/recover indexes. Not a generic job queue, enforced in the comment header.
- `backend/app/services/call_retry_queue.py` — enqueue / claim_due (FOR UPDATE SKIP LOCKED via CTE) / mark_done / mark_failed / recover_stuck.
- `backend/app/services/call_service.py` — replaced `asyncio.sleep(120)` with `schedule_retry()`. Added `_execute_retry()` and `run_due_retries()`. Kept `retry_call()` as a backwards-compat shim; remove when every callsite migrates.
- `backend/app/api/public/twilio.py` — retry callsite now persists via `schedule_retry()` instead of `asyncio.create_task(retry_call(...))`. Restart-safe.
- `backend/app/main.py` — startup recovery call, plus a new APScheduler job `call_retry_worker` ticking every 30s alongside the existing 60s engagement worker. Worker ID is `hostname-pid` so restarts are distinguishable in logs.
- `backend/tests/test_call_retry.py` — 4 tests, all pass: max-attempts cap, enqueue+mark-lead, recover-before-claim ordering, fail-loudly on mid-execute exception.
- `backend/pytest.ini` — added `asyncio_mode=auto` so pytest-asyncio picks up the new tests without per-function decorators.

**INF-01 — TLS termination** [COMPLETE]
- `Caddyfile` at repo root. Auto Let's Encrypt, HSTS, security headers, structured access log. Split-routing between Next.js (port 3000) and FastAPI (port 8000) with an alt-config block for the subdomain pattern (`api.` vs `app.`) commented out.
- Deploy step: export `WARDER_DOMAIN=<pilot-domain>` and run `caddy run --config ./Caddyfile`. DNS A record required before first run so the ACME challenge resolves.

**INF-02 — Sentry + PII scrubbing** [COMPLETE]
- `backend/app/observability.py` — `init_sentry()` + `_before_send` scrubber. Strips sensitive keys (phone, email, body, authorization, token, smtp_pass, twilio_auth_token, claude_api_key, etc.) AND regex-scrubs phone/email patterns out of free-text fields (exception messages, breadcrumbs). No-op when `SENTRY_DSN` unset.
- `backend/app/main.py` — wired immediately after logger init so module import failures report too.
- `frontend/sentry.client.config.ts` + `sentry.server.config.ts` + `instrumentation.ts` — matching scrubber in TS.
- `backend/requirements.txt` — `sentry-sdk[fastapi,asyncpg]>=2.0.0`.
- `.env.example` updates on both sides with `SENTRY_DSN`, `SENTRY_ENV`, `WARDER_RELEASE`.
- `backend/tests/test_observability.py` — 5 tests, all pass: phone scrub, email scrub, nested-dict key filtering, full event flow, scrubber crash safety.

### Test status after Day 1

- **New tests:** 9/9 pass (4 BE-01 + 5 INF-02).
- **Existing tests:** 1 pre-existing failure in `test_api.py::test_login_and_get_leads`. The mock org fixture is missing `agency_id`, which was added to the schema after the test was written. NOT caused by any Day 1 change. Filed as follow-up (see below).

### Decisions made during execution (not pre-decided in sprint plan)

1. **Call retry tick interval is 30s**, not 60s. Reason: the retry target is ~2 minutes after failure, so a 60s tick adds up to 60s of jitter on top. 30s keeps SLA close to the prior in-process behavior.
2. **Sentry `traces_sample_rate=0.05`** (5%), profiling off. Cheap observability for pilot volume; we can dial up if we see issues.
3. **Regex scrub on free-text** (phone + email patterns) in addition to key-based scrub. A common leak path is exception messages like `"failed to send to +15551234567"`. Key-based scrubbing alone misses that.
4. **Dropped the `sentry-sdk` LoggingIntegration at ERROR level only.** Not INFO — we don't want every log line becoming a Sentry breadcrumb in a chatty service.
5. **Caddy over nginx.** Auto-cert is the pilot-critical feature; one less moving part than certbot renew cron.

### Follow-ups for Day 2

- **INF-03 backups** is next on the infra track. Need: bucket target confirmed.
- **INF-04 secrets audit** is a 30-minute sweep; do it before opening the first pilot-branch PR.
- **SEC-01 Twilio signature validation** depends on INF-01 being deployed (signature validation requires the webhook URLs to be HTTPS). Queue for Day 3 once DNS + cert are live.
- **Pre-existing test fix:** `test_api.py::test_login_and_get_leads` fixture needs `agency_id` key on the mock org row. Trivial. Will fix alongside the test expansion work in QA-01.
- **`retry_call` shim removal:** once Sprint 3 wraps, delete it and anything still importing the name.

### Tool note for the implementer

The Claude-side file editor truncated two large overwrite operations during BE-01 (`call_service.py` stopped at ~106 lines; `main.py` stopped at line 128 mid-string). Both files were reconstructed via `bash` heredocs and parse cleanly now. If a future edit looks incomplete, run `python -c "import ast; ast.parse(open('<path>').read())"` on the file before shipping — it's the fastest early-warning signal.
