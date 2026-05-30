from collections import defaultdict
from datetime import datetime, timedelta, timezone
from .base_agent import BaseAgent


class RiskClosureAgent(BaseAgent):
    """closure_rate = closed_risks / total_risks * 100"""

    def run(self) -> dict:
        col = self.collection("risks")
        all_risks = list(col.find({}))
        total = len(all_risks)
        now = datetime.now(tz=timezone.utc)
        overdue_threshold = now - timedelta(days=30)

        closed = [r for r in all_risks if r.get("closed_at") is not None]
        closure_rate = round(len(closed) / total * 100, 2) if total else 0.0

        # By severity
        by_severity: dict[str, dict] = defaultdict(lambda: {"total": 0, "closed": 0})
        overdue_risks = []

        for r in all_risks:
            sev = r.get("severity", "unknown")
            by_severity[sev]["total"] += 1
            if r.get("closed_at") is not None:
                by_severity[sev]["closed"] += 1
            else:
                created_at = r.get("created_at")
                if created_at:
                    try:
                        created_dt = datetime.fromisoformat(str(created_at))
                        if created_dt.tzinfo is None:
                            created_dt = created_dt.replace(tzinfo=timezone.utc)
                        if created_dt < overdue_threshold:
                            overdue_risks.append({
                                "risk_id": r.get("risk_id"),
                                "severity": sev,
                                "mitigation_status": r.get("mitigation_status"),
                                "days_open": (now - created_dt).days,
                            })
                    except Exception:
                        pass

        severity_rates = {
            sev: {
                "closure_rate": round(v["closed"] / v["total"] * 100, 2) if v["total"] else 0.0,
                "closed": v["closed"],
                "total": v["total"],
            }
            for sev, v in by_severity.items()
        }

        n = total
        return {
            "metric": "risk_closure_rate",
            "value": closure_rate,
            "unit": "percent closed",
            "trend": "n/a",
            "trend_delta": 0.0,
            "period": "current",
            "sample_size": n,
            "warning": self.low_sample_warning(n),
            "details": {
                "total_risks": total,
                "closed_risks": len(closed),
                "by_severity": severity_rates,
                "overdue_risks": overdue_risks,
            },
        }
