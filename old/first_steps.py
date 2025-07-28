import sqlite3

# Connect to (or create) a file-based database:
conn = sqlite3.connect('my_database.db')
# Create a cursor to run SQL commands:
cur = conn.cursor()


# Create a table if it doesn't exist:
cur.execute(
    '''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        age INTEGER
    )
    '''
)
conn.commit()

cur.execute("INSERT INTO users (name, age) VALUES (?, ?)",
            ("Alice", 30))
cur.execute("INSERT INTO users (name, age) VALUES (?, ?)",
            ("Bob", 25))
conn.commit()

cur.execute("SELECT * FROM users")
rows = cur.fetchall()
for row in rows:
print(row)  # Each row is a tuple: (id, name, age)

# Update Alice’s age:
cur.execute("UPDATE users SET age = ? WHERE name = ?", (31, "Alice"))
# Delete Bob:
cur.execute("DELETE FROM users WHERE name = ?", ("Bob",))
conn.commit()

conn.close()