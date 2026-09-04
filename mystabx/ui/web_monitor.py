"""Deferred read-only web dashboard.

Do not implement a browser trading desk here. If a web view is added later it
must be read-only (account / position / logs) and must never place, amend, or
cancel orders. All order flow stays in the desktop MainEngine process.
"""
