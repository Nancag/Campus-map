import sqlite3, os

db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "campus_carpool.db")
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

test_leaders = ("userA", "userB", "userC", "dbg")
test_trip_ids = []

rows = conn.execute("SELECT trip_id, team_name, leader, depart_at FROM trips").fetchall()
for r in rows:
    is_test = r["leader"] in test_leaders or r["depart_at"].startswith("2099")
    if is_test:
        test_trip_ids.append(r["trip_id"])
        print(f"  TEST: {r['trip_id']} | {r['team_name']:<20} | {r['leader']:<10} | {r['depart_at']}")

print(f"\nTest trips to delete: {len(test_trip_ids)}")

test_post_ids = []
for tid in test_trip_ids:
    rows = conn.execute("SELECT post_id FROM team_forum_posts WHERE trip_id = ?", (tid,)).fetchall()
    for r in rows:
        test_post_ids.append(r["post_id"])

print(f"Test posts to delete: {len(test_post_ids)}")

for tid in test_trip_ids:
    conn.execute("DELETE FROM trip_members WHERE trip_id = ?", (tid,))
    conn.execute("DELETE FROM team_forum_posts WHERE trip_id = ?", (tid,))
    conn.execute("DELETE FROM trips WHERE trip_id = ?", (tid,))

for pid in test_post_ids:
    conn.execute("DELETE FROM post_likes WHERE post_id = ?", (pid,))
    conn.execute("DELETE FROM comments WHERE post_id = ?", (pid,))
    conn.execute("DELETE FROM posts WHERE post_id = ?", (pid,))

conn.commit()

remaining = conn.execute("SELECT COUNT(*) AS c FROM trips").fetchone()["c"]
remaining_members = conn.execute("SELECT COUNT(*) AS c FROM trip_members").fetchone()["c"]
remaining_tfp = conn.execute("SELECT COUNT(*) AS c FROM team_forum_posts").fetchone()["c"]
print(f"\nAfter cleanup:")
print(f"  trips: {remaining}")
print(f"  trip_members: {remaining_members}")
print(f"  team_forum_posts: {remaining_tfp}")

print("\nRemaining trips:")
rows = conn.execute("SELECT trip_id, team_name, origin, destination, depart_at, status, leader FROM trips").fetchall()
for r in rows:
    print(f"  {r['trip_id']} | {r['team_name']:<20} | {r['leader']:<10} | {r['depart_at']} | {r['status']}")

conn.close()