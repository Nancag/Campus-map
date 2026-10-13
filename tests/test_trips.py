import os
import sys
import tempfile
import unittest
from types import SimpleNamespace

os.environ["CAMPUS_CARPOOL_DB"] = os.path.join(tempfile.mkdtemp(), "test.db")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.db import init_db
from app.models.schemas import ErrorCode
from app.services import trip_service

init_db()


def _req(**kw):
    defaults = dict(
        origin="滨海校区东门",
        destination="长乐校区南门",
        departAt="2099-01-01T08:00:00",
        seats=2,
        fee=None,
        originLat=25.8805227,
        originLng=119.5566502,
        destinationLat=25.9259051,
        destinationLng=119.4953332,
        gender="不限",
        remark=None,
    )
    defaults.update(kw)
    return SimpleNamespace(**defaults)


class TestTrips(unittest.TestCase):
    def test_missing_field_rejected(self):
        self.assertEqual(trip_service.create_trip("张三", _req(destination=""))[0], ErrorCode.TRIP_FIELD_MISSING)

    def test_seats_less_than_one_rejected(self):
        self.assertEqual(trip_service.create_trip("张三", _req(seats=0))[0], ErrorCode.SEATS_INVALID)

    def test_origin_out_of_range_rejected(self):
        self.assertEqual(trip_service.create_trip("张三", _req(originLat=30.0, originLng=120.0))[0], ErrorCode.OUT_OF_RANGE)

    def test_destination_out_of_range_rejected(self):
        self.assertEqual(trip_service.create_trip("张三", _req(destinationLat=30.0, destinationLng=120.0))[0], ErrorCode.OUT_OF_RANGE)

    def test_past_depart_time_rejected(self):
        self.assertEqual(trip_service.create_trip("张三", _req(departAt="2020-01-01T08:00:00"))[0], ErrorCode.TRIP_FIELD_MISSING)

    def test_negative_fee_rejected(self):
        self.assertEqual(trip_service.create_trip("张三", _req(fee=-1))[0], ErrorCode.TRIP_FIELD_MISSING)

    def test_invalid_gender_rejected(self):
        self.assertEqual(trip_service.create_trip("张三", _req(gender="随便"))[0], ErrorCode.TRIP_FIELD_MISSING)

    def test_remark_too_long_rejected(self):
        self.assertEqual(trip_service.create_trip("张三", _req(remark="x" * 201))[0], ErrorCode.TRIP_FIELD_MISSING)

    def test_valid_gender_accepted(self):
        code, _m, _d = trip_service.create_trip("张三", _req(gender="仅女生"))
        self.assertEqual(code, ErrorCode.OK)


if __name__ == "__main__":
    unittest.main()