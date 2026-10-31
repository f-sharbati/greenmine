import sqlite3

def check():
    conn = sqlite3.connect('greenmine.db')
    cursor = conn.cursor()
    print("--- User List ---")
    cursor.execute("SELECT id, username, full_name FROM users")
    users = cursor.fetchall()
    for u in users:
        print(f"ID: {u[0]} | Username: {u[1]} | Name: {u[2]}")
    conn.close()

if __name__ == "__main__":
    check()
