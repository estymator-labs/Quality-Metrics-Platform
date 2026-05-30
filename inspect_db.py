"""
Запуск: python inspect_db.py
Показывает реальную структуру документов в sandmark-history.
"""
import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()
client = MongoClient(os.environ.get("MONGODB_URI"))
db = client[os.environ.get("MONGO_DB_NAME", "sandmark-db")]
col = db["sandmark-history"]

total = col.count_documents({})
print(f"Всего документов: {total}\n")

# Один документ целиком
print("=" * 60)
print("ПРИМЕР ДОКУМЕНТА (первый):")
print("=" * 60)
doc = col.find_one({})
if doc:
    for k, v in doc.items():
        if k == "_id":
            continue
        if k == "review_json":
            print(f"  review_json:")
            if isinstance(v, dict):
                for k2, v2 in v.items():
                    if k2 == "comments":
                        print(f"    comments: [{len(v2)} шт]")
                        if v2:
                            print(f"      пример: {v2[0]}")
                    else:
                        s = str(v2)
                        print(f"    {k2}: {s[:80]}")
        else:
            print(f"  {k}: {v}")

# Проверяем ключевые поля
print("\n" + "=" * 60)
print("СТАТИСТИКА ПОЛЕЙ:")
print("=" * 60)

checks = [
    ("lines_added",    {"lines_added": {"$exists": True}}),
    ("lines_added > 0",{"lines_added": {"$gt": 0}}),
    ("review_json",    {"review_json": {"$exists": True}}),
    ("comments > 0",   {"review_json.comments.0": {"$exists": True}}),
    ("escaped_to_prod существует", {"escaped_to_prod": {"$exists": True}}),
    ("escaped_to_prod = true",     {"escaped_to_prod": True}),
    ("timestamp существует",       {"timestamp": {"$exists": True}}),
]

for label, query in checks:
    n = col.count_documents(query)
    pct = f"{n/total*100:.0f}%" if total else "—"
    mark = "✓" if n > 0 else "✗"
    print(f"  {mark} {label}: {n} ({pct})")

# Показываем реальные имена всех полей
print("\n" + "=" * 60)
print("ВСЕ КЛЮЧИ В ДОКУМЕНТАХ (первые 5):")
print("=" * 60)
all_keys = set()
for d in col.find({}, limit=5):
    all_keys.update(d.keys())
print("  Верхний уровень:", sorted(k for k in all_keys if k != "_id"))

# Ключи внутри review_json
rj = col.find_one({"review_json": {"$exists": True}})
if rj and "review_json" in rj:
    print("  review_json:", sorted(rj["review_json"].keys()))
    comments = rj["review_json"].get("comments", [])
    if comments:
        print("  comments[0]:", sorted(comments[0].keys()))