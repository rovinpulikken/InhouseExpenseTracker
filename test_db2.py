from database import get_connection, update_user_age
print("Updating rovinp...")
result = update_user_age('rovinp', 40)
print("Update result:", result)
conn = get_connection()
cursor = conn.cursor()
cursor.execute("SELECT id, username, age FROM users WHERE username = 'rovinp'")
print("After update:", cursor.fetchone())
