"""Single source of truth for the bundled Atlas location (contract: docs/features/ATLAS.md §4)."""

from azimuth.paths import ROOT

# Runtime copy of Azimuth Atlas v2: the package quas_atlas (pages, Python models, local server).
ATLAS_HOME = ROOT / 'modules' / 'atlas' / 'atlas_v2'
SITE_ROOT = ATLAS_HOME / 'quas_atlas' / 'web'
ATLAS_ENTRY = SITE_ROOT / 'index.html'
# Author's Atlas 0.80 site (file-based, calculations in JavaScript); kept as source material, not loaded.
LEGACY_SITE = ROOT / 'modules' / 'atlas' / 'QuAS_Атлас_сайт'
