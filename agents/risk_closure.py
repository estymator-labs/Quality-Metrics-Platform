from collections import defaultdict
from datetime import datetime, timedelta, timezone

from .base_agent import BaseAgent


class RiskClosureAgent(BaseAgent):
    """Percentage of closed or mitigated risks."""

    CLOSED_STATUSES = {"closed", "mitigated", "accepted", "resolved", "done"}

    def _is_closed(self, risk) -> bool:
        status = str(risk.get("status") or risk.get("mitigation_status") or "").lower()
        return risk.get("closed_at") is not None or status in self.CLOSED_STATUSES

    def run(self) -> dict:
        col = self.collection("risks")
        all_risks = list(col.find({}))
        total = len(all_risks)

        now = datetime.now(tz=timezone.utc)
        overdue_threshold = now - timedelta(days=30)

        closed = [risk for risk in all_risks if self._is_closed(risk)]
        closure_rate = round(len(closed) / total * 100, 2) if total else 0.0

        by_severity: dict[str, dict] = defaultdict(lambda: {"total": 0, "closed": 0})
        overdue_risks = []

        for risk in all_risks:
            severity = risk.get("severity") or risk.get("risk_class") or "unknown"
            by_severity[severity]["total"] += 1

            if self._is_closed(risk):
                by_severity[severity]["closed"] += 1
                continue

            due_date = risk.get("due_date") or risk.get("deadline") or risk.get("target_date")
            created_at = risk.get("created_at")
            compare_date = self.parse_datetime(due_date) or self.parse_datetime(created_at)

            if compare_date and compare_date < overdue_threshold:
                overdue_risks.append({
                    "risk_id": risk.get("risk_id") or str(risk.get("_id")),
                    "severity": severity,
                    "mitigation_status": risk.get("mitigation_status") or risk.get("status") or "open",
                    "days_open": (now - compare_date).days,
                })

        severity_rates = {
            severity: {
                "closure_rate": round(values["closed"] / values["total"] * 100, 2) if values["total"] else 0.0,
                "closed": values["closed"],
                "total": values["total"],
            }
            for severity, values in by_severity.items()
        }

        return {
            "metric": "risk_closure",
            "value": closure_rate,
            "unit": "% closed risks",
            "trend": "not_calculated",
            "trend_delta": None,
            "period": "current",
            "sample_size": total,
            "warning": "No documents found in risks collection" if total == 0 else self.low_sample_warning(total),
            "details": {
                "total_risks": total,
                "closed_risks": len(closed),
                "open_risks": total - len(closed),
                "by_severity": severity_rates,
                "overdue_risks": overdue_risks,
            },
        }
