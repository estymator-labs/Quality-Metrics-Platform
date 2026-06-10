from collections import defaultdict
from datetime import datetime

from .base_agent import BaseAgent


class DefectEscapeAgent(BaseAgent):
    """Percentage of Merge Requests with at least one bug-type Gemini comment."""

    def run(self) -> dict:
        col = self.collection("review_logs")
        all_docs = list(col.find({}))
        total = len(all_docs)

        by_type: dict[str, int] = defaultdict(int)
        monthly_mrs: dict[str, int] = defaultdict(int)
        monthly_bug_mrs: dict[str, int] = defaultdict(int)
        top_bug_files: dict[str, int] = defaultdict(int)
        mrs_with_bugs = []

        for doc in all_docs:
            comments = doc.get("review_json", {}).get("comments", [])
            month = self._month(doc)
            monthly_mrs[month] += 1

            doc_bugs = [c for c in comments if c.get("type") == "bug"]

            for comment in comments:
                by_type[comment.get("type", "unknown")] += 1

            if doc_bugs:
                monthly_bug_mrs[month] += 1
                for comment in doc_bugs:
                    file_name = comment.get("file")
                    if file_name:
                        top_bug_files[file_name] += 1
                mrs_with_bugs.append({
                    "mr_url": doc.get("mr_url"),
                    "bug_count": len(doc_bugs),
                })

        bug_mr_rate_by_month = {
            month: round(monthly_bug_mrs.get(month, 0) / monthly_mrs[month] * 100, 1)
            for month in sorted(monthly_mrs)
        }

        top_files = [file_name for file_name, _ in sorted(top_bug_files.items(), key=lambda x: -x[1])[:5]]
        value = round(len(mrs_with_bugs) / total * 100, 1) if total else 0.0

        total_comments = sum(by_type.values())
        by_type_pct = {
            comment_type: {
                "count": count,
                "pct": round(count / total_comments * 100, 1) if total_comments else 0.0,
            }
            for comment_type, count in sorted(by_type.items(), key=lambda x: -x[1])
        }

        warning = None
        if total == 0:
            warning = "No documents found in sandmark-history"
        else:
            warning = self.low_sample_warning(total)

        return {
            "metric": "defect_escape",
            "value": value,
            "unit": "% MR with at least one bug comment",
            "trend": "not_calculated",
            "trend_delta": None,
            "period": "all_time",
            "sample_size": total,
            "warning": warning,
            "details": {
                "total_mrs": total,
                "total_comments": total_comments,
                "mrs_with_bugs": len(mrs_with_bugs),
                "mrs_clean": total - len(mrs_with_bugs),
                "by_type": by_type_pct,
                "bug_mr_rate_by_month": bug_mr_rate_by_month,
                "top_bug_files": top_files,
            },
        }

    def _month(self, doc) -> str:
        ts = self.parse_datetime(doc.get("timestamp"))
        return ts.strftime("%Y-%m") if ts else "unknown"
