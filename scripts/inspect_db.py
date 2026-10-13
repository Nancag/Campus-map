import sqlite3, os

db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "campus_carpool.db")
print(f"DB: {db_path}")
print(f"Exists: {os.path.exists(db_path)}")

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

rows = conn.execute("SELECT trip_id, team_name, origin, destination, depart_at, status, leader FROM trips ORDER BY created_at").fetchall()
print(f"\nTotal trips: {len(rows)}")
print(f"{'trip_id':<20} {'team_name':<20} {'origin':<30} {'destination':<20} {'depart_at':<20} {'status':<10} {'leader':<10}")
print("-" * 130)
for r in rows:
    print(f"{r['trip_id']:<20} {r['team_name']:<20} {r['origin']:<30} {r['destination']:<20} {r['depart_at']:<20} {r['status']:<10} {r['leader']:<10}")

print("\n--- trip_members ---")
members = conn.execute("SELECT * FROM trip_members").fetchall()
print(f"Total members: {len(members)}")
for m in members:
    print(f"  {m['trip_id']} | {m['username']} | {m['gender']}")

print("\n--- team_forum_posts ---")
tfp = conn.execute("SELECT * FROM team_forum_posts").fetchall()
print(f"Total team_forum_posts: {len(tfp)}")
for t in tfp:
    print(f"  {t['post_id']} | {t['trip_id']}")

conn.close()