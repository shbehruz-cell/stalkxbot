import tempfile
import unittest
from pathlib import Path

from app.database import Database


class DatabaseTests(unittest.TestCase):
    def test_upsert_and_list_connection(self):
        with tempfile.TemporaryDirectory() as temp:
            db = Database(str(Path(temp) / "test.sqlite3"))
            db.upsert_connection("conn-1", 12345, True, True, True)
            row = db.get_connection("conn-1")
            self.assertIsNotNone(row)
            self.assertEqual(row["owner_user_id"], 12345)
            self.assertEqual(row["is_enabled"], 1)
            self.assertEqual(db.count_active_connections(12345), 1)
            self.assertEqual(len(db.list_connections(12345)), 1)

    def test_close_connection(self):
        with tempfile.TemporaryDirectory() as temp:
            db = Database(str(Path(temp) / "test.sqlite3"))
            db.upsert_connection("conn-1", 12345, True)
            db.close_connection("conn-1", 12345)
            self.assertEqual(db.count_active_connections(12345), 0)


if __name__ == "__main__":
    unittest.main()
