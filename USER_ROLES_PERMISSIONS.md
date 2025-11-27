# User Roles and Permissions

This documentation describes in detail the permissions of user roles (Admin, Analyst, Viewer) in the system.

## Roles Overview

The system has three main user roles:
- **ADMIN**: Full access
- **ANALYST**: Management permissions (except user management)
- **VIEWER**: Read-only permissions

---

## 🔴 ADMIN (Administrator)

### General Permissions
- Full access to all system features
- User management (create, edit, delete, change roles)
- System configuration

### Page Access
- ✅ **Dashboard**: Full access
- ✅ **IOC Search**: Full access (query + view history)
- ✅ **CVE DB**: Full access
- ✅ **Watchlist**: Full access (create, edit, delete)
- ✅ **Reports**: Full access (create, view, delete)
- ✅ **API Keys**: Full access (create, edit, delete, test)
- ✅ **User Management**: Full access (admin only)
- ✅ **Alerts**: Full access

### API Endpoint Permissions

#### User Management (Admin Only)
- `GET /users` - List users
- `GET /users/{user_id}` - User details
- `POST /users` - Create new user
- `PUT /users/{user_id}` - Update user
- `DELETE /users/{user_id}` - Delete user (soft delete)
- `DELETE /users/{user_id}/hard` - Permanently delete user
- `PUT /users/{user_id}/activate` - Activate/deactivate user
- `PUT /users/{user_id}/role` - Change user role

#### API Keys (Admin + Analyst)
- `GET /api-keys` - List API keys
- `GET /api-keys/{api_key_id}` - API key details
- `POST /api-keys` - Create new API key
- `PUT /api-keys/{api_key_id}` - Update API key
- `DELETE /api-keys/{api_key_id}` - Delete API key
- `POST /api-keys/{api_key_id}/test` - Test API key
- `GET /api-keys/sources` - List API sources

#### API Sources (Admin + Analyst)
- `GET /api-sources` - List API sources
- `GET /api-sources/{source_id}` - API source details
- `POST /api-sources` - Create new API source
- `PUT /api-sources/{source_id}` - Update API source
- `DELETE /api-sources/{source_id}` - Delete API source
- `POST /api-sources/{source_id}/test` - Test API source

#### IOC Operations (Admin + Analyst)
- `POST /ioc/query` - Query IOC
- `GET /ioc/history` - View IOC query history
- `GET /ioc/history/export` - Export IOC history

#### Reports (Admin + Analyst)
- `GET /reports` - List reports
- `GET /reports/{report_id}` - Report details
- `POST /reports` - Create new report
- `PUT /reports/{report_id}` - Update report
- `DELETE /reports/{report_id}` - Delete report

### Special Permissions
- Create, edit, delete users
- Change user roles
- Activate/deactivate users
- View and export IOC query history
- Create, edit, delete watchlists
- Create and delete reports

---

## 🔵 ANALYST (Analyst)

### General Permissions
- IOC querying and analysis
- Watchlist management
- Report creation and management
- API key management
- User management **NOT ALLOWED**

### Page Access
- ✅ **Dashboard**: Full access
- ✅ **IOC Search**: Full access (query + view history)
- ✅ **CVE DB**: Full access
- ✅ **Watchlist**: Full access (create, edit, delete)
- ✅ **Reports**: Full access (create, view, delete)
- ✅ **API Keys**: Full access (create, edit, delete, test)
- ❌ **User Management**: No access (admin only)
- ✅ **Alerts**: Full access

### API Endpoint Permissions

#### API Keys (Admin + Analyst)
- `GET /api-keys` - List API keys
- `GET /api-keys/{api_key_id}` - API key details
- `POST /api-keys` - Create new API key
- `PUT /api-keys/{api_key_id}` - Update API key
- `DELETE /api-keys/{api_key_id}` - Delete API key
- `POST /api-keys/{api_key_id}/test` - Test API key
- `GET /api-keys/sources` - List API sources

#### API Sources (Admin + Analyst)
- `GET /api-sources` - List API sources
- `GET /api-sources/{source_id}` - API source details
- `POST /api-sources` - Create new API source
- `PUT /api-sources/{source_id}` - Update API source
- `DELETE /api-sources/{source_id}` - Delete API source
- `POST /api-sources/{source_id}/test` - Test API source

#### IOC Operations (Admin + Analyst)
- `POST /ioc/query` - Query IOC
- `GET /ioc/history` - View IOC query history
- `GET /ioc/history/export` - Export IOC history

#### Reports (Admin + Analyst)
- `GET /reports` - List reports
- `GET /reports/{report_id}` - Report details
- `POST /reports` - Create new report
- `PUT /reports/{report_id}` - Update report
- `DELETE /reports/{report_id}` - Delete report

### Special Permissions
- View and export IOC query history
- Create, edit, delete watchlists
- Create and delete reports
- API key management

### Restrictions
- ❌ Cannot manage users
- ❌ Cannot create, edit, or delete users
- ❌ Cannot change user roles

---

## 🟢 VIEWER (Viewer)

### General Permissions
- Read-only permissions
- Cannot perform data analysis or reporting
- Cannot perform management operations

### Page Access
- ✅ **Dashboard**: View only
- ✅ **IOC Search**: Can query (cannot view history)
- ✅ **CVE DB**: View only
- ✅ **Watchlist**: View only (cannot manage)
- ✅ **Reports**: View only (cannot create/delete)
- ❌ **API Keys**: No access
- ❌ **User Management**: No access
- ✅ **Alerts**: View only

### API Endpoint Permissions

#### IOC Operations (Limited)
- `POST /ioc/query` - Can query IOC
- ❌ `GET /ioc/history` - Cannot view IOC query history
- ❌ `GET /ioc/history/export` - Cannot export IOC history

#### Reports (View Only)
- `GET /reports` - View report list
- `GET /reports/{report_id}` - View report details
- ❌ `POST /reports` - Cannot create reports
- ❌ `PUT /reports/{report_id}` - Cannot update reports
- ❌ `DELETE /reports/{report_id}` - Cannot delete reports

### Special Permissions
- Can query IOC
- Can view dashboard
- Can view CVE database
- Can view watchlists (cannot manage)
- Can view reports (cannot create/delete)
- Can view alerts

### Restrictions
- ❌ Cannot view IOC query history
- ❌ Cannot export IOC history
- ❌ Cannot create, edit, or delete watchlists
- ❌ Cannot create, update, or delete reports
- ❌ Cannot manage API keys
- ❌ Cannot manage API sources
- ❌ Cannot manage users

---

## Permission Comparison Table

| Feature | ADMIN | ANALYST | VIEWER |
|---------|-------|---------|--------|
| **Dashboard View** | ✅ | ✅ | ✅ |
| **IOC Query** | ✅ | ✅ | ✅ |
| **IOC History View** | ✅ | ✅ | ❌ |
| **IOC History Export** | ✅ | ✅ | ❌ |
| **CVE DB View** | ✅ | ✅ | ✅ |
| **Watchlist View** | ✅ | ✅ | ✅ |
| **Watchlist Management** | ✅ | ✅ | ❌ |
| **Report View** | ✅ | ✅ | ✅ |
| **Report Create/Delete** | ✅ | ✅ | ❌ |
| **API Key Management** | ✅ | ✅ | ❌ |
| **API Source Management** | ✅ | ✅ | ❌ |
| **User Management** | ✅ | ❌ | ❌ |
| **Alert View** | ✅ | ✅ | ✅ |

---

## Notes

1. **Self-Account Deletion**: No user (including admin) can delete their own account. This security measure applies to both soft delete and hard delete operations.

2. **Role Hierarchy**: 
   - ADMIN > ANALYST > VIEWER
   - Each role has all permissions of roles below it (except user management)

3. **Frontend Controls**: Some UI elements are hidden/shown based on role in the frontend:
   - IOC History: Only Admin and Analyst can see
   - Watchlist Management: Only Admin and Analyst can do
   - Report Create/Delete: Only Admin and Analyst can do

4. **Backend Controls**: All critical operations are protected by the `require_role` dependency in the backend.

---

## Security Notes

- All authorization checks are performed in both frontend and backend
- Backend controls are the primary security layer
- Frontend controls are only for UX purposes
- API endpoints do not work without role checks
- Users cannot delete their own accounts (security measure)
