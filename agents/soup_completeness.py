from .base_agent import BaseAgent


REQUIRED_FIELDS = [
    "version",
    "license",
    "has_risk_assessment",
    "has_validation_record",
    "last_reviewed_at",
]


class SoupCompletenessAgent(BaseAgent):
    """Completeness of SOUP register records."""

    def _is_filled(self, value) -> bool:
        if value is None:
            return False
        if isinstance(value, str) and value.strip() == "":
            return False
        if isinstance(value, list) and len(value) == 0:
            return False
        if value is False:
            return False
        return True

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
                value = lib.get(field)
                if self._is_filled(value):
                    filled += 1
                else:
                    missing.append(field)

            if missing:
                incomplete_libs.append({
                    "library_name": lib.get("library_name") or lib.get("name") or str(lib.get("_id")),
                    "version": lib.get("version") or "",
                    "missing_fields": missing,
                })

        completeness = round(filled / total_fields * 100, 2) if total_fields else 0.0

        return {
            "metric": "soup_completeness",
            "value": completeness,
            "unit": "% complete SOUP fields",
            "trend": "not_calculated",
            "trend_delta": None,
            "period": "current",
            "sample_size": total,
            "warning": "No documents found in soup_register collection" if total == 0 else self.low_sample_warning(total),
            "details": {
                "total_libraries": total,
                "required_fields": REQUIRED_FIELDS,
                "fully_complete_count": total - len(incomplete_libs),
                "incomplete_count": len(incomplete_libs),
                "incomplete_libraries": incomplete_libs,
            },
        }
