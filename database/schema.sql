-- Lash Zone London AI Receptionist - Database Schema
-- Run this in Supabase SQL Editor to create all required tables

-- ===================
-- CALLS TABLE
-- ===================
CREATE TABLE IF NOT EXISTS calls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_sid VARCHAR(255),
    caller_number VARCHAR(50),
    duration_seconds INTEGER DEFAULT 0,
    outcome VARCHAR(100),
    transcript_json JSONB DEFAULT '[]'::jsonb,
    recording_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for searching
CREATE INDEX IF NOT EXISTS idx_calls_caller ON calls(caller_number);
CREATE INDEX IF NOT EXISTS idx_calls_created ON calls(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_calls_outcome ON calls(outcome);

-- Enable RLS
ALTER TABLE calls ENABLE ROW LEVEL SECURITY;

-- Allow anon read
CREATE POLICY "Allow read for authenticated" ON calls
    FOR SELECT TO anon USING (true);

-- Allow anon insert (for API)
CREATE POLICY "Allow insert for anon" ON calls
    FOR INSERT TO anon WITH CHECK (true);

-- ===================
-- CLIENTS TABLE
-- ===================
CREATE TABLE IF NOT EXISTS clients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255),
    phone VARCHAR(50) UNIQUE,
    email VARCHAR(255),
    preferred_service VARCHAR(255),
    visit_count INTEGER DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_clients_phone ON clients(phone);
CREATE INDEX IF NOT EXISTS idx_clients_name ON clients(name);

ALTER TABLE clients ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow read for anon" ON clients
    FOR SELECT TO anon USING (true);

CREATE POLICY "Allow insert for anon" ON clients
    FOR INSERT TO anon WITH CHECK (true);

CREATE POLICY "Allow update for anon" ON clients
    FOR UPDATE TO anon USING (true);

-- ===================
-- APPOINTMENTS TABLE
-- ===================
CREATE TABLE IF NOT EXISTS appointments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_name VARCHAR(255) NOT NULL,
    client_phone VARCHAR(50) NOT NULL,
    client_email VARCHAR(255),
    service VARCHAR(255) NOT NULL,
    requested_date DATE NOT NULL,
    requested_time TIME NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    booked_via VARCHAR(50) DEFAULT 'ai_phone',
    call_id UUID REFERENCES calls(id),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_appointments_date ON appointments(requested_date);
CREATE INDEX IF NOT EXISTS idx_appointments_status ON appointments(status);
CREATE INDEX IF NOT EXISTS idx_appointments_phone ON appointments(client_phone);

ALTER TABLE appointments ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow read for anon" ON appointments
    FOR SELECT TO anon USING (true);

CREATE POLICY "Allow insert for anon" ON appointments
    FOR INSERT TO anon WITH CHECK (true);

CREATE POLICY "Allow update for anon" ON appointments
    FOR UPDATE TO anon USING (true);

-- ===================
-- ESCALATIONS TABLE
-- ===================
CREATE TABLE IF NOT EXISTS escalations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id UUID REFERENCES calls(id),
    client_name VARCHAR(255) NOT NULL,
    client_phone VARCHAR(50) NOT NULL,
    issue_summary TEXT NOT NULL,
    details_json JSONB DEFAULT '{}'::jsonb,
    priority VARCHAR(50) DEFAULT 'normal',
    status VARCHAR(50) DEFAULT 'pending',
    resolved_at TIMESTAMP WITH TIME ZONE,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_escalations_status ON escalations(status);
CREATE INDEX IF NOT EXISTS idx_escalations_priority ON escalations(priority);
CREATE INDEX IF NOT EXISTS idx_escalations_created ON escalations(created_at DESC);

ALTER TABLE escalations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow read for anon" ON escalations
    FOR SELECT TO anon USING (true);

CREATE POLICY "Allow insert for anon" ON escalations
    FOR INSERT TO anon WITH CHECK (true);

CREATE POLICY "Allow update for anon" ON escalations
    FOR UPDATE TO anon USING (true);

-- ===================
-- STUDIO CONFIG TABLE
-- ===================
CREATE TABLE IF NOT EXISTS studio_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    config_key VARCHAR(100) UNIQUE NOT NULL,
    config_value TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

ALTER TABLE studio_config ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow read for anon" ON studio_config
    FOR SELECT TO anon USING (true);

CREATE POLICY "Allow upsert for anon" ON studio_config
    FOR INSERT TO anon WITH CHECK (true);

CREATE POLICY "Allow update for anon" ON studio_config
    FOR UPDATE TO anon USING (true);

-- ===================
-- FAQ KNOWLEDGE BASE TABLE
-- ===================
CREATE TABLE IF NOT EXISTS faq_knowledge (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_pattern VARCHAR(500) NOT NULL,
    answer TEXT NOT NULL,
    category VARCHAR(100) DEFAULT 'general',
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_faq_category ON faq_knowledge(category);
CREATE INDEX IF NOT EXISTS idx_faq_active ON faq_knowledge(active);

ALTER TABLE faq_knowledge ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow read for anon" ON faq_knowledge
    FOR SELECT TO anon USING (true);

CREATE POLICY "Allow insert for anon" ON faq_knowledge
    FOR INSERT TO anon WITH CHECK (true);

CREATE POLICY "Allow update for anon" ON faq_knowledge
    FOR UPDATE TO anon USING (true);

CREATE POLICY "Allow delete for anon" ON faq_knowledge
    FOR DELETE TO anon USING (true);

-- ===================
-- INSERT DEFAULT CONFIG
-- ===================
INSERT INTO studio_config (config_key, config_value) VALUES
    ('studio_name', 'Lash Zone London'),
    ('studio_phone', '07748252038'),
    ('studio_address', 'London, UK'),
    ('opening_hours', '{"mon": "9:00-19:00", "tue": "9:00-19:00", "wed": "9:00-19:00", "thu": "9:00-19:00", "fri": "9:00-19:00", "sat": "9:00-19:00", "sun": "10:00-17:00"}'),
    ('ai_name', 'Luna'),
    ('ai_voice', 'alloy'),
    ('booking_url', ''),
    ('owner_phone', '07748252038'),
    ('sms_booking_message', 'Thanks for calling! Ready to book? Click here: {booking_url}'),
    ('sms_escalation_alert', 'ESCALATION: Client needs callback. Name: {name}, Phone: {phone}, Issue: {issue}')
ON CONFLICT (config_key) DO NOTHING;

-- ===================
-- INSERT SAMPLE FAQS
-- ===================
INSERT INTO faq_knowledge (question_pattern, answer, category) VALUES
    ('what services do you offer', 'We offer a range of lash and beauty services including Classic, Hybrid, Volume, and Mega Volume lash extensions, lash lifts, brow lamination, and facial treatments. Would you like more details on any specific service?', 'services'),
    ('how much are lash extensions', 'Our lash extensions start from £45 for classic lashes, going up to £110 for mega volume. The price depends on the style and lash type you choose. Would you like me to explain the differences?', 'pricing'),
    ('how long does it take', 'Classic lashes take about 90 minutes, while volume lashes can take up to 2 hours. Your first appointment may be slightly longer as we discuss your preferences.', 'services'),
    ('do you take walk ins', 'We primarily work by appointment to ensure you get our full attention. Please call or book online to schedule your visit. We do our best to accommodate urgent requests!', 'booking'),
    ('what is your cancellation policy', 'We require 24 hours notice for cancellations. This allows us to offer the time to other clients. Late cancellations or no-shows may incur a fee.', 'policies'),
    ('do you offer refills', 'Yes! We offer lash refill services. Most clients need fills every 2-3 weeks to maintain their lashes. Would you like to book a refill?', 'services'),
    ('are your lashes vegan', 'Yes! We use premium vegan and cruelty-free products for all our lash extensions and treatments.', 'products'),
    ('what aftercare should i follow', 'After your lash appointment, avoid getting them wet for 24 hours, dont use oil-based products near your eyes, and brush them gently daily. We provide full aftercare instructions at your appointment.', 'aftercare'),
    ('do you do lash lifts', 'Yes! Our lash lift service costs between £35-50 and takes about 45-60 minutes. It curls your natural lashes for a beautiful, mascara-like effect without extensions.', 'services'),
    ('can i wear makeup after', 'We recommend waiting 24-48 hours before applying eye makeup to allow the adhesive to fully set. After that, feel free to apply makeup as normal, just avoid waterproof products near the lashes.', 'aftercare')
ON CONFLICT DO NOTHING;
