from collections import defaultdict
from datetime import datetime, timedelta, timezone

from .base_agent import BaseAgent


class ReviewDensityAgent(BaseAgent):
    """Average number of Gemini comments per Merge Request."""

    def run(self) -> dict:
        col = self.collection("review_logs")
        all_docs = list(col.find({}))

        now = datetime.now(tz=timezone.utc)
        cutoff_30 = now - timedelta(days=30)
        cutoff_60 = now - timedelta(days=60)

        dated_docs = [(doc, self.parse_datetime(doc.get("timestamp"))) for doc in all_docs]
        recent = [doc for doc, ts in dated_docs if ts is not None and ts >= cutoff_30]
        previous = [doc for doc, ts in dated_docs if ts is not None and cutoff_60 <= ts < cutoff_30]

        period = "last_30_days"
        docs_for_value = recent
        previous_for_trend = previous
        if not docs_for_value and all_docs:
            docs_for_value = all_docs
            previous_for_trend = []
            period = "all_time"

        def avg_comments(docs):
            if not docs:
                return 0.0
            total = sum(len(d.get("review_json", {}).get("comments", [])) for d in docs)
            return round(total / len(docs), 4)

        current_value = avg_comments(docs_for_value)
        previous_value = avg_comments(previous_for_trend)
        trend, delta = self.trend_label(current_value, previous_value)

        by_type: dict[str, int] = defaultdict(int)
        file_counts: dict[str, int] = defaultdict(int)
        total_comments = 0

        for doc in docs_for_value:
            comments = doc.get("review_json", {}).get("comments", [])
            total_comments += len(comments)
            for comment in comments:
                by_type[comment.get("type", "unknown")] += 1
                file_name = comment.get("file")
                if file_name:
                    file_counts[file_name] += 1

        top_files = [file_name for file_name, _ in sorted(file_counts.items(), key=lambda x: -x[1])[:5]]

        weekly: dict[str, list[int]] = defaultdict(list)
        for doc in docs_for_value:
            ts = self.parse_datetime(doc.get("timestamp"))
            week = ts.strftime("%Y-W%W") if ts else "unknown"
            weekly[week].append(len(doc.get("review_json", {}).get("comments", [])))
        weekly_avg = {w: round(sum(v) / len(v), 2) for w, v in sorted(weekly.items())}

        sample_size = len(docs_for_value)
        return {
            "metric": "review_density",
            "value": round(current_value, 2),
            "unit": "avg comments per MR",
            "trend": trend,
            "trend_delta": delta,
            "period": period,
            "sample_size": sample_size,
            "warning": "No documents found in sandmark-history" if sample_size == 0 else self.low_sample_warning(sample_size),
            "details": {
                "total_mrs": sample_size,
                "total_comments": total_comments,
                "by_type": dict(by_type),
                "top_files": top_files,
                "weekly_avg": weekly_avg,
            },
        }
