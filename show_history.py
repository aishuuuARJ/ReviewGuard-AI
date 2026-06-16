import sqlite3
import os

def show_database_logs():
    db_path = "reviewguard_db.db"
    
    if not os.path.exists(db_path):
        print(f"Error: Database file '{db_path}' not found in the current directory.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        
        if "analysis_history" not in tables:
            print("No analysis history records found yet (the table does not exist).")
            return
            
        # Join analysis_history with users if users table exists, otherwise just print history
        query = """
            SELECT 
                h.history_id, 
                COALESCE(u.username, 'Guest/Deleted User') as user_name, 
                h.product_name, 
                h.total_reviews, 
                h.fake_reviews, 
                h.genuine_reviews, 
                h.created_at 
            FROM analysis_history h
            LEFT JOIN users u ON h.user_id = u.user_id
            ORDER BY h.created_at DESC
        """
        cursor.execute(query)
        rows = cursor.fetchall()

        if not rows:
            print("\nDatabase found, but the 'analysis_history' table is empty.")
            return

        print("\n" + "="*90)
        print("                        REVIEWGUARD AI - DATABASE HISTORY LOGS")
        print("="*90)
        print(f"{'ID':<4} | {'User Name':<20} | {'Product Name':<20} | {'Total':<6} | {'Fake':<5} | {'Genuine':<7} | {'Date/Time'}")
        print("-"*90)
        
        for row in rows:
            history_id, user_name, product_name, total, fake, genuine, created_at = row
            # Trim long product names for clean table formatting
            prod_display = product_name[:18] + ".." if len(product_name) > 20 else product_name
            print(f"{history_id:<4} | {user_name:<20} | {prod_display:<20} | {total:<6} | {fake:<5} | {genuine:<7} | {created_at}")
            
        print("="*90 + "\n")

    except sqlite3.Error as e:
        print(f"SQLite error occurred: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    show_database_logs()
