import sqlite3 as sq

conn = sq.connect('kb.sqlite')
cursor = conn.cursor()

cursor.execute('select text from chunks where doc like "vaswani%";')
records = cursor.fetchall()

with open('test_chunks.md', 'w') as file:
    for record in records:
        file.write(record[0])

conn.close()