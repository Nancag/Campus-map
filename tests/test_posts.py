import os
import sys
import unittest
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.schemas import ErrorCode
from app.services import post_service


def _req(title="标题", content="内容", campusName=None, topic="校园生活"):
    return SimpleNamespace(title=title, content=content, campusName=campusName, topic=topic)


class TestPosts(unittest.TestCase):
    def test_empty_title_rejected(self):
        self.assertEqual(post_service.create_post("张三", _req(title=""))[0], ErrorCode.POST_TITLE_INVALID)

    def test_overlong_title_rejected(self):
        self.assertEqual(post_service.create_post("张三", _req(title="a" * 51))[0], ErrorCode.POST_TITLE_INVALID)

    def test_empty_content_rejected(self):
        self.assertEqual(post_service.create_post("张三", _req(content=""))[0], ErrorCode.POST_CONTENT_INVALID)

    def test_overlong_content_rejected(self):
        self.assertEqual(post_service.create_post("张三", _req(content="a" * 2001))[0], ErrorCode.POST_CONTENT_INVALID)


if __name__ == "__main__":
    unittest.main()