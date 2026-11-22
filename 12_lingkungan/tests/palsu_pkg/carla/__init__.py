"""Paket 'carla' palsu untuk uji end-to-end runner (lihat tests/carla_palsu.py). Dikonfigurasi lewat env var:
CARLA_PALSU_CITRA (folder PNG), CARLA_PALSU_GT (GT v2 lengkap), CARLA_PALSU_V (km/jam per throttle)."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import carla_palsu as _p  # noqa: E402
from carla_palsu import *  # noqa: F401,F403,E402

_p.Client.CITRA_DIR = os.environ.get("CARLA_PALSU_CITRA", "")
if os.environ.get("CARLA_PALSU_GT"):
    with open(os.environ["CARLA_PALSU_GT"], encoding="utf-8") as _f:
        _p.Client.SLOT = json.load(_f)
if os.environ.get("CARLA_PALSU_V"):
    _p.V_MAKS_KMH_PER_THROTTLE = float(os.environ["CARLA_PALSU_V"])
if os.environ.get("CARLA_PALSU_SETIR"):
    _p.FAKTOR_SETIR = float(os.environ["CARLA_PALSU_SETIR"])
if os.environ.get("CARLA_PALSU_BUG"):
    _p.BUG_TOGGLE = float(os.environ["CARLA_PALSU_BUG"])
_p.TOGGLE_DIR = os.environ.get("CARLA_PALSU_TOGGLE_DIR", "")
