import sqlite3

def run_migration():
    conn = sqlite3.connect("human_cache.db")
    c = conn.cursor()
    cols = [col[1] for col in c.execute("PRAGMA table_info(notifications)").fetchall()]
    new_cols = [
        ("entity_type", "TEXT"),
        ("entity_id", "TEXT"),
        ("priority", "TEXT DEFAULT 'normal'"),
        ("scheduled_for", "TIMESTAMP"),
        ("delivered_at", "TIMESTAMP"),
        ("expires_at", "TIMESTAMP"),
        ("meta", "JSON")
    ]
    for col_name, col_type in new_cols:
        if col_name not in cols:
            c.execute(f"ALTER TABLE notifications ADD COLUMN {col_name} {col_type}")
            print(f"Added column {col_name}")
    conn.commit()
    final_cols = [col[1] for col in c.execute("PRAGMA table_info(notifications)").fetchall()]
    conn.close()
    print("Migration complete. Columns:", final_cols)

if __name__ == "__main__":
    run_migration()
