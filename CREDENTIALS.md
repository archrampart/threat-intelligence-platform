# Default Login Credentials

## Development Users

The following default users are created automatically on first startup:

### Admin User
- **Username:** `admin`
- **Password:** `admin123`
- **Role:** ADMIN
- **Email:** admin@threatintel.local

### Analyst User
- **Username:** `analyst`
- **Password:** `analyst123`
- **Role:** ANALYST
- **Email:** analyst@threatintel.local

### Viewer User
- **Username:** `viewer`
- **Password:** `viewer123`
- **Role:** VIEWER
- **Email:** viewer@threatintel.local

## User Roles

- **ADMIN**: Full access to all features including user management, API key management, and system configuration
- **ANALYST**: Can create IOC queries, watchlists, reports, and manage API keys
- **VIEWER**: Read-only access to view IOC queries, CVE data, and reports

## Important Notes

⚠️ **These credentials are for development only!**

- Change default passwords in production
- Create your own users via the Register page
- Default users are only created if they don't already exist

## Register New User

You can also register a new user via the frontend:
1. Go to `/register` page
2. Fill in username, email, password, and select role
3. Click "Register"











