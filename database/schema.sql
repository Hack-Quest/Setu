-- 🗄️ Supabase PostgreSQL Schema for Setu

-- 1. otps table
CREATE TABLE IF NOT EXISTS otps (
    email TEXT PRIMARY KEY,
    otp TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

-- 2. ngos table
CREATE TABLE IF NOT EXISTS ngos (
    id TEXT PRIMARY KEY,
    ngo_name TEXT,
    owner_name TEXT,
    description TEXT,
    type TEXT,
    location TEXT,
    email TEXT,
    phone TEXT,
    verified BOOLEAN DEFAULT FALSE,
    registered_at TIMESTAMPTZ,
    verified_at TIMESTAMPTZ,
    region TEXT,
    reg_number TEXT,
    lat DOUBLE PRECISION,
    lng DOUBLE PRECISION,
    radius DOUBLE PRECISION
);

-- 3. volunteers_auth table
CREATE TABLE IF NOT EXISTS volunteers_auth (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    name TEXT,
    phone TEXT,
    location TEXT,
    skills TEXT[],
    lat DOUBLE PRECISION,
    lng DOUBLE PRECISION,
    available BOOLEAN DEFAULT TRUE,
    registered_at TIMESTAMPTZ
);

-- 4. volunteers table
CREATE TABLE IF NOT EXISTS volunteers (
    id TEXT PRIMARY KEY,
    name TEXT,
    email TEXT,
    phone TEXT,
    skills TEXT[],
    lat DOUBLE PRECISION,
    lng DOUBLE PRECISION,
    available BOOLEAN DEFAULT TRUE,
    active_assignments INTEGER DEFAULT 0,
    registered_at TIMESTAMPTZ,
    ngo_id TEXT,
    ngo_verified BOOLEAN DEFAULT FALSE,
    specialty TEXT,
    ngo_affiliation TEXT,
    verification_code TEXT,
    updated_at TIMESTAMPTZ
);

-- 5. needs_reports table
CREATE TABLE IF NOT EXISTS needs_reports (
    id TEXT PRIMARY KEY,
    reporter_name TEXT,
    reporter_phone TEXT,
    location_text TEXT,
    description TEXT,
    lat DOUBLE PRECISION,
    lng DOUBLE PRECISION,
    severity TEXT,
    category TEXT,
    status TEXT DEFAULT 'open',
    timestamp TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    trust_score INTEGER,
    summary_en TEXT,
    summary_local TEXT,
    disaster_type TEXT,
    help_needed TEXT
);

-- 6. assignments table
CREATE TABLE IF NOT EXISTS assignments (
    id TEXT PRIMARY KEY,
    need_id TEXT,
    need_description TEXT,
    need_location TEXT,
    volunteer_id TEXT,
    volunteer_name TEXT,
    volunteer_phone TEXT,
    assigned_at TIMESTAMPTZ,
    status TEXT DEFAULT 'assigned',
    resolved_at TIMESTAMPTZ
);
