import sqlite3
c = sqlite3.connect('trading_desk.db')
c.execute("UPDATE prop_stages SET current_profit = 0 WHERE id = 2")
c.commit()
print('Rows affected:', c.total_changes)
print()
print('=== After fix ===')
for r in c.execute('SELECT id, stage_type, status, current_profit FROM prop_stages').fetchall():
    print(r)