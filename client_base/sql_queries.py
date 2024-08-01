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
    symbol_type INTEGER,
    name TEXT,
    PRIMARY KEY (canonical_signature)
);
"""
PUSH_RENAME_QUERY = """
REPLACE INTO rename_records (canonical_signature, symbol_type, name) VALUES (?, ?, ?);
"""
DELETE_RENAME_QUERY = """
DELETE FROM rename_records WHERE canonical_signature = ?;
"""
GET_RENAME_BY_CANONICAL_SIGNATURE_QUERY = """
SELECT name, symbol_type
FROM rename_records
WHERE canonical_signature = ?;
"""
GET_RENAMES_QUERY = """
SELECT canonical_signature, symbol_type, name
FROM rename_records;
"""

CREATE_METADATA_TABLE_QUERY = """
CREATE TABLE IF NOT EXISTS metadata (
    property TEXT,
    value TEXT,
    PRIMARY KEY (property)
);"""
WRITE_METADATA_PROPERTY_QUERY = """
REPLACE INTO metadata(property, value) VALUES (?, ?);
"""
READ_METADATA_PROPERTY_QUERY = """
SELECT value FROM metadata WHERE property = ?;
"""
