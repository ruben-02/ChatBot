import sqlite3

# Path to your SQLite DB file
DB_FILE = "chatbots.db"  # <-- change this if your DB is in another folder

def fix_gemini_models():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # Update all records to the correct model
    cur.execute("UPDATE chatbots SET gemini_model = 'gemini-2.0-flash';")

    conn.commit()
    conn.close()
    print("✅ All gemini_model values have been set to gemini-2.0-flash")

if __name__ == "__main__":
    fix_gemini_models()