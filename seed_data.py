"""Seed support collections for local demo.

This script does NOT modify sandmark-history. Real code review data must come from Sandmark.
It only inserts example requirements, risks and SOUP records if those collections are empty.
"""

import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()


def seed():
    uri = os.getenv("MONGODB_URI")
    db_name = os.getenv("MONGO_DB_NAME")

    if not uri or not db_name:
        raise ValueError("Set MONGODB_URI and MONGO_DB_NAME in .env before running seed_data.py")

    client = MongoClient(uri)
    db = client[db_name]
    now = datetime.now(timezone.utc)

    risks_col = db[os.getenv("COLLECTION_RISKS", "risks")]
    if risks_col.count_documents({}) == 0:
        risks_data = []
        for i in range(1, 16):
            closed = i % 2 == 0
            severity = "high" if i <= 3 else "medium" if i <= 10 else "low"
            risks_data.append({
                "risk_id": f"RSK-{i:03d}",
                "severity": severity,
                "created_at": (now - timedelta(days=40)).isoformat(),
                "closed_at": now.isoformat() if closed else None,
                "mitigation_status": "done" if closed else "in_progress",
            })
        risks_col.insert_many(risks_data)
        print("Inserted 15 risk records.")
    else:
        print("risks collection is not empty; skipped.")

    req_col = db[os.getenv("COLLECTION_REQUIREMENTS", "requirements")]
    if req_col.count_documents({}) == 0:
        req_data = []
        for i in range(1, 21):
            req_data.append({
                "req_id": f"REQ-{i:03d}",
                "title": f"Requirement {i}",
                "linked_test_ids": [f"TEST-{i:03d}"] if i % 5 != 0 else [],
            })
        req_col.insert_many(req_data)
        print("Inserted 20 requirement records.")
    else:
        print("requirements collection is not empty; skipped.")

    soup_col = db[os.getenv("COLLECTION_SOUP", "soup_register")]
    if soup_col.count_documents({}) == 0:
        soup_data = []
        for i in range(1, 13):
            soup_data.append({
                "library_name": f"lib-package-{i}",
                "version": f"1.{i}.0",
                "license": "MIT",
                "has_risk_assessment": True,
                "has_validation_record": False if i == 4 else True,
                "last_reviewed_at": now.isoformat(),
            })
        soup_col.insert_many(soup_data)
        print("Inserted 12 SOUP records.")
    else:
        print("soup_register collection is not empty; skipped.")

    print("Done.")


if __name__ == "__main__":
    seed()
