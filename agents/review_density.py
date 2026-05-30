from collections import defaultdict
from datetime import datetime, timedelta, timezone
from .base_agent import BaseAgent


class ReviewDensityAgent(BaseAgent):
    """
    Counting findings per MR.
    """

    def run(self) -> dict:
        col = self.collection("review_logs")
        now = datetime.now(tz=timezone.utc)
        cutoff_30 = now - timedelta(days=30)
        cutoff_60 = now - timedelta(days=60)

        all_docs = list(col.find({}))
        recent   = [d for d in all_docs if self._ts(d) >= cutoff_30]
        previous = [d for d in all_docs if cutoff_60 <= self._ts(d) < cutoff_30]

        def avg_comments(docs):
            if not docs:
                return 0.0
            total = sum(len(d.get("review_json", {}).get("comments", [])) for d in docs)
            return round(total / len(docs), 4)

        current_value  = avg_comments(recent)
        previous_value = avg_comments(previous)
        trend, delta   = self.trend_label(current_value, previous_value)

        by_type: dict[str, int]  = defaultdict(int)
        file_counts: dict[str, int] = defaultdict(int)
        total_comments = 0

        for doc in recent:
            for c in doc.get("review_json", {}).get("comments", []):
                by_type[c.get("type", "unknown")] += 1
                total_comments += 1
                f = c.get("file")
                if f:
                    file_counts[f] += 1

        top_files = sorted(file_counts, key=file_counts.get, reverse=True)[:3]  # type: ignore

        weekly: dict[str, list] = defaultdict(list)
        for doc in recent:
            week = self._ts(doc).strftime("%Y-W%W")
            weekly[week].append(len(doc.get("review_json", {}).get("comments", [])))
        weekly_avg = {w: round(sum(v) / len(v), 2) for w, v in weekly.items()}

        n = len(recent)
        return {
            "metric": "review_density",
            "value": current_value,
            "unit": "avg comments per MR",
            "trend": trend,
            "trend_delta": delta,
            "period": "last_30_days",
            "sample_size": n,
            "warning": self.low_sample_warning(n),
            "details": {
                "total_comments": total_comments,
                "by_type": dict(by_type),
                "top_files": top_files,
                "weekly_avg": weekly_avg,
            },
        }

    def _ts(self, doc) -> datetime:
        ts = doc.get("timestamp", "")
        try:
            dt = datetime.fromisoformat(ts)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            return datetime.min.replace(tzinfo=timezone.utc)