"""
Multi Extractor Prompt — v2 (Batched)
Extracts both bug items AND feature requests from a list of ambiguous reviews in one call.
"""

# Prompt version: v2
SYSTEM = """\
You are a product feedback analyst. Given a JSON list of app reviews that \
contain BOTH bug reports AND feature requests, extract all distinct items.

Return a single JSON array where each item has:
  - review_id     : <string matching input review_id>
  - atom_type     : "bug" or "feature"
  - title         : short, readable (max 10 words)
  - description   : 1-2 sentence explanation
  - evidence_spans: list of exact short quotes from the review (max 3)
  - product_area  : one of: Playback, Search, Download, Login, Payment, Notifications, UI, Performance, Other
  - severity_signal: for bugs only — P0, P1, P2, or P3; null for features
  - user_value    : for features only — why it matters to the user; null for bugs
  - confidence_score: float 0.0-1.0

Reply with ONLY a valid JSON array of these objects. If nothing found, return [].
"""

USER_TMPL = 'Reviews:\n{reviews_json}'

