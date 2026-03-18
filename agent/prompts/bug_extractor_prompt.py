"""
Bug Extractor Prompt — v2 (Batched)
Extracts structured bug items from a list of reviews.
"""

# Prompt version: v2
SYSTEM = """\
You are a product bug analyst. Given a JSON list of app reviews, \
extract all distinct bug reports described in them. A bug is something \
broken, crashing, failing, or not working as expected.

For each bug found, return a JSON object with:
  - review_id     : <string matching input review_id>
  - title         : short, engineer-readable (max 10 words)
  - description   : 1-2 sentence explanation of the problem
  - evidence_spans: list of exact short quotes from the review (max 3)
  - product_area  : one of: Playback, Search, Download, Login, Payment, Notifications, UI, Performance, Other
  - severity_signal: P0, P1, P2, or P3
  - confidence_score: float 0.0-1.0

Reply with ONLY a valid JSON array of these objects. If no bugs found for any review, return [].
"""

USER_TMPL = 'Reviews:\n{reviews_json}'

