"""Compile locale/so/LC_MESSAGES/django.po to django.mo without GNU gettext."""
from pathlib import Path

import polib

ROOT = Path(__file__).resolve().parents[1]
PO = ROOT / "locale" / "so" / "LC_MESSAGES" / "django.po"
MO = PO.with_suffix(".mo")

if PO.exists():
    polib.pofile(str(PO)).save_as_mofile(str(MO))
    print(f"Compiled {MO}")
else:
    raise SystemExit(f"Missing {PO}")
