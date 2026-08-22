from datetime import date

# ─── Course Settings ───────────────────────────────────────────────────────────
COURSE_NAME = "QMB 2301 – Business Stats and Analytics I"
SEMESTER    = "Fall 2026"
INSTRUCTOR  = "Dr. Masood Dastan"

# ─── Access Control ────────────────────────────────────────────────────────────
REQUIRE_PASSWORD = False          # Set to True to enable password gate

# ─── Date Range (tutor only works during the semester) ─────────────────────────
# Covers both the 16-week (CRN 10491, retake deadline Dec 10) and 8-week
# (CRN 18080, retake deadline Oct 13) sections. Set to the later of the two
# end dates so the longer section isn't cut off early.
START_DATE = date(2026, 8, 24)
END_DATE   = date(2026, 12, 11)   # One day after CRN 10491's retake deadline (Dec 10)

# ─── Resources (private GitHub repo subfolder for this course) ─────────────────
RESOURCES_PATH = "QMB2301"

# ─── Model ─────────────────────────────────────────────────────────────────────
MODEL      = "claude-haiku-4-5-20251001"
MAX_TOKENS = 1024
