import sqlite3

c = sqlite3.connect('trading_desk.db')

# چک قبل
print('=== BEFORE ===')
for r in c.execute('SELECT id, stage_type, status FROM prop_stages').fetchall():
    print(r)

# Update
c.execute("UPDATE prop_stages SET status = 'PASSED', end_date = datetime('now') WHERE id = 1")
c.commit()

print()
print('Rows affected:', c.total_changes)

# چک بعد
print()
print('=== AFTER ===')
for r in c.execute('SELECT id, stage_type, status FROM prop_stages').fetchall():
    print(r)