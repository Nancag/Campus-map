"""拼车队伍仓储：插入、检索、详情、席位原子增减、状态更新。"""
from datetime import datetime
from typing import List, Optional, Tuple

from app.models import db


def _row_to_trip(row) -> dict:
    keys = row.keys()
    return {
        "tripId": row["trip_id"],
        "teamName": row["team_name"] if "team_name" in keys else "",
        "origin": row["origin"],
        "destination": row["destination"],
        "originLat": row["origin_lat"],
        "originLng": row["origin_lng"],
        "destinationLat": row["destination_lat"],
        "destinationLng": row["destination_lng"],
        "departAt": row["depart_at"],
        "maxSeats": row["max_seats"],
        "currentSeats": row["current_seats"],
        "fee": row["fee"],
        "leaderName": row["leader"],
        "status": row["status"],
        "gender": row["gender"],
        "remark": row["remark"],
        "createdAt": row["created_at"],
    }


def create(trip: dict) -> None:
    conn = db.get_conn()
    try:
        conn.execute(
            "INSERT INTO trips "
            "(trip_id, team_name, origin, destination, origin_lat, origin_lng, "
            " destination_lat, destination_lng, depart_at, max_seats, "
            " current_seats, fee, leader, status, gender, remark, created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                trip["tripId"],
                trip.get("teamName", ""),
                trip["origin"],
                trip["destination"],
                trip.get("originLat"),
                trip.get("originLng"),
                trip.get("destinationLat"),
                trip.get("destinationLng"),
                trip["departAt"],
                trip["maxSeats"],
                trip["currentSeats"],
                trip.get("fee"),
                trip["leaderName"],
                trip["status"],
                trip.get("gender", "不限"),
                trip.get("remark"),
                trip["createdAt"],
            ),
        )
        conn.commit()
    finally:
        conn.close()


def find_by_id(trip_id: str) -> Optional[dict]:
    conn = db.get_conn()
    try:
        row = conn.execute("SELECT * FROM trips WHERE trip_id = ?", (trip_id,)).fetchone()
        return _row_to_trip(row) if row else None
    finally:
        conn.close()


def search(
    origin: Optional[str],
    destination: Optional[str],
    depart_from: Optional[str],
    depart_to: Optional[str],
    page: int,
    size: int,
) -> Tuple[List[dict], int]:
    """按关键词模糊检索 + 可选出发时间区间，按创建时间倒序分页。"""
    sql = "SELECT * FROM trips WHERE 1=1"
    params: list = []

    if origin:
        sql += " AND origin LIKE ?"
        params.append(f"%{origin}%")
    if destination:
        sql += " AND destination LIKE ?"
        params.append(f"%{destination}%")
    if depart_from:
        sql += " AND depart_at >= ?"
        params.append(depart_from)
    if depart_to:
        sql += " AND depart_at <= ?"
        params.append(depart_to)

    conn = db.get_conn()
    try:
        total = conn.execute(
            f"SELECT COUNT(*) AS c FROM trips WHERE 1=1" + _where_suffix(origin, destination, depart_from, depart_to),
            params,
        ).fetchone()["c"]

        rows = conn.execute(
            sql + " ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [size, (page - 1) * size],
        ).fetchall()
        return [_row_to_trip(r) for r in rows], total
    finally:
        conn.close()


def _where_suffix(origin, destination, depart_from, depart_to) -> str:
    parts = []
    if origin:
        parts.append(" AND origin LIKE ?")
    if destination:
        parts.append(" AND destination LIKE ?")
    if depart_from:
        parts.append(" AND depart_at >= ?")
    if depart_to:
        parts.append(" AND depart_at <= ?")
    return "".join(parts)


def atomic_join(trip_id: str) -> bool:
    """席位 +1 的原子操作；名额已满或无此队伍时返回 False。"""
    conn = db.get_conn()
    try:
        cur = conn.execute(
            "UPDATE trips SET current_seats = current_seats + 1, "
            " status = CASE WHEN current_seats + 1 >= max_seats THEN ? ELSE status END "
            "WHERE trip_id = ? AND current_seats < max_seats",
            ("已满员", trip_id),
        )
        conn.commit()
        return cur.rowcount == 1
    finally:
        conn.close()


def atomic_leave(trip_id: str) -> bool:
    """席位 -1 的原子操作；无此队伍或席位已为 0 时返回 False。"""
    conn = db.get_conn()
    try:
        cur = conn.execute(
            "UPDATE trips SET current_seats = current_seats - 1, "
            " status = CASE WHEN status = ? THEN ? ELSE status END "
            "WHERE trip_id = ? AND current_seats > 0",
            ("已满员", "待出发", trip_id),
        )
        conn.commit()
        return cur.rowcount == 1
    finally:
        conn.close()


def update_status(trip_id: str, status: str) -> bool:
    conn = db.get_conn()
    try:
        cur = conn.execute("UPDATE trips SET status = ? WHERE trip_id = ?", (status, trip_id))
        conn.commit()
        return cur.rowcount == 1
    finally:
        conn.close()

def update_trip(trip_id: str, fields: dict) -> bool:
    cols = []
    params = []
    mapping = {
        "teamName": "team_name",
        "origin": "origin",
        "destination": "destination",
        "departAt": "depart_at",
        "maxSeats": "max_seats",
        "gender": "gender",
        "remark": "remark",
        "originLat": "origin_lat",
        "originLng": "origin_lng",
        "destinationLat": "destination_lat",
        "destinationLng": "destination_lng",
    }
    for k, v in fields.items():
        col = mapping.get(k)
        if col:
            cols.append(f"{col} = ?")
            params.append(v)
    if not cols:
        return False
    params.append(trip_id)
    conn = db.get_conn()
    try:
        cur = conn.execute(f"UPDATE trips SET {', '.join(cols)} WHERE trip_id = ?", params)
        conn.commit()
        return cur.rowcount == 1
    finally:
        conn.close()


def add_member(trip_id: str, username: str, gender: str) -> bool:
    conn = db.get_conn()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO trip_members (trip_id, username, gender, joined_at) VALUES (?,?,?,?)",
            (trip_id, username, gender, datetime.now().isoformat()),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def remove_member(trip_id: str, username: str) -> bool:
    conn = db.get_conn()
    try:
        cur = conn.execute(
            "DELETE FROM trip_members WHERE trip_id = ? AND username = ?",
            (trip_id, username),
        )
        conn.commit()
        return cur.rowcount == 1
    finally:
        conn.close()


def list_members(trip_id: str) -> list:
    conn = db.get_conn()
    try:
        rows = conn.execute(
            "SELECT username, gender, joined_at FROM trip_members WHERE trip_id = ? ORDER BY joined_at",
            (trip_id,),
        ).fetchall()
        return [{"username": r["username"], "gender": r["gender"], "joinedAt": r["joined_at"]} for r in rows]
    finally:
        conn.close()


def is_member(trip_id: str, username: str) -> bool:
    conn = db.get_conn()
    try:
        row = conn.execute(
            "SELECT 1 FROM trip_members WHERE trip_id = ? AND username = ?",
            (trip_id, username),
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def clear_members(trip_id: str) -> None:
    conn = db.get_conn()
    try:
        conn.execute("DELETE FROM trip_members WHERE trip_id = ?", (trip_id,))
        conn.commit()
    finally:
        conn.close()


def get_trips_by_leader(username: str) -> list:
    conn = db.get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM trips WHERE leader = ? AND status NOT IN ('已取消','已完成') ORDER BY created_at DESC",
            (username,),
        ).fetchall()
        return [_row_to_trip(r) for r in rows]
    finally:
        conn.close()