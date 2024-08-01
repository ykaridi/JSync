CREATE_SYMBOLS_TABLE_QUERY = """
CREATE TABLE IF NOT EXISTS symbols (
    author TEXT,
    symbol_type INTEGER,
    canonical_signature TEXT,
    name TEXT,
    timestamp INTEGER,
    PRIMARY KEY (author, canonical_signature, timestamp)
);
"""
PUSH_SYMBOLS_QUERY = """
WITH input(author, symbol_type, canonical_signature, name, timestamp) AS (
    VALUES (?, ?, ?, ?, ?)
),
latest_symbols(author, symbol_type, canonical_signature, name, timestamp) AS (
    SELECT author, symbol_type, canonical_signature, name, MAX(timestamp)
    FROM symbols
    GROUP BY author, canonical_signature
)
REPLACE INTO symbols(author, symbol_type, canonical_signature, name, timestamp)
SELECT input.author, input.symbol_type, input.canonical_signature, input.name, input.timestamp
FROM input
LEFT JOIN latest_symbols ON
    input.author = latest_symbols.author
AND input.canonical_signature = latest_symbols.canonical_signature
WHERE input.name != latest_symbols.name
   OR latest_symbols.name IS NULL;
"""
DELETE_SYMBOLS_QUERY = """
DELETE FROM symbols WHERE author = ? AND canonical_signature = ? AND timestamp = ?;
"""
GET_SYMBOLS_QUERY = """
SELECT *, max(timestamp)
FROM symbols
WHERE timestamp > ?
GROUP BY canonical_signature, author;
"""
GET_SYMBOLS_CANONICAL_SIGNATURE_QUERY = """
SELECT *, max(timestamp)
FROM symbols
WHERE canonical_signature = ? AND timestamp > ? 
GROUP BY author;
"""
GET_SYMBOLS_AUTHOR_QUERY = """
SELECT *, max(timestamp)
FROM symbols
WHERE author = ? AND timestamp > ? 
GROUP BY canonical_signature;
"""
GET_SYMBOLS_CANONICAL_SIGNATURE_AUTHOR_QUERY = """
SELECT *, max(timestamp)
FROM symbols
WHERE canonical_signature = ? AND author = ? AND timestamp > ?;
"""
