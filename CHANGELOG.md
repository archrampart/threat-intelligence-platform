# Changelog

## Unreleased

### Added

- **Dark web: E-mail address assets** - watch a single mailbox; matched exactly in leak posts, Telegram messages and feeds.
- `BACKEND_PORT` sets the host port of the backend (Swagger UI / debugging, still bound to 127.0.0.1).

### Changed

- Dark web domain / e-mail domain assets: a full address gets a clear "enter only the domain part" message, and
  public mail providers (`gmail.com`, `hotmail.com`, ...) are rejected because they match almost every leak.

### Fixed

- Watchlists: assets added by hand in the **Create** dialog were dropped (the form did not send them and
  `POST /watchlists/` had no field for them).
- Watchlists: **Add** did nothing on plain-http hosts other than localhost (e.g. `http://192.168.1.29:4765`):
  `crypto.randomUUID()` only exists in secure contexts. A fallback id generator is used.
- Watchlists: Enter in the value field adds the asset instead of submitting the form; a value typed but not added
  is saved too. Create / edit dialogs show server errors.
- Deleting or editing a watchlist left its items and check history behind in the database.

## 2.1.0 - 2026-11-06

### Security

| Severity | Issue | Fix |
|---|---|---|
| Critical | Analysts could create/update/delete **global** API sources. Repointing a predefined source (e.g. VirusTotal) to an attacker host would send every user's API key there. Combined with the source test endpoint and `api_url` override this was also a full-read SSRF (cloud metadata, Redis, internal services). | Source mutation and test endpoints are admin-only. All outbound requests of the dynamic client go through `app/core/url_guard.py` (http/https only, no private/loopback/link-local/CGNAT/metadata targets, every redirect hop re-validated, no cross-host redirects, 10 MiB response cap). `ALLOW_PRIVATE_API_TARGETS=true` opts out for lab use. |
| High | Default `SECRET_KEY` / `ENCRYPTION_KEY` were silently accepted (also as fallbacks in `docker-compose.yml`), allowing JWT forgery. | Production refuses weak or example secrets; `docker-start.sh` generates them. |
| High | Hard-coded demo users `admin/admin123` etc. were seeded in every environment, including Docker/production. | Demo users only in development or with `SEED_DEFAULT_USERS=true`. Production creates one admin from `DEFAULT_ADMIN_PASSWORD` or a random one-time password. |
| High | Viewers with a *shared* (read-only) watchlist could edit, upload to, re-share or delete it. | Write operations require owner or admin (`WatchlistService._can_modify`). |
| High | Stored HTML injection in HTML/PDF reports (titles, IOC values and third-party tags such as OTX pulse tags were not escaped). | All values HTML-escaped (HTML and ReportLab markup); report preview iframe uses an empty `sandbox`. CSV export neutralises formula injection. |
| High | Rate limiter keyed on client-supplied `X-Forwarded-For` (trivial bypass); login had no rate limit (brute force). | Proxy headers only trusted with `TRUST_PROXY_HEADERS=true`; separate 10/min limit for `/auth/login` and `/auth/refresh`. |
| High | API keys were effectively shared: every IOC query used **all users'** active keys (and quotas), the IOC cache was global (results obtained with one user's keys were served to others for 5 minutes), and admins could list, test and use other users' keys. | Keys are personal: queries use only the caller's own keys (one per source), the IOC cache is scoped per user, and key endpoints are owner-only for every role. |
| Medium | `python-jose` 3.3.0 (CVE-2024-33663 algorithm confusion, CVE-2024-33664 JWE DoS) and unmaintained `passlib`. | Replaced by `PyJWT` (algorithm pinned, `exp/iat/sub/type/iss` required) and `bcrypt`. Existing password hashes remain valid. |
| Medium | CVE endpoints and `/metrics` (recent errors, paths) were unauthenticated. | Authentication required; `/metrics` is admin-only unless `METRICS_PUBLIC=true`. |
| Medium | IOC values were inserted into URL paths unencoded (`../` traversal to other endpoints carrying the user's key); API keys leaked into logs/error messages via URLs. | Path values are percent-encoded; secrets are redacted from errors and logs; AbuseIPDB key moved from query string to header. |
| Medium | CORS `allow_origins=["*"]` default with credentials, `allow_headers=*`. | Explicit allow-list (`CORS_ORIGINS`), `*` rejected. |
| Medium | Redis published on `0.0.0.0:6379` without a password; containers ran as root; `.env` files could be copied into images. | Redis internal-only with `requirepass`; non-root backend and nginx images; `no-new-privileges`; `.dockerignore` excludes secrets, venvs and databases. |
| Low | Username enumeration via login timing; 6-character minimum passwords. | Constant-time dummy hash check; minimum 10 characters for new passwords. |
| Low | Weak / inconsistent security headers. | Strict CSP for API responses and the SPA (no third-party scripts; Leaflet marker images bundled locally), COOP, CORP, `Referrer-Policy`, `server_tokens off`. |

### Bug fixes

- The Fernet key was standard-base64 encoded (Fernet expects URL-safe). Newer Python versions warn and will drop the invalid characters, which would have made every stored API key undecryptable. Fixed without changing the raw key, so existing values still decrypt.
- VirusTotal and OTX never worked: the IOC type was used verbatim in the URL (`/ip/…` instead of `/ip_addresses/…` and `/IPv4/…`). Added `ioc_type_map` / `ioc_value_transform` (VirusTotal URL ids).
- abuse.ch POST bodies were never sent (`body` vs `body_template`) and form bodies were sent as JSON.
- Risk scores were not normalised: AbuseIPDB 25 % or one OTX pulse counted as "high". Sources now declare `risk_score_max`, `risk_score_map` and `risk_score_weight`.
- `/ioc/history/export` was shadowed by `/ioc/history/{query_id}`, and its JSON branch was mis-indented so the export always returned `null`.
- The risk-level filter of the query history and of report creation was shifted by one bucket ("High" returned medium scores, "Low" included clean). It now uses the stored level; "Clean" was added as a filter option and "Critical" means score >= 90 %.
- The old project venv pointed at a previous checkout location (`~/Documents/...`); recreated.
- `get_settings()` built a new `Settings` object on every call (broken `lru_cache`).
- SQLite database in Docker was written outside the volume (lost on rebuild).
- Test suite: in-memory SQLite without `StaticPool` ("no such table"), tests touching the developer database, outdated assertions.
- IOC result page: sources were grouped by score only, so errors, skipped and "not listed" sources were all shown as "Unknown".
- Mobile: the navigation button did nothing (no navigation below the `md` breakpoint); horizontal overflow from long IOC values.

### Threat intelligence sources

- **New:** Shodan InternetDB, GreyNoise Community (no key), ipapi.is, Tor exit nodes, Spamhaus DROP (CIDR), C2IntelFeeds, CIRCL hashlookup, abuse.ch YARAify, RIPEstat, FIRST EPSS.
- **Feed mode:** Feodo Tracker, SSLBL, blocklist.de, GreenSnow, Proofpoint ET, CINS Army and the new feeds are real membership checks (exact, CIDR, URL host) with a 1 h cache instead of downloading the whole list on every query.
- **Now require a (free) key:** URLhaus, ThreatFox, MalwareBazaar (abuse.ch Auth-Key), EmailRep; CIRCL passive DNS/SSL use basic auth. Keyless entries are reported as *skipped* with a hint.
- **Deactivated** (dead, HTML-only or not per-IOC): see `DEPRECATED_SOURCES` in `backend/app/db/source_catalog.py` (ThreatMiner, BufferOver, psbdmp, BGPView, SORBS, PhishStats, …).
- CVE search and detail are enriched with **CISA KEV** (incl. ransomware use, due date, required action) and **EPSS**.

### Features (2.1.0, second batch)

- **Exploit availability for CVEs:** GitHub PoC repositories (nomi-sec/PoC-in-GitHub), Exploit-DB, Nuclei templates and Metasploit modules per CVE, with a "PoC gap" badge and filter (no public exploit found) plus "newest first" sorting. GitHub matches are flagged as unverified (fake PoCs carrying malware are common).
- **Parallel source queries:** each IOC queries its sources concurrently (`IOC_QUERY_CONCURRENCY`, default 8).
- **Bulk IOC input:** paste a report or log; IOCs are extracted (defanged `hxxp`, `[.]`, `[at]` supported; file names are not mistaken for domains) and queried with progress, results exportable as CSV.
- **STIX 2.1 / MISP export** of the IOC query history (deterministic ids, confidence from the normalised score).
- **Webhook notifications** for watchlist alerts (Slack, Microsoft Teams Workflows, generic JSON) per user, minimum severity, test button. Webhook URLs are encrypted at rest and SSRF-checked.
- **Source catalog on the API Keys page:** access tier badges (no key / free key / free tier / on request / paid) and "get your own key" links. Viewers can now manage their own keys.
- **Risk scores fixed in storage and dashboard:** queries store the real mean score instead of a fixed number per level (`unknown` used to be stored as 0.5 and shown as "high"); dashboard buckets follow the risk levels. `scripts/recompute_risk_scores.py` re-derives existing history from the saved raw responses (dry run by default, `--apply` writes and keeps a `.bak`). OTX pulse count alone is capped at "medium".

### Dark web monitoring (new module, menu: IOC Search -> Dark Web)

- **Monitored assets per user**: domains (incl. subdomains, `acme.com.tr` / `evil-acme.com` do not match), e-mail domains and brand keywords (whole word).
- **Sources** (checked live 2026-11-06): ransomware leak-site victim posts via **ransomware.live** and **RansomLook** (aggregators, no Tor connection from our side), infostealer exposure via **Hudson Rock** (free API), the **Have I Been Pwned** breach catalog, and **Telegram** channels.
- **Telegram**: public channels through the `t.me/s/<channel>` web preview (no account), plus optional per-user **MTProto login (Telethon)** for private channels/groups the user joined. API hash and session are encrypted at rest; only message text is stored, attachments are never downloaded.
- Matches become **mentions** (deduplicated by fingerprint; infostealer mentions re-trigger when the numbers change) and **alerts** of the new type `darkweb`, which also reach the user's webhook. At most 15 alerts per scan plus a summary.
- Automatic scan every `DARKWEB_SCAN_INTERVAL_MINUTES` (default 60, minimum 15; `DARKWEB_MONITOR_ENABLED=false` disables it) and a "Scan now" button.
- **Sources tab**: every source with health (last fetch / success, item count, duration, last error), a per-user "use in my scans" switch and an admin "enabled for everyone" switch. Admins can add **custom RSS/Atom or JSON feeds** (JSONPath field mapping, severity per feed, live "Test feed" preview before saving). Feed URLs are SSRF-checked on every redirect hop, capped at 5 MB, XML is parsed with `defusedxml`, and only admins see feed URLs.
- **More built-in sources** (all checked live 2026-11-06, RSS through the same SSRF-safe feed reader):
  - Forums & markets (new category): **Dark Web Informer** (database sales, access listings, leak claims), **DeXpose** (leak-site disclosures); **Daily Dark Web** is included but off by default (no posts since April 2026).
  - Breach reporting: **DataBreaches.net**.
  - Security news, off until an admin enables them: The Cyber Express, Security Affairs, Hackread, The Record.
  - Suggested public Telegram channels with one-click add: Dark Feed, vx-underground.
  - Evaluated and not added: RansomFeed and HackManac (behind bot protection), FalconFeeds (no RSS), ransomwatch (archived), ransomware.live `recentcyberattacks` (1 request/minute and invalid JSON; a second call per scan would also rate-limit the victim feed). Rate-limit responses from the leak aggregators are now reported as source errors.
- Not verified live: the MTProto login against a real Telegram account (covered by mocked tests only).

### Reports

- **Redesigned reports** (`app/services/report_builder.py`): one model rendered as HTML, PDF and CSV. Executive summary (counts per risk level, indicator types, sources with most detections), findings sorted by risk with the evidence that produced them, compact "Clean" and "No verdict" appendices, TLP marking and page numbers. Repeated queries of the same IOC are merged (latest wins). Sources without an opinion are summarised as counts instead of one empty row each: the same 100 queries went from 136 PDF pages to 2.
- Reports now store the resolved query ids, so exporting in another format works (HTML/CSV exports of PDF reports used to be empty). Reports created before this change cannot be re-rendered.
- **Risk aggregation**: overall score = 70 % strongest source + 30 % mean. A confirmed hit (e.g. Feodo C2 blocklist 95 %) is no longer diluted to "medium" by sources that merely know the indicator.

- **Dark web in reports**: new report type **Dark web exposure** (severity summary, sources, monitored assets with mention counts, every finding with evidence and link; filters: sources, minimum severity, date range) and an optional **dark web summary** section in IOC reports (top critical/high mentions). Reports store their selection in `reports.report_spec`, so they re-render in every format.
- **Additive schema sync** (`app/db/schema_sync.py`): new nullable columns on existing tables are added at startup (`create_all` never alters tables). Non-additive changes still need Alembic.

### Session security

- Browser sessions use **httpOnly, SameSite=Strict cookies** (`Secure` in production); tokens are no longer stored in `localStorage`. Bearer tokens keep working for API clients.
- Cookie-authenticated state changes require `X-Requested-With` (CSRF).
- **Refresh token rotation** with reuse detection (a replayed refresh token revokes all sessions of the user), real **logout**, and session revocation on password change, deactivation and deletion. Access token lifetime 15 minutes.
- Development uses the Vite proxy so the browser stays same-origin.

### Dependencies

- Backend: FastAPI 0.162, Starlette 1.10, Pydantic 2.14, SQLAlchemy 2.1, PyJWT 2.15, bcrypt 5, cryptography 50, requests 2.34, ReportLab 5.1, redis 8.1; removed unused WeasyPrint; dev tools moved to `requirements-dev.txt`. Docker base `python:3.13-slim`.
- Frontend: React 19.3, React Router 7, Vite 8, TypeScript 6, **Tailwind CSS 4.3** (CSS-first config, `@tailwindcss/vite`; the custom `light:` variant is now a `@custom-variant`), ESLint 10 (flat config), TanStack Query 5.106, Recharts 3.10, react-leaflet 5, lucide-react 1.x, axios 1.21; removed unused zustand, PostCSS and autoprefixer. Docker base `node:24-alpine` / `nginx-unprivileged:1.29-alpine`.
- `pip-audit` and `npm audit` report no known vulnerabilities; both run in CI.
