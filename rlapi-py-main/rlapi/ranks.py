from enum import IntEnum

TIER_NAMES = [
    "Unranked",
    "Bronze I", "Bronze II", "Bronze III",
    "Silver I", "Silver II", "Silver III",
    "Gold I", "Gold II", "Gold III",
    "Platinum I", "Platinum II", "Platinum III",
    "Diamond I", "Diamond II", "Diamond III",
    "Champion I", "Champion II", "Champion III",
    "Grand Champion I", "Grand Champion II", "Grand Champion III",
    "Supersonic Legend",
]

DIVISION_NAMES = ["I", "II", "III", "IV"]

PLAYLIST_NAMES = {
    10: "Ranked Duel 1v1",
    11: "Ranked Doubles 2v2",
    13: "Ranked Standard 3v3",
    27: "Hoops",
    28: "Rumble",
    29: "Dropshot",
    30: "Snow Day",
}

def tier_name(tier: int) -> str:
    if 0 <= tier < len(TIER_NAMES):
        return TIER_NAMES[tier]
    return f"Unknown ({tier})"

def division_name(div: int) -> str:
    if 0 <= div < len(DIVISION_NAMES):
        return DIVISION_NAMES[div]
    return str(div)

def playlist_name(playlist_id: int) -> str:
    return PLAYLIST_NAMES.get(playlist_id, f"Playlist {playlist_id}")