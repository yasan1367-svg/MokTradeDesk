import sqlite3

c = sqlite3.connect('trading_desk.db')
c.execute("UPDATE prop_stages SET status = 'ACTIVE', end_date = NULL WHERE id = 1")
c.commit()
print('Rows affected:', c.total_changes)
print()
print('=== After revert ===')
for r in c.execute('SELECT id, stage_type, status FROM prop_stages').fetchall():
    print(r)