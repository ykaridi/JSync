CLIENT_CREATE_SYMBOLS_TABLE_QUERY = """
CREATE TABLE IF NOT EXISTS symbols (
    author TEXT,
    symbol_type INTEGER,
    canonical_signature TEXT,
    name TEXT,
    timestamp INTEGER,
    PRIMARY KEY (author, canonical_signature)
);"""
CLIENT_DELETE_SYMBOLS_QUERY = """
DELETE FROM symbols WHERE author = ? AND canonical_signature = ?;
"""
CREATE_RENAME_RECORDS_TABLE_QUERY = """
CREATE TABLE IF NOT EXISTS rename_records (
    canonical_signature TEXT,
    name TEXT,
    PRIMARY KEY (canonical_signature)
);
"""
PUSH_RENAME_QUERY = """
INSERT OR REPLACE INTO rename_records (canonical_signature, name) VALUES (?, ?);
"""
DELETE_RENAME_QUERY = """
DELETE FROM rename_records WHERE canonical_signature = ?;
"""
GET_RENAME_QUERY = """
SELECT name
FROM rename_records
WHERE canonical_signature = ?;
"""
