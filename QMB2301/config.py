from datetime import date

# ─── Course Settings ───────────────────────────────────────────────────────────
COURSE_NAME = "QMB 2301 – Business Stats and Analytics I"
SEMESTER    = "Summer 2026"
INSTRUCTOR  = "Dr. Seyedmasood Dastan"

# ─── Access Control ────────────────────────────────────────────────────────────
CLASS_PASSWORD = "miners2026"   # Change each semester

# ─── Date Range (tutor only works during the semester) ─────────────────────────
START_DATE = date(2026, 5, 21)  # TESTING — change back to date(2026, 6, 8) before deploying
END_DATE   = date(2026, 7, 7)   # One day after final deadline

# ─── Model ─────────────────────────────────────────────────────────────────────
MODEL      = "claude-haiku-4-5-20251001"
MAX_TOKENS = 1024
