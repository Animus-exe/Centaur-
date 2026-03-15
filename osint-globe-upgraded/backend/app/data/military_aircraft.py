"""
Curated military/government aircraft identifiers for OSINT classification.
ICAO type designators from Doc 8643 and common OSINT sources.
ICAO24 prefixes: known military/state allocation blocks (2-char hex, lower).
"""

# ICAO aircraft type designators commonly associated with military/government use.
# Normalized to uppercase; match first 2-4 chars from raw "t" or "type" field.
MILITARY_AIRCRAFT_TYPES = frozenset({
    "A4", "A10", "A29", "A37", "A400", "A400M",
    "B1", "B2", "B52", "B350", "BE20", "BE40",  # B350/BE20/BE40 used by militaries
    "C2", "C5", "C12", "C17", "C20", "C26", "C27", "C28", "C29", "C30", "C32",
    "C37", "C38", "C40", "C130", "C135", "C140", "C141", "C160", "C212", "C235",
    "C295", "C390", "CASA", "CN35",
    "E2", "E3", "E4", "E6", "E8", "E8C", "E9", "EC35", "EJET",
    "F4", "F5", "F14", "F15", "F16", "F18", "F22", "F35", "F111", "F117",
    "G222", "G550", "GLF4", "GLF5", "GLF6",  # Gulfstream gov/mil
    "H60", "H64", "H130", "H135", "H145", "H160", "H215", "H225", "H47", "H53",
    "K35", "K35R", "KC10", "KC130", "KC135", "KC46", "KC767",
    "P3", "P8", "P180", "PC12", "PC21",  # PC12/PC21 used by armed forces
    "R135", "RC135", "RC12", "RJ70", "RJ85", "RJ1H",
    "T38", "T45", "T6", "T34", "T37", "T39", "T43",
    "U2", "UH60", "UH1", "UH72",
    "V22", "VH60", "VH3", "VC25", "C32",
    "Y12", "Y20",
    "C17", "C130J", "C27J", "C40B", "C40C",
    "F15E", "F16C", "F16D", "F18C", "F18E", "F18F",
    "E2C", "E2D", "E3A", "E6B", "E8C",
    "KC10A", "KC135R", "KC135T", "KC46A",
    "P3C", "P8A", "RC135V", "RC135W", "RC135U",
    "C5M", "C130H", "C130J", "A400", "C27", "C295",
})

# ICAO24 hex prefixes (2 chars, lower) commonly associated with military/state blocks.
# US DoD (ae, ad), NATO and other allocations; used only when no strong type/callsign signal.
MILITARY_ICAO24_PREFIXES = frozenset({
    "ad",  # US (DoD)
    "ae",  # US (DoD)
    "af",  # US (Air Force)
    "43",  # Japan (military block)
    "48",  # Poland (includes military)
    "4b",  # Switzerland (military block)
    "33",  # Italy (military block)
    "3f",  # Germany (military block)
    "3e",  # Germany
    "39",  # Italy
    "0d",  # Mexico (gov/mil)
    "0f",  # (various)
    "06",  # Egypt (mil)
    "02",  # (various)
})
