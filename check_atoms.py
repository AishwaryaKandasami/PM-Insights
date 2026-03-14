from database.db import get_connection

conn = get_connection()

tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print("Tables:", [t["name"] for t in tables])

count = conn.execute("SELECT COUNT(*) as n FROM review_atoms").fetchone()
print("Atoms total:", count["n"])

breakdown = conn.execute(
    "SELECT routed_as, atom_type, COUNT(*) as n FROM review_atoms "
    "GROUP BY routed_as, atom_type ORDER BY routed_as"
).fetchall()
print("Breakdown by routed_as + atom_type:")
for r in breakdown:
    print(" ", dict(r))

# Note: noise reviews are SKIPPED by the agent — they never get atoms written.
# To inspect them we look at reviews_normalized that are NOT in review_atoms.
noise_approx = conn.execute("""
    SELECT rn.cleaned_text
    FROM reviews_normalized rn
    WHERE rn.is_supported = 1
      AND rn.is_low_quality = 0
      AND rn.is_duplicate = 0
      AND rn.review_id NOT IN (SELECT DISTINCT review_id FROM review_atoms)
    LIMIT 10
""").fetchall()
print(f"\nReviews processed but skipped (noise candidates) — "
      f"showing up to 10 from unmatched pool:")
for i, r in enumerate(noise_approx, 1):
    print(f"  [{i}] {r['cleaned_text'][:120]}")

conn.close()
