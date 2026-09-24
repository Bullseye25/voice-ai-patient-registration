-- =========================================================================
-- CareCloud Patient Registration System — Supabase PostgreSQL Schema
-- Run this in the Supabase Dashboard: SQL Editor -> New Query -> Run
-- =========================================================================

-- 1. Create Patients Table
CREATE TABLE IF NOT EXISTS public.patients (
    patient_id VARCHAR(36) PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    date_of_birth DATE NOT NULL,
    sex VARCHAR(20) NOT NULL,
    phone_number VARCHAR(20) NOT NULL,
    email VARCHAR(255),
    address_line_1 VARCHAR(255) NOT NULL,
    address_line_2 VARCHAR(255),
    city VARCHAR(100) NOT NULL,
    state VARCHAR(2) NOT NULL,
    zip_code VARCHAR(10) NOT NULL,
    insurance_provider VARCHAR(100),
    insurance_member_id VARCHAR(50),
    preferred_language VARCHAR(50) DEFAULT 'English',
    emergency_contact_name VARCHAR(100),
    emergency_contact_phone VARCHAR(20),
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    deleted_at TIMESTAMPTZ DEFAULT NULL
);

-- 2. Create Search & Performance Indexes
CREATE INDEX IF NOT EXISTS idx_patients_last_name ON public.patients (last_name);
CREATE INDEX IF NOT EXISTS idx_patients_phone ON public.patients (phone_number);
CREATE INDEX IF NOT EXISTS idx_patients_dob ON public.patients (date_of_birth);
CREATE INDEX IF NOT EXISTS idx_patients_deleted_at ON public.patients (deleted_at);
CREATE INDEX IF NOT EXISTS idx_patient_search ON public.patients (last_name, date_of_birth, phone_number);

-- 3. Enable Row Level Security (RLS) & Grant Full Access for API
ALTER TABLE public.patients ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow service role and API full access" ON public.patients;
CREATE POLICY "Allow service role and API full access" ON public.patients
    FOR ALL
    TO anon, authenticated, service_role
    USING (true)
    WITH CHECK (true);
