-- Solution 1: Admin Management Database Migration
-- Add admin management columns to Users table

-- Add new columns
ALTER TABLE "Users" 
ADD COLUMN IF NOT EXISTS isAdmin BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS adminId VARCHAR NULL;

-- Add email unique constraint if not exists
DO $$ 
BEGIN
    BEGIN
        ALTER TABLE "Users" ADD CONSTRAINT users_email_unique UNIQUE (email);
    EXCEPTION
        WHEN duplicate_table THEN -- constraint already exists
        NULL;
    END;
END $$;

-- Add self-referential foreign key
DO $$
BEGIN
    BEGIN
        ALTER TABLE "Users" 
        ADD CONSTRAINT users_admin_fk 
        FOREIGN KEY (adminId) REFERENCES "Users"(userId) 
        ON DELETE SET NULL;
    EXCEPTION
        WHEN duplicate_object THEN -- constraint already exists
        NULL;
    END;
END $$;

-- Add check constraints
DO $$
BEGIN
    BEGIN
        ALTER TABLE "Users" 
        ADD CONSTRAINT users_adminid_null_if_admin 
        CHECK (CASE WHEN isAdmin THEN adminId IS NULL ELSE TRUE END);
    EXCEPTION
        WHEN duplicate_object THEN -- constraint already exists
        NULL;
    END;
END $$;

DO $$
BEGIN
    BEGIN
        ALTER TABLE "Users" 
        ADD CONSTRAINT users_not_self_managed 
        CHECK (adminId IS NULL OR adminId <> userId);
    EXCEPTION
        WHEN duplicate_object THEN -- constraint already exists
        NULL;
    END;
END $$;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS users_adminid_idx ON "Users" (adminId);
CREATE INDEX IF NOT EXISTS users_adminid_non_admin_idx ON "Users" (adminId) WHERE isAdmin = FALSE;

-- Add foreign key to photos_path for data integrity (recommended)
DO $$
BEGIN
    BEGIN
        ALTER TABLE photos_path 
        ADD CONSTRAINT photos_user_fk 
        FOREIGN KEY (user_id) REFERENCES "Users"(userId) 
        ON DELETE CASCADE;
    EXCEPTION
        WHEN duplicate_object THEN -- constraint already exists
        NULL;
    END;
END $$;

-- Sample data: Mark existing users as admins (modify as needed)
-- UPDATE "Users" SET isAdmin = TRUE WHERE email IN ('admin@example.com');

COMMIT;
