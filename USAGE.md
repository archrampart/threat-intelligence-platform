# Threat Intelligence Platform - User Guide

Complete guide to using the Threat Intelligence Platform for security teams.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Authentication](#authentication)
3. [IOC Query](#ioc-query)
4. [Dark Web Monitoring](#dark-web-monitoring)
5. [CVE Search](#cve-search)
6. [Watchlist Management](#watchlist-management)
7. [Reports](#reports)
8. [API Keys Management](#api-keys-management)
9. [API Sources Management](#api-sources-management)
10. [User Management](#user-management)
11. [Dashboard](#dashboard)
12. [Alerts and Notifications](#alerts-and-notifications)
13. [Troubleshooting](#troubleshooting)

---

## Getting Started

### Installation Options

#### Option 1: Docker Deployment (Recommended)

The easiest way to get started is using Docker:

```bash
# Clone the repository
git clone https://github.com/archrampart/threat-intelligence-platform.git
cd threat-intelligence-platform

# Start all services
./docker-start.sh
```

This will start:
- **Frontend**: http://localhost:4765
- **API**: http://localhost:4765/api/v1 (proxied by the frontend)
- **API Docs**: http://127.0.0.1:8777/docs (localhost only)

#### Option 2: Local Development

See the [README.md](README.md) for detailed local setup instructions.

### Default Login Credentials

**Local development** (`ENVIRONMENT=development`, or `SEED_DEFAULT_USERS=true`) seeds these demo accounts:

| Username | Password | Role | Permissions |
|----------|----------|------|-------------|
| `admin` | `admin123` | Admin | Full access to all features |
| `analyst` | `analyst123` | Analyst | IOC queries, watchlists, reports |
| `viewer` | `viewer123` | Viewer | Read-only access, can view shared watchlists |

**Docker / production** does not create demo accounts. On first start a single `admin`
account is created with `DEFAULT_ADMIN_PASSWORD` from `.env`, or with a random password
printed once in the backend log (`docker compose logs backend | grep "Initial admin"`).
New passwords must be at least 10 characters.

---

## Authentication

### Login

1. Navigate to the login page
2. Enter your username and password
3. Click "Sign In"
4. You'll be redirected to the Dashboard

### Session Management

- The browser session is kept in **httpOnly cookies**: scripts on the page cannot read your tokens.
- Access tokens are valid for **15 minutes** and are renewed automatically in the background while you
  work (refresh tokens are valid for 7 days and are single use).
- **Logout** (user menu, top right) ends the session on the server, not just in the browser.
- Changing your password signs out all your other sessions. Admins deactivating or deleting a user also
  ends that user's sessions.
- API clients (scripts, Swagger "Authorize") can still use `Authorization: Bearer <token>`.

### Role-Based Access Control

| | Admin | Analyst | Viewer |
|---|:-:|:-:|:-:|
| IOC queries (single and bulk), CVE search, Dark Web monitoring | ✓ | ✓ | ✓ |
| Own API keys and notification webhook | ✓ | ✓ | ✓ |
| Create / share reports, create watchlists | ✓ | ✓ | - |
| See watchlists and reports shared with them | ✓ | ✓ | ✓ (read only) |
| Manage users, global API sources, global dark web sources and custom feeds | ✓ | - | - |

---

## IOC Query

Query Indicators of Compromise (IOCs) across multiple threat intelligence sources.

### Supported IOC Types

- **IP Address**: IPv4 addresses (e.g., `192.168.1.1`)
- **Domain**: Domain names (e.g., `example.com`)
- **URL**: Full URLs (e.g., `https://example.com/malware.exe`)
- **Hash**: MD5, SHA1, SHA256 (e.g., `44d88612fea8a8f36de82e1278abb02f`)
- **Email**: Email addresses (e.g., `suspicious@example.com`)
- **CVE**: Common Vulnerabilities and Exposures (e.g., `CVE-2024-1234`)

### Performing a Query

**Single IOC**

1. Navigate to **IOC Search** from the sidebar
2. Keep **Single IOC** selected, choose the IOC type and enter the value
3. Click **Query IOC**

All sources that support the IOC type are queried in parallel - with your own API keys plus all sources
that need no key.

**Bulk / paste text**

1. Switch to **Bulk / paste text**
2. Paste a report, log, e-mail or plain list. Defanged values are fine (`hxxps://evil[.]com`,
   `1.2.3[.]4`, `user[at]mail[.]ru`); file names such as `invoice.pdf` are not treated as domains.
3. Click **Extract IOCs**, untick anything you do not want to query
4. Click **Query N IOCs** - progress is shown per row; **Stop** pauses, **Export CSV** saves the results

### Understanding Results

Each source's answer is grouped by outcome:

- **High / Medium / Low / Clean** - the source returned a verdict with a score
- **No Signal** - the source answered but had no opinion (e.g. "not listed" in a blocklist)
- **Error** - the request failed or timed out
- **Skipped** - the IOC type is not supported, or the source needs an API key you have not added

The overall score is **70 % of the strongest source + 30 % of the mean** of the sources that returned a
verdict, so a confirmed hit (e.g. a C2 blocklist) is not diluted by sources that merely know the
indicator. Levels: High ≥ 80 %, Medium ≥ 50 %, Low ≥ 20 %, Clean < 20 %. "Unknown" means no source
returned a verdict - that is not the same as clean.

### Query History

- All queries are saved in your history (results are cached for 5 minutes per user)
- Filter by risk level, IOC type, value, source, watchlist and date range
- Export the filtered history as **JSON**, **STIX 2.1** (bundle of indicators for OpenCTI, Sentinel or
  any TAXII client) or **MISP** (event JSON)

### Best Practices

- Check related indicators together (domain and the IPs it resolves to)
- Treat "No verdict" as unknown, not as safe
- Use watchlists for continuous monitoring and Dark Web Monitoring for your own brand and domains

---

## Dark Web Monitoring

Watch ransomware leak sites, infostealer data, breach reports, dark web forum reporting and Telegram
channels for your own domains and brand. Open **Dark Web** in the sidebar (below IOC Search).

### Monitored Assets

On **Monitored assets**, add what to look for (up to 50 per user):

| Type | Matches | Example |
|---|---|---|
| Domain | The domain and its subdomains; `evil-acme.com` and `acme.com.tr` do not match | `acme.com` |
| E-mail domain | Any leaked address on your domain, such as `john@acme.com` (enter the domain only) | `acme.com` |
| E-mail address | One mailbox, matched exactly (`xceo@acme.com` and `ceo@acme.com.tr` do not match) | `ceo@acme.com` |
| Brand / keyword | Whole word, case-insensitive (min. 3 characters) | `Acme Corp` |

Public mail providers (`gmail.com`, `hotmail.com`, `outlook.com`, `yandex.com`, ...) are rejected as domain or
e-mail domain assets: they appear in almost every leak and would flood you with unrelated alerts. Watch a single
mailbox on them with the **E-mail address** type. E-mail addresses are matched in ransomware leak posts, Telegram
messages and RSS/JSON feeds; the domain-level lookups (HIBP breach catalog, Hudson Rock) do not apply to them, and
the content of breach dumps is not searched.

### Sources

The **Sources** tab lists every source with its health (last fetch, last success, item count, duration,
last error):

| Source | Category | Default |
|---|---|---|
| ransomware.live, RansomLook | Ransomware leak-site victim posts | On |
| Hudson Rock | Infostealer-infected employees / users of your domains | On |
| Have I Been Pwned catalog, DataBreaches.net | Breaches | On |
| Dark Web Informer, DeXpose | Forums & markets (data sales, access listings, leak claims) | On |
| Daily Dark Web | Forums & markets (no new posts since April 2026) | Off |
| The Cyber Express, Security Affairs, Hackread, The Record | Security news (noisier) | Off |
| Telegram channels | Your channels (Telegram tab) | On |

- **Use in my scans** switches a source off for your own scans only.
- **Enabled for everyone** (admin) disables a source for all users; it is then not fetched at all.
- **Add a custom feed** (admin): any RSS/Atom or JSON feed. For JSON, map the item list and the title,
  text, link and date fields with JSONPath (e.g. items `$.data[*]`, title `$.name`). Choose the severity
  of matches, click **Test feed** to preview the parsed items, then **Save source**. Feed URLs must be
  public addresses (internal addresses are refused) and are visible to admins only.

The platform never connects to Tor itself; leak sites are covered through aggregators.

### Telegram

- **Public channels**: enter `@channel` or a `t.me` link. The channel's public web preview is read - no
  account needed. Channels without a public preview are refused with a clear message. Suggested channels
  (Dark Feed, vx-underground) can be added with one click.
- **Private channels / groups (optional)**: connect your own Telegram account at the bottom of the tab:
  create an API ID and hash at [my.telegram.org/apps](https://my.telegram.org/apps), enter them with
  your phone number, then the login code (and your two-step password if you use one). Add channels with
  the mode **My Telegram account** (by @username or numeric id). Use a dedicated research account:
  Telegram may restrict accounts that read a lot.
- Only message text is stored. Attachments are never downloaded.

### Mentions and Scans

- Scans run automatically every hour (configurable) and on demand with **Scan now**.
- Every match becomes a **mention** with severity, source, the matched term, a snippet and a link.
  Mentions are de-duplicated; infostealer mentions are raised again when the numbers change.
- Severity: a ransomware victim post whose domain is yours is **critical**; other leak-site, breach,
  infostealer (employees affected) and forum matches are **high**; Telegram brand-keyword matches are
  **medium**.
- New mentions also create **alerts** (type "Dark Web", at most 15 per scan plus a summary) and reach your
  webhook, see [Alerts and Notifications](#alerts-and-notifications).

---

## CVE Search

Search for Common Vulnerabilities and Exposures (CVEs) using the NIST NVD database.

### Searching for CVEs

1. Navigate to **CVE DB** from the sidebar
2. Enter a CVE ID (e.g. `CVE-2024-3400`) or keyword, optionally a year and severity
3. Click **Search**

### Exploit Intelligence

Every result is enriched automatically (no API keys needed):

- **EPSS** (FIRST.org): probability of exploitation in the next 30 days, with percentile
- **CISA KEV**: "Exploited (KEV)" badge, ransomware use, date added, federal due date, required action
- **Public exploits**: Metasploit modules, Exploit-DB entries, Nuclei templates and GitHub PoC
  repositories (top by stars). GitHub repositories are matched by name and **not verified** - fake PoCs
  that ship malware are common; review code in an isolated lab.
- **PoC gap**: no public exploit was found in any of the above

### Filtering and Sorting

- **Known exploited only (CISA KEV)** and **PoC gap (no public exploit)** filters
- Sort by NVD order, **newest first**, **EPSS** or **CVSS**
- Filters and sorting apply to the current results page

Click a CVE to open its details: description, CVSS vector breakdown, Exploit Intelligence panel, public
exploits, affected products and references.

---

## Watchlist Management

Create and manage watchlists to monitor critical assets and automate threat detection.

### Creating a Watchlist

1. Navigate to **Watchlists** from the sidebar
2. Click **Create Watchlist**
3. Enter:
   - **Name**: Descriptive name
   - **Description**: Optional description
   - **Check Interval**: How often to check (in minutes)
   - **Notification Enabled**: Enable/disable alerts
4. Click **Create**

### Adding Items to Watchlist

#### Method 1: Manual Entry

1. Open your watchlist
2. Click **Add Items**
3. Enter IOC values (one per line)
4. Click **Add**

#### Method 2: TXT File Upload

1. Create a TXT file with one IOC per line
2. Open your watchlist
3. Click **Upload TXT File**
4. Select your TXT file
5. Click **Upload**

The platform will automatically detect the IOC type (IP, Domain, URL, or Hash) from each line.

Example TXT file:
```
192.168.1.100
malicious.com
https://example.com/malware.exe
44d88612fea8a8f36de82e1278abb02f
```

You can also add optional descriptions by using tab or space separation:
```
203.0.113.10    build-server01.example.internal
```

This format creates both an IP and Domain asset.

### Checking Watchlists

#### Manual Check

1. Open your watchlist
2. Click **Check Now**
3. Results will appear below

#### Automatic Checking

- Enable automatic checking in watchlist settings
- The platform checks watchlists at the specified interval
- Alerts are generated when threats are detected

#### Check All Watchlists

- Click **Check All** to check all your watchlists at once
- Viewers can check watchlists shared with them

### Sharing Watchlists

1. Open your watchlist
2. Click **Share**
3. Select users to share with
4. Shared users (Viewers) can view and check the watchlist

### Watchlist Status

- **Active**: Items are being monitored
- **Inactive**: Monitoring paused
- **Shared**: Shared with other users

---

## Reports

Generate comprehensive reports from IOC queries and watchlist results.

### Creating a Report

1. Navigate to **Reports** and click **New Report** (admins and analysts)
2. Enter a **Title** and optional **Description**, choose the **Format** (PDF, HTML or JSON)
3. Choose the **Report type**:
   - **IOC queries**: use **Filter options** (watchlist, IOC type, risk level, API source, date range) or
     **select IOC queries** individually; with neither, the **last 100 queries** are used. Tick
     **Include a dark web exposure summary** to append counts per severity/source and the top critical and
     high dark web mentions.
   - **Dark web exposure**: mentions of your monitored assets from the Dark Web page, optionally limited to
     sources (ransomware leaks, infostealer logs, breaches, forums & markets, Telegram, news & custom feeds),
     a minimum severity and the date range in which they were found.
4. Click **Create Report**

### Report Content

- **Executive summary**: counts per risk level, indicator types, average score, sources with most
  detections
- **Findings**: indicators with a risk verdict, sorted by risk, each with the evidence that produced it
  (e.g. "Feodo Tracker 95 % - Listed in Feodo Tracker C2 blocklist") and the source coverage
- **Clean** and **No verdict** appendices in compact tables
- Repeated queries of the same indicator are merged (latest result kept)
- TLP:AMBER marking and page numbers (PDF)

A **dark web exposure report** contains: severity summary, period, mentions per source, the monitored
assets with their number of mentions, and every finding with source, matched term, actor, date, snippet
and link. Dark web reports are marked with a "Dark Web" badge in the report list.

### Formats and Export

- **PDF** (A4) and **HTML** for people, **JSON** for tools; any report can be downloaded as PDF, HTML,
  JSON or CSV - the content is rebuilt from the underlying queries or dark web mentions.
- Reports created before version 2.1 do not store their query list and cannot be converted to another
  format; create them again.

### Sharing Reports

Click the share icon and choose the users who should see the report. Shared users (e.g. viewers) can open
and download it but not change it.

---

## API Keys Management

Manage API keys for threat intelligence sources securely.

### Personal Keys

API keys are **personal**: your queries only use your own keys and quota, and nobody else - admins
included - can see, test or use them. Every role can add keys.

### Adding API Keys

1. Navigate to **API Keys** from the sidebar
2. Use the **Source catalog** at the top: filter by access (No key, Free key, Free tier, On request,
   Paid), follow **Get key** to the provider's sign-up page, then click **Add** on the card - or use
   **Add API Key** and pick the source
3. Enter the key (some sources need a username/password instead), choose the update mode (Manual is
   recommended to save quota) and save
4. **Add All Free Sources** adds every source that needs no key in one go

> abuse.ch (URLhaus, ThreatFox, MalwareBazaar, YARAify) requires a free Auth-Key since 2025. Sources that
> need a key you have not added are shown as **Skipped** in query results with a hint.

### API Key Security

- Keys are encrypted at rest (Fernet: AES-128-CBC + HMAC-SHA256) and never returned by the API
- Keys are redacted from logs and error messages

### Testing API Keys

Click **Test** next to a key: the platform runs a sample query and stores the result (valid / invalid).

---

## API Sources Management

The source definitions (URL templates, authentication, response parsing) are global and managed by
**admins through the API** (`/api/v1/api-sources`, see Swagger at `/docs`); there is no sidebar page.
Every user can read the catalog on the API Keys page.

### Adding a Custom API Source

`POST /api/v1/api-sources/` with:

```json
{
  "name": "custom_source",
  "display_name": "Custom Threat Intel",
  "api_type": "custom",
  "base_url": "https://api.example.com/v1",
  "authentication_type": "api_key",
  "supported_ioc_types": ["ip", "domain"],
  "request_config": {
    "method": "GET",
    "endpoint_template": "/check/{ioc_type}/{ioc_value}",
    "headers": {"X-API-Key": "{api_key}"},
    "ioc_type_map": {"ip": "ipv4"}
  },
  "response_config": {
    "risk_score_path": "data.threat_score",
    "risk_score_max": 100,
    "data_path": "data",
    "not_found_ok": true
  }
}
```

- Placeholders: `{ioc_type}`, `{ioc_value}`, `{hash_type}` (md5/sha1/sha256), `{api_key}`,
  `{username}`, `{password}`
- Risk normalisation: `risk_score_max` (divide), `risk_score_map` (e.g. `{"malicious": 0.9}`),
  `risk_score_weight`; `not_found_ok` treats HTTP 404 as "not found"
- Feed sources: `"mode": "feed"` checks membership in a downloadable list (plain lines, CSV column or
  JSON lines, CIDR supported)
- `base_url` must be a public address: internal, loopback and cloud-metadata addresses are refused, and
  redirects to other hosts are not followed

### Testing API Sources

`POST /api/v1/api-sources/{id}/test` with a sample IOC and key verifies connectivity, authentication and
score extraction.

---

## User Management

Manage users, roles, and permissions (Admin only).

### Creating a User

New passwords must be at least 10 characters.

1. Navigate to **User Management** from the sidebar
2. Click **Add User**
3. Enter:
   - **Username**: Unique username
   - **Email**: User email address
   - **Password**: Initial password
   - **Role**: Admin, Analyst, or Viewer
   - **Full Name**: Optional full name
4. Click **Create**

### User Roles

#### Admin
- Full access to all features
- User management
- Global API sources, dark web sources and custom feeds
- Own API keys (keys are personal - admins cannot see other users' keys)

#### Analyst
- IOC queries, CVE search, Dark Web monitoring
- Watchlist management and report generation
- Own API keys
- Cannot manage users or global sources

#### Viewer
- IOC queries, CVE search and Dark Web monitoring
- Own API keys and notification webhook
- Read-only access to watchlists and reports shared with them
- Cannot create watchlists or reports

### Editing Users

1. Find the user in the user list
2. Click **Edit**
3. Update information
4. Click **Save**

### Resetting Passwords

1. Open user details
2. Click **Reset Password**
3. Enter new password
4. Click **Update**

---

## Dashboard

Get an overview of platform activity and statistics.

### Dashboard Widgets

- Query, API, watchlist and alert counters
- **Risk cards**: Critical (score ≥ 90 %), High (≥ 80 %), Medium (≥ 50 %), Low (< 50 %) and Unknown
  (no source returned a verdict)
- Query trend, risk distribution, IOC types, CVE summary, API status, watchlist summary, threat map

### Customizing Dashboard

Click **Customize** to show or hide widgets; the choice is stored in your browser.

> After upgrading from 2.0, run `python -m scripts.recompute_risk_scores --apply` once (see README):
> older versions stored "unknown" results as 0.5, which the dashboard counted as high risk.

---

## Alerts and Notifications

### Viewing Alerts

1. Navigate to **Alerts** from the sidebar (the bell in the top bar shows the unread count)
2. Filter by read state, severity and type (Watchlist, IOC Query, CVE, System, **Dark Web**)
3. Mark as read / unread, mark all as read, or delete

### Alert Sources

- **Watchlists**: risk changes of watchlist items (enable notifications on the watchlist)
- **Dark Web**: new mentions of your monitored assets

### Webhook Notifications (Slack, Teams, generic)

1. Open the user menu (top right) → **Notifications**
2. Enter your webhook URL (https), choose **Slack**, **Microsoft Teams (Workflows)** or **Generic JSON**,
   and the minimum severity
3. Tick **Send alerts to my webhook**, click **Save**, then **Send test**

The URL is stored encrypted and is never shown again (only a masked hint). Internal addresses are
refused. E-mail delivery is not built in; use a Slack/Teams/generic webhook (e.g. to an automation tool)
instead.

---

## Troubleshooting

### Common Issues

#### Logged Out After Updating / "Not authenticated"

Sessions moved from localStorage tokens to cookies in 2.1: everyone signs in once after the upgrade. In
local development open the app through the Vite dev server (`http://localhost:5173`) so the API is
same-origin. When serving Docker over plain HTTP on a host other than localhost, set
`COOKIE_SECURE=false`.

#### Too Many Authentication Attempts

The login and refresh endpoints allow 10 requests per minute per client; wait a minute.

#### Cannot Login

- **Check credentials**: Ensure username and password are correct
- **Check database**: Ensure backend is running and database is initialized
- **Check logs**: Review backend logs for errors

#### IOC Query Returns No Results / Sources "Skipped"

- **Check API keys**: Keys are personal - add your own on the API Keys page; "Skipped ... requires an API
  key" names the source
- **Check API source status**: Verify API sources are online
- **Check IOC format**: Ensure IOC value is in correct format
- **Check rate limits**: Some APIs have rate limits

#### Dark Web Source Shows "Failing"

Open **Dark Web → Sources**: the card shows the last error (e.g. a rate limit such as "1 per 1
minute" from ransomware.live, or an unreachable feed). Other sources keep working; the next scan retries.

#### Watchlist Not Updating

- **Check check interval**: Verify automatic checking is enabled
- **Check watchlist status**: Ensure watchlist is active
- **Check API keys**: Verify API keys are configured
- **Check logs**: Review backend logs for errors

#### Frontend Not Loading

- **Check backend**: Ensure backend API is running
- **Check network**: Verify frontend can reach backend
- **Check browser console**: Look for JavaScript errors
- **Clear browser cache**: Try hard refresh (Ctrl+Shift+R)

### Getting Help

1. Check the [GitHub Issues](https://github.com/archrampart/threat-intelligence-platform/issues)
2. Review the [README.md](README.md) for installation instructions
3. Check the [API Documentation](http://127.0.0.1:8777/docs) for API details
4. Report bugs or request features on GitHub

### Logs

#### Docker Logs

```bash
# All services
docker-compose logs -f

# Backend only
docker-compose logs -f backend

# Frontend only
docker-compose logs -f frontend
```

#### Docker Update Issues

If you updated the application but don't see changes, try rebuilding without cache:

```bash
docker-compose down -v
git pull
docker-compose build --no-cache
docker-compose up -d
```

#### Local Development Logs

- Backend logs: Check terminal where backend is running
- Frontend logs: Check browser developer console

---

## Best Practices

### Security

- Do not enable demo users (`SEED_DEFAULT_USERS`) outside a lab; set `DEFAULT_ADMIN_PASSWORD` or note the
  generated one-time admin password
- Use strong, unique passwords
- Regularly rotate your API keys (they are personal) and webhook URLs
- Limit user access based on role
- Keep `SECRET_KEY` / `ENCRYPTION_KEY` secret and backed up: changing `ENCRYPTION_KEY` makes stored API
  keys unreadable

### IOC Analysis

- Query multiple sources for critical IOCs
- Verify false positives before taking action
- Document investigation findings
- Keep IOC history for trend analysis

### Watchlist Management

- Organize watchlists by category (e.g., Critical Assets, Threat Actors)
- Set appropriate check intervals to balance monitoring and API usage
- Regularly review and update watchlist items
- Share watchlists with relevant team members

### Performance

- Use Redis caching for faster queries
- Limit watchlist check frequency to avoid rate limits
- Archive old IOC queries periodically
- Monitor API usage and rate limits

---

## Support

For questions, issues, or contributions:

- **GitHub**: https://github.com/archrampart/threat-intelligence-platform
- **Issues**: https://github.com/archrampart/threat-intelligence-platform/issues
- **Email**: security@archrampart.com

