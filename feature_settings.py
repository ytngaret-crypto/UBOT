FEATURE_SETTINGS = {
    "autoreply": {"enabled": True, "mode": "contains"},
    "antispam": {"enabled": False, "max_messages": 8, "window_seconds": 10, "mute_seconds": 60},
    "translate": {"enabled": False, "target_language": "id"},
    "ai": {"enabled": False, "model": "default", "system_prompt": "Jawab dengan singkat dan jelas."},
    "ocr": {"enabled": False, "language": "eng"},
    "music": {"enabled": False, "provider": "default"},
    "movie": {"enabled": False, "language": "id-ID"},
    "game": {"enabled": True, "xp_per_win": 10},
    "quiz": {"enabled": True, "question_count": 5},
    "random": {"enabled": True},
    "textgen": {"enabled": False, "model": "default"},
    "texttools": {"enabled": True},
    "jashare": {"enabled": False, "interval_seconds": 5},
    "payment": {"enabled": True},
}

def parse_value(raw):
    v = raw.strip()
    low = v.lower()
    if low in ("on", "true", "yes", "aktif"):
        return True
    if low in ("off", "false", "no", "nonaktif"):
        return False
    try:
        return int(v)
    except ValueError:
        return v
