import os
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.collection import Collection

load_dotenv()


COLLECTION_MAP = {
    "review_logs": os.environ.get("COLLECTION_REVIEW_LOGS", "sandmark-history"),
    "requirements": os.environ.get("COLLECTION_REQUIREMENTS", "requirements"),
    "risks": os.environ.get("COLLECTION_RISKS", "risks"),
    "soup_register": os.environ.get("COLLECTION_SOUP", "soup_register"),
}


class BaseAgent:
    """Base class for all QualityMetrics agents."""

    def __init__(self):
        uri = os.environ.get("MONGODB_URI")
        db_name = os.environ.get("MONGO_DB_NAME")

        if not uri:
            raise ValueError("MONGODB_URI is missing. Add it to .env or environment variables.")
        if not db_name:
            raise ValueError("MONGO_DB_NAME is missing. Add it to .env or environment variables.")

        self.client = MongoClient(uri)
        self.db = self.client[db_name]

    def collection(self, name: str) -> Collection:
        """Return a MongoDB collection by logical or real name."""
        real_name = COLLECTION_MAP.get(name, name)
        return self.db[real_name]

    def trend_label(self, current: float, previous: float) -> tuple[str, float]:
        delta = round(current - previous, 4)
        if previous == 0 and current == 0:
            return "stable", 0.0
        if delta > 0:
            return "up", delta
        if delta < 0:
            return "down", delta
        return "stable", 0.0

    def low_sample_warning(self, n: int, threshold: int = 30) -> Optional[str]:
        if n < threshold:
            return f"Sample size {n} is below {threshold}; result may be less reliable."
        return None

    def parse_datetime(self, value) -> Optional[datetime]:
        """Parse Mongo Date or ISO string into timezone-aware datetime."""
        if value is None:
            return None
        if isinstance(value, datetime):
            dt = value
        elif isinstance(value, str):
            try:
                dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return None
        else:
            return None

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt

    def run(self) -> dict:
        raise NotImplementedError
