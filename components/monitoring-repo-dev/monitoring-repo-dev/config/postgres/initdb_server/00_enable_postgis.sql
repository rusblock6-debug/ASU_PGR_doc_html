-- ==============================================================================
-- POSTGIS EXTENSION SETUP
-- ==============================================================================
-- Enable PostGIS in template databases so all new databases inherit it
-- This must run before other database creation scripts
-- ==============================================================================

-- Connect to template1 database
\c template1;

-- Enable PostGIS extensions in template database
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Connect to postgres default database
\c postgres;

-- Enable PostGIS extensions in default postgres database
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Output confirmation
SELECT 'PostGIS version: ' || PostGIS_Version() AS status;

