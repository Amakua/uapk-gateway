-- UAPK Gateway PostgreSQL initialization script
-- This script runs on first database creation

-- Enable useful extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE 'UAPK Gateway database initialized successfully';
END $$;
