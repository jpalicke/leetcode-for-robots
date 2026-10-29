# ABOUTME: Builds endpoint-shaped test data from the real committed catalog.
# ABOUTME: Shares one full-row translator across refresh tests without network mocks.

import json
from typing import Any

from practice.catalog import DEFAULT_CATALOG_PATH


def payload() -> dict[str, Any]:
    data = json.loads(DEFAULT_CATALOG_PATH.read_text(encoding="utf-8"))
    return {
        "stat_status_pairs": [
            {
                "stat": {
                    "frontend_question_id": e["frontend_question_id"],
                    "question_id": e["question_id"],
                    "question__title": e["title"],
                    "question__title_slug": e["slug"],
                },
                "difficulty": {
                    "level": {"easy": 1, "medium": 2, "hard": 3}[e["difficulty"]]
                },
                "paid_only": e["paid_only"],
            }
            for e in data["entries"]
        ]
    }
