from database import get_connection, update_user_age
conn = get_connection()
cursor = conn.cursor()
cursor.execute("SELECT id, username, age FROM users")
print("Before:", cursor.fetchall())
