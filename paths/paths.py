# Location => ./paths/paths.py

import sys
sys.dont_write_bytecode = True

from pathlib import Path

ROOT_DIR  = Path(__file__).resolve().parent.parent

DIR_MAPS  = ROOT_DIR / "maps"
DIR_UTILS = ROOT_DIR / "utils"
DIR_PAGES = ROOT_DIR / "pages"
DIR_ASSETS = ROOT_DIR / "assets"

# Maps
ROOM_TYPES_JSON     = DIR_MAPS / "room_types.json"
RATE_PLANS_JSON     = DIR_MAPS / "rate_plans.json"
CANCELLATION_JSON   = DIR_MAPS / "cancellation_policies.json"
SPACE_NAMES_JSON    = DIR_MAPS / "space_names.json"
SERVICES_JSON       = DIR_MAPS / "services.json"
EVENT_TYPES_JSON    = DIR_MAPS / "event_types.json"
PRICE_COMBOS_JSON   = DIR_MAPS / "price_combos.json"

# Pages
MAIN_APP    = ROOT_DIR / "app.py"
DASHBOARD   = DIR_PAGES / "1_dashboard.py"
SETTINGS    = DIR_PAGES / "2_settings.py"

# Assets
LOGO = DIR_ASSETS / "bird.png"

# Other
APP_NAME = "Event Monitor"
VERSION  = "1.1.2"