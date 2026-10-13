"""领域实体与拼车队伍状态机。"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from app.utils.geo import within_radius


class TripStatus(str, Enum):
    OPEN = "待出发"
    FULL = "已满员"
    DEPARTED = "已出发"
    COMPLETED = "已完成"
    CANCELED = "已取消"


# 状态机合法流转表
VALID_TRANSITIONS = {
    TripStatus.OPEN: {TripStatus.FULL, TripStatus.DEPARTED, TripStatus.CANCELED},
    TripStatus.FULL: {TripStatus.DEPARTED, TripStatus.CANCELED},
    TripStatus.DEPARTED: {TripStatus.COMPLETED},
    TripStatus.COMPLETED: set(),
    TripStatus.CANCELED: set(),
}


def can_transition(current: TripStatus, target: TripStatus) -> bool:
    return target in VALID_TRANSITIONS.get(current, set())


@dataclass
class User:
    username: str


@dataclass
class Campus:
    name: str
    center_lat: float
    center_lng: float
    radius_km: float = 40

    def contains(self, lat, lng) -> bool:
        return within_radius(self.center_lat, self.center_lng, lat, lng, self.radius_km)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "centerLat": self.center_lat,
            "centerLng": self.center_lng,
            "radiusKm": self.radius_km,
        }


@dataclass
class Trip:
    trip_id: str
    origin: str
    destination: str
    origin_lat: Optional[float]
    origin_lng: Optional[float]
    destination_lat: Optional[float]
    destination_lng: Optional[float]
    depart_at: str
    max_seats: int
    current_seats: int
    fee: Optional[float]
    leader: str
    status: str
    gender: str = "不限"
    remark: Optional[str] = None
    team_name: str = ""
    created_at: str = ""


@dataclass
class Post:
    post_id: str
    title: str
    content: str
    author: str
    campus_name: Optional[str]
    created_at: str