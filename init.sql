CREATE TABLE IF NOT EXISTS url_mappings (
    slug TEXT PRIMARY KEY,
    original_url TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE IF NOT EXISTS rate_limits (
    ip_address TEXT PRIMARY KEY,
    request_count INTEGER,
    last_request TIMESTAMP WITH TIME ZONE
);
