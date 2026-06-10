import os
from pprint import pprint

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

uri = os.getenv("MONGODB_URI")
db_name = os.getenv("MONGO_DB_NAME")

if not uri or not db_name:
    raise ValueError("Set MONGODB_URI and MONGO_DB_NAME in .env first.")

client = MongoClient(uri)
db = client[db_name]

collections = {
    "review logs": os.getenv("COLLECTION_REVIEW_LOGS", "sandmark-history"),
    "requirements": os.getenv("COLLECTION_REQUIREMENTS", "requirements"),
    "risks": os.getenv("COLLECTION_RISKS", "risks"),
    "soup": os.getenv("COLLECTION_SOUP", "soup_register"),
}

print("Database:", db_name)
print("Available collections:", db.list_collection_names())
print()

for label, collection_name in collections.items():
    col = db[collection_name]
    count = col.count_documents({})
    print(f"{label}: {collection_name} -> {count} documents")
    example = col.find_one({})
    if example:
        print("Example fields:", list(example.keys()))
    print()
