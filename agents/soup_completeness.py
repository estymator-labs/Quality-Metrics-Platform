from .base_agent import BaseAgent

REQUIRED_FIELDS = ["license", "has_risk_assessment", "has_validation_record", "last_reviewed_at"]


class SoupCompletenessAgent(BaseAgent):
    """completeness = filled_required_fields / total_required_fields * 100"""

    def run(self) -> dict:
        col = self.collection("soup_register")
        all_libs = list(col.find({}))
        total = len(all_libs)
        total_fields = total * len(REQUIRED_FIELDS)

        filled = 0
        incomplete_libs = []

        for lib in all_libs:
            missing = []
            for field in REQUIRED_FIELDS:
                val = lib.get(field)
                if val is None or val == "" or val is False:
                    missing.append(field)
                else:
                    filled += 1
            if missing:
                incomplete_libs.append({
                    "library_name": lib.get("library_name"),
                    "version": lib.get("version"),
                    "missing_fields": missing,
                })

        completeness = round(filled / total_fields * 100, 2) if total_fields else 0.0

        n = total
        return {
            "metric": "soup_completeness",
            "value": completeness,
            "unit": "percent complete",
            "trend": "n/a",
            "trend_delta": 0.0,
            "period": "current",
            "sample_size": n,
            "warning": self.low_sample_warning(n),
            "details": {
                "total_libraries": total,
                "required_fields": REQUIRED_FIELDS,
                "fully_complete_count": total - len(incomplete_libs),
                "incomplete_count": len(incomplete_libs),
                "incomplete_libraries": incomplete_libs,
            },
        }
