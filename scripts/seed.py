"""初始化校区数据与示例数据（可重复执行）。"""
from datetime import datetime, timedelta

from app.models.db import get_conn, init_db


def seed() -> None:
    init_db()
    conn = get_conn()
    try:
        conn.execute("DELETE FROM trips")
        conn.execute("DELETE FROM posts")
        conn.execute("DELETE FROM sessions")

        now = datetime.now()
        depart_at = (now + timedelta(hours=3)).isoformat()

        conn.execute(
            "INSERT INTO trips "
            "(trip_id, origin, destination, origin_lat, origin_lng, destination_lat, "
            " destination_lng, depart_at, max_seats, current_seats, fee, leader, status, created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                "t_demo001",
                "福州外语外贸学院滨海校区",
                "福州外语外贸学院长乐校区",
                25.44, 119.62, 25.86, 119.51,
                depart_at, 3, 1, 5.0, "演示队长", "待出发", now.isoformat(),
            ),
        )

        conn.execute(
            "INSERT INTO posts (post_id, title, content, author, campus_name, created_at) "
            "VALUES (?,?,?,?,?,?)",
            (
                "p_demo001",
                "周三滨海到长乐求拼车",
                "有顺路的朋友吗？加我一个~",
                "演示用户",
                "福州外语外贸学院滨海校区",
                now.isoformat(),
            ),
        )
        conn.commit()
        print("示例数据初始化完成：1 条拼车队伍 + 1 条帖子")
    finally:
        conn.close()


if __name__ == "__main__":
    seed()