# ABOUTME: Searches a catalog by learner-visible ID, slug or title fragment.
# ABOUTME: The first matching kind wins: ID, then slug, then title substring.

from practice.catalog import Catalog, Entry


def search(catalog: Catalog, query: str) -> list[Entry]:
    text = query.strip().lower()
    if not text:
        return []
    entries = catalog.entries  # Stored in frontend ID order.

    if text.isdecimal():
        by_id = [e for e in entries if e.frontend_question_id == int(text)]
        if by_id:
            return by_id

    by_slug = [e for e in entries if e.slug == text]
    if by_slug:
        return by_slug

    by_title = [e for e in entries if text in e.title.lower()]
    # An exact title leads; sorted() is stable so the rest stay in ID order.
    return sorted(by_title, key=lambda e: e.title.lower() != text)
