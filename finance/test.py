from cs50 import SQL


db = SQL("sqlite:///finance.db")

check = db.execute(
    'SELECT username FROM users WHERE EXISTS (SELECT username FROM users WHERE username = "mrseri")')

# insert = db.execute(
# 'INSERT INTO users (username, hash) VALUES ("mrseri", "hello")')

print(len(check))
