# Threat Intelligence Platform - User Guide

Complete guide to using the Threat Intelligence Platform for security teams.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Authentication](#authentication)
3. [IOC Query](#ioc-query)
4. [CVE Search](#cve-search)
5. [Watchlist Management](#watchlist-management)
6. [Reports](#reports)
7. [API Keys Management](#api-keys-management)
8. [API Sources Management](#api-sources-management)
9. [User Management](#user-management)
10. [Dashboard](#dashboard)
11. [Alerts](#alerts)
12. [Troubleshooting](#troubleshooting)

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
- **Backend API**: http://localhost:8777
- **API Docs**: http://localhost:8777/docs

#### Option 2: Local Development

See the [README.md](README.md) for detailed local setup instructions.

### Default Login Credentials

After starting the platform, use these credentials:

| Username | Password | Role | Permissions |
|----------|----------|------|-------------|
| `admin` | `admin123` | Admin | Full access to all features |
| `analyst` | `analyst123` | Analyst | IOC queries, watchlists, reports |
| `viewer` | `viewer123` | Viewer | Read-only access, can view shared watchlists |

**⚠️ Important**: Change these default passwords immediately after first login!

---

## Authentication

### Login

1. Navigate to the login page
2. Enter your username and password
3. Click "Sign In"
4. You'll be redirected to the Dashboard

### Session Management

- JWT tokens are valid for **30 minutes**
- You'll be automatically logged out after inactivity
- To log out, click the user menu in the top-right corner and select "Logout"

### Role-Based Access Control

- **Admin**: Full access to all features including user management
- **Analyst**: Can perform IOC queries, manage watchlists, create reports
- **Viewer**: Read-only access, can view shared watchlists and query results

---

## IOC Query

Query Indicators of Compromise (IOCs) across multiple threat intelligence sources.

### Supported IOC Types

- **IP Address**: IPv4 addresses (e.g., `192.168.1.1`)
- **Domain**: Domain names (e.g., `example.com`)
- **URL**: Full URLs (e.g., `https://example.com/malware.exe`)
- **Hash**: MD5, SHA1, SHA256 (e.g., `44d88612fea8a8f36de82e1278abb02f`)

### Performing a Query

1. Navigate to **IOC Search** from the sidebar
2. Select the IOC type (IP, Domain, URL, or Hash)
3. Enter the IOC value
4. Click **Search**

### Understanding Results

Results are grouped by risk level:

- **🔴 High Risk**: Risk score ≥ 0.8
- **🟡 Medium Risk**: Risk score ≥ 0.5
- **🟢 Low Risk**: Risk score ≥ 0.2
- **⚪ Clean**: Risk score < 0.2
- **❓ Unknown**: No risk score available
- **⚠️ Error**: API source returned an error

### Query History

- All queries are saved in your history
- Filter by IOC type, value, date range, or source
- Export history as CSV or JSON
- Share query results with team members

### Best Practices

- Check multiple IOC types for the same indicator (e.g., domain and IP)
- Review query history to identify patterns
- Use watchlists for automated monitoring

---

## CVE Search

Search for Common Vulnerabilities and Exposures (CVEs) using the NIST NVD database.

### Searching for CVEs

1. Navigate to **CVE Database** from the sidebar
2. Enter a CVE ID (e.g., `CVE-2024-1234`) or keyword
3. Click **Search**

### CVE Details

Each CVE entry includes:
- **CVE ID**: Unique identifier
- **Description**: Vulnerability description
- **CVSS Score**: Base score (0.0 - 10.0)
- **Severity**: Critical, High, Medium, Low
- **Published Date**: When the CVE was published
- **References**: Links to advisories and patches

### Filtering and Sorting

- Filter by CVSS score range
- Sort by date, score, or severity
- Search by keyword in description

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
172.31.22.44    devops-runner01.company.local
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

1. Navigate to **Reports** from the sidebar
2. Click **Generate Report**
3. Select:
   - **Report Type**: IOC Query Report or Watchlist Report
   - **Data Source**: Select query or watchlist
   - **Format**: PDF, HTML, or JSON
4. Click **Generate**

### Report Formats

#### PDF Report
- Professional formatted document
- Includes charts and visualizations
- Suitable for sharing with stakeholders

#### HTML Report
- Interactive web format
- Clickable links and expandable sections
- Can be opened in any browser

#### JSON Report
- Machine-readable format
- Includes all raw data
- Useful for integration with other tools

### Report Content

Reports include:
- **Title and Description**: Report title and optional description
- **Metadata**: Generated timestamp and total IOC queries count
- **IOC Queries Table**: Detailed table with:
  - IOC Type
  - IOC Value
  - Risk Score
  - Status
  - Query Date

---

## API Keys Management

Manage API keys for threat intelligence sources securely.

### Adding API Keys

1. Navigate to **API Keys** from the sidebar
2. Click **Add API Key**
3. Select the **API Source** (e.g., VirusTotal, AbuseIPDB)
4. Enter your **API Key**
5. Select **Update Mode**:
   - **Auto**: Automatically use for queries
   - **Manual**: Use only when explicitly requested
6. Click **Save**

### Supported API Sources

- **VirusTotal**: File, URL, IP, and domain analysis
  - Requires: API key
  - Rate limit: 500 requests/day (free tier)
- **AbuseIPDB**: IP abuse reports and blacklist checking
  - Requires: API key
  - Rate limit: 1000 requests/day (free tier)
- **OTX (AlienVault)**: Community-based threat intelligence
  - Requires: API key
  - Rate limit: 10,000 requests/day (free tier)
- **NIST NVD**: CVE database
  - No API key required
  - Rate limit: 5 requests/second

### API Key Security

- All API keys are encrypted with AES-256
- Keys are stored securely in the database
- Only admins and analysts can manage API keys

### Testing API Keys

1. Click **Test** next to an API key
2. The platform will verify the key with the API source
3. Status will be updated (Active/Invalid)

---

## API Sources Management

Add custom threat intelligence API sources to extend the platform's capabilities.

### Adding a Custom API Source

1. Navigate to **API Sources** from the sidebar
2. Click **Add API Source**
3. Fill in:
   - **Name**: Internal name (e.g., `custom_source`)
   - **Display Name**: User-friendly name (e.g., `Custom Threat Intel`)
   - **Description**: Brief description
   - **Base URL**: API endpoint (e.g., `https://api.example.com/v1`)
   - **Authentication Type**: API Key, Bearer Token, Basic Auth, or None
   - **Supported IOC Types**: IP, Domain, URL, Hash, CVE
   - **Request Configuration**: HTTP method, endpoint template, headers
   - **Response Configuration**: Risk score path, data path
4. Click **Test** to verify the configuration
5. Click **Save**

### API Source Configuration

#### Request Configuration

```json
{
  "method": "GET",
  "endpoint_template": "/check/{ioc_type}/{ioc_value}",
  "headers": {
    "X-API-Key": "{api_key}"
  }
}
```

#### Response Configuration

```json
{
  "risk_score_path": "data.threat_score",
  "status_path": "data.status",
  "data_path": "data"
}
```

### Testing API Sources

Use the **Test** button to verify:
- API connectivity
- Authentication
- Response format
- Risk score extraction

---

## User Management

Manage users, roles, and permissions (Admin only).

### Creating a User

1. Navigate to **Users** from the sidebar
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
- System configuration
- API key management

#### Analyst
- IOC queries
- Watchlist management
- Report generation
- API key management
- Cannot manage users

#### Viewer
- Read-only access
- View IOC queries
- View shared watchlists
- Cannot create or modify data

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

- **Total IOC Queries**: Number of queries performed
- **Active Watchlists**: Number of active watchlists
- **Total Alerts**: Number of alerts generated
- **High Risk IOCs**: Number of high-risk IOCs detected

### Charts and Visualizations

- **Query Activity**: Line chart showing query trends
- **Risk Distribution**: Pie chart of risk levels
- **Top Sources**: Bar chart of most-used API sources
- **Watchlist Status**: Status of all watchlists

### Customizing Dashboard

- Rearrange widgets by dragging
- Click **Edit** to modify widget configuration
- Add or remove widgets based on your needs

---

## Alerts

View and manage alerts generated by watchlist monitoring.

### Viewing Alerts

1. Navigate to **Alerts** from the sidebar
2. Alerts are listed by date (newest first)
3. Filter by:
   - Alert type
   - Severity
   - Watchlist
   - Date range

### Alert Types

- **Threat Detected**: High-risk IOC found in watchlist
- **Watchlist Check Failed**: Error during automatic check
- **API Source Error**: API source returned an error

### Managing Alerts

- **Mark as Read**: Dismiss individual alerts
- **Mark All as Read**: Dismiss all alerts
- **Delete**: Remove alerts from history

### Alert Notifications

Alerts are created in the platform when threats are detected in watchlists. To enable alerts:
1. Go to watchlist settings
2. Enable **Notification Enabled**
3. Alerts will be created in the Alerts section when threats are detected

Note: Alerts are stored in the platform's database and displayed in the Alerts section. Email notifications are not currently supported.

---

## Troubleshooting

### Common Issues

#### Cannot Login

- **Check credentials**: Ensure username and password are correct
- **Check database**: Ensure backend is running and database is initialized
- **Check logs**: Review backend logs for errors

#### IOC Query Returns No Results

- **Check API keys**: Ensure API keys are configured and active
- **Check API source status**: Verify API sources are online
- **Check IOC format**: Ensure IOC value is in correct format
- **Check rate limits**: Some APIs have rate limits

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
3. Check the [API Documentation](http://localhost:8777/docs) for API details
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

#### Local Development Logs

- Backend logs: Check terminal where backend is running
- Frontend logs: Check browser developer console

---

## Best Practices

### Security

- Change default passwords immediately
- Use strong, unique passwords
- Regularly rotate API keys
- Limit user access based on role
- Enable encryption for sensitive data

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

