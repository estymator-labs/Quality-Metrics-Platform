from collections import defaultdict
from datetime import datetime, timezone
from .base_agent import BaseAgent


class DefectEscapeAgent(BaseAgent):

    def run(self) -> dict:
        col = self.collection("review_logs")
        all_docs = list(col.find({}))
        total = len(all_docs)

        by_type: dict[str, int]     = defaultdict(int)
        monthly_mrs: dict[str, int] = defaultdict(int)   # всего MR в месяце
        monthly_bug_mrs: dict[str, int] = defaultdict(int)  # MR с багом в месяце
        top_bug_files: dict[str, int] = defaultdict(int)
        mrs_with_bugs = []

        for doc in all_docs:
            comments  = doc.get("review_json", {}).get("comments", [])
            month     = self._month(doc)
            monthly_mrs[month] += 1
            doc_bugs  = [c for c in comments if c.get("type") == "bug"]

            for c in comments:
                by_type[c.get("type", "unknown")] += 1

            if doc_bugs:
                monthly_bug_mrs[month] += 1
                for c in doc_bugs:
                    f = c.get("file")
                    if f:
                        top_bug_files[f] += 1
                mrs_with_bugs.append({
                    "mr_url":    doc.get("mr_url"),
                    "bug_count": len(doc_bugs),
                })

        # % MR с хотя бы одним багом — по месяцам
        bug_mr_rate_by_month = {
            m: round(monthly_bug_mrs.get(m, 0) / monthly_mrs[m] * 100, 1)
            for m in sorted(monthly_mrs)
        }

        top_files = sorted(top_bug_files, key=top_bug_files.get, reverse=True)[:5]  # type: ignore

        # Главная цифра: % MR с багом из всех MR
        value = round(len(mrs_with_bugs) / total * 100, 1) if total else 0.0

        total_comments = sum(by_type.values())
        by_type_pct = {
            t: {"count": c, "pct": round(c / total_comments * 100, 1)}
            for t, c in sorted(by_type.items(), key=lambda x: -x[1])
        }

        return {
            "metric": "defect_escape_rate",
            "value": value,
            "unit": "% MR с хотя бы одним bug-комментарием",
            "trend": "n/a",
            "trend_delta": 0.0,
            "period": "all_time",
            "sample_size": total,
            "warning": (
                "escaped_to_prod не заполнен — показываем % MR где Gemini нашёл баги."
            ),
            "details": {
                "total_comments": total_comments,
                "mrs_with_bugs": len(mrs_with_bugs),
                "mrs_clean": total - len(mrs_with_bugs),
                "by_type": by_type_pct,
                "bug_mr_rate_by_month": bug_mr_rate_by_month,
                "top_bug_files": top_files,
            },
        }

    def _month(self, doc) -> str:
        try:
            return datetime.fromisoformat(doc.get("timestamp", "")).strftime("%Y-%m")
        except Exception:
            return "unknown"