from database.db import get_connection
conn = get_connection()

# Check pipeline_runs columns
cols = conn.execute('PRAGMA table_info(pipeline_runs)').fetchall()
print("pipeline_runs columns:", [c[1] for c in cols])

# Show recent runs
runs = conn.execute('SELECT * FROM pipeline_runs ORDER BY rowid DESC LIMIT 5').fetchall()
for r in runs:
    print(dict(r))

# Atom counts
total = conn.execute('SELECT COUNT(*) FROM review_atoms').fetchone()[0]
bugs = conn.execute("SELECT COUNT(*) FROM review_atoms WHERE atom_type = 'bug'").fetchone()[0]
features = conn.execute("SELECT COUNT(*) FROM review_atoms WHERE atom_type = 'feature'").fetchone()[0]
print(f'Atoms written: {total}')
print(f'Bugs: {bugs} | Features: {features}')

conn.close()