import os
from datetime import datetime, timezone
from pymongo import MongoClient
from pymongo.collection import Collection

# Маппинг логических имён коллекций → реальные имена в MongoDB
COLLECTION_MAP = {
    "review_logs":  os.environ.get("COLLECTION_REVIEW_LOGS",  "sandmark-history"),
    "requirements": os.environ.get("COLLECTION_REQUIREMENTS", "requirements"),
    "risks":        os.environ.get("COLLECTION_RISKS",        "risks"),
    "soup_register":os.environ.get("COLLECTION_SOUP",         "soup_register"),
}


class BaseAgent:
    """Base class providing MongoDB connection and shared utilities."""

    def __init__(self):
        uri     = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
        db_name = os.environ.get("MONGO_DB_NAME", "sandmark-db")
        self.client = MongoClient(uri)
        self.db     = self.client[db_name]

    def collection(self, name: str) -> Collection:
        real_name = COLLECTION_MAP.get(name, name)
        return self.db[real_name]

    def trend_label(self, current: float, previous: float) -> tuple[str, float]:
        if previous == 0:
            return "stable", 0.0
        delta = round(current - previous, 4)
        if delta > 0:
            return "up", delta
        elif delta < 0:
            return "down", delta
        return "stable", 0.0

    def low_sample_warning(self, n: int, threshold: int = 30) -> str | None:
        if n < threshold:
            return f"Sample size {n} is below {threshold}; trend may not be statistically significant."
        return None

    def run(self) -> dict:
        raise NotImplementedError