# Solution 1: Admin Management Implementation

This implements Solution 1 from the admin design document - using a single Users table with self-referential foreign key for admin management.

## What's Added

### Database Changes
- **isAdmin**: Boolean column to mark admin users
- **adminId**: Self-referential FK to Users.userId for admin managing this user
- Constraints to prevent cycles and ensure data integrity
- Indexes for performance

### Helper Functions (`database.py`)
- `is_admin(user)`: Check if user is admin
- `admin_controls_elderly(admin_id, elderly_id, db)`: Verify admin controls elderly
- `fetch_managed_users(admin_id, db)`: Get elderly managed by admin
- `create_elderly_user(admin_id, elderly_data, db)`: Create elderly under admin
- `verify_admin_token()`: FastAPI dependency for admin auth
- `authorize_admin_controls()`: FastAPI dependency for elderly access

### API Models (`admin_models.py`)
- `ElderlyUser`: Response model for elderly user data
- `CreateElderlyRequest`: Request model for creating elderly
- `AdminActionResponse`: Generic response for admin actions

### Admin Management Router (`routers/admin.py`)
- `GET /admin/elderly`: List managed elderly (paginated)
- `POST /admin/elderly`: Create new elderly user
- `GET /admin/elderly/{elderly_id}`: Get elderly details
- `DELETE /admin/elderly/{elderly_id}`: Remove from management

### Updated Login Response (`routers/login.py`)
- Added `isAdmin` field to login response for frontend routing

## Usage Examples

### 1. Admin Login
```bash
POST /login
{
  "email": "admin@example.com",
  "password": "adminpass"
}

Response:
{
  "userId": "admin-uuid",
  "token": "jwt-token",
  "message": "Login successful",
  "isAdmin": true
}
```

### 2. Create Elderly User
```bash
POST /admin/elderly
Authorization: Bearer <admin-jwt>
{
  "email": "elderly1@example.com",
  "fullName": "John Doe",
  "phoneNumber": "+1234567890",
  "ageGroup": "elderly"
}

Response:
{
  "message": "Elderly user created successfully",
  "elderly_id": "elderly-uuid",
  "action": "create"
}
```

### 3. List Managed Elderly
```bash
GET /admin/elderly?page=1&limit=10
Authorization: Bearer <admin-jwt>

Response:
{
  "elderly": [
    {
      "userId": "elderly-uuid",
      "username": "elderly_admin123_abc12345",
      "email": "elderly1@example.com",
      "fullName": "John Doe",
      "createdAt": "2025-08-12T10:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "limit": 10
}
```

## Database Migration

Run the migration script:
```bash
psql -h localhost -U your_user -d your_db -f migrations/001_add_admin_management.sql
```

Or manually execute the SQL commands in your database.

## Next Steps

### To Update Existing Endpoints (analyze, upload, etc.):

1. **Add admin authorization pattern**:
```python
@router.post("/admin/elderly/{elderly_id}/analyze")
def admin_analyze_for_elderly(
    elderly_id: str,
    image: UploadFile = File(...),
    admin_id: str = Depends(verify_admin_token),
    db: Session = Depends(get_db)
):
    authorize_admin_controls(admin_id, elderly_id, db)
    # Continue with existing analyze logic using elderly_id
```

2. **Update existing endpoints to accept target_user_id**:
```python
@router.post("/analyze/{user_id}")  # Keep for self-service
def analyze_photos(
    user_id: str,
    image: UploadFile = File(...),
    current_user_id: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    # Allow self-access or admin access
    if current_user_id != user_id:
        current_user = fetch_user_by_id(current_user_id, db)
        if not is_admin(current_user):
            raise HTTPException(403, "Access denied")
        authorize_admin_controls(current_user_id, user_id, db)
    
    # Continue with analysis using user_id
```

### Required Changes:
- [ ] Run database migration
- [ ] Update main.py to include admin router
- [ ] Update analyze.py endpoint
- [ ] Update photoUpload.py endpoint  
- [ ] Update retrieve.py endpoint
- [ ] Update update.py endpoint
- [ ] Test with admin and elderly users

## Testing

1. Create an admin user and set `isAdmin = TRUE`
2. Use admin login to get JWT
3. Create elderly users via `/admin/elderly`
4. Test admin access to elderly data
5. Verify non-admins cannot access other users

## Security Notes

- Elderly users should not log in (password = NULL)
- Admin tokens required for all management operations
- Self-referential FK prevents orphaned relationships
- Check constraints prevent admin cycles
