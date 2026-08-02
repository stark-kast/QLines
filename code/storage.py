import json
import os
from config import PATTERNS_FILE

def get_pattern_sort_key(pattern):
    name = pattern.get("name", "").lower()
    key = []
    ru_alphabet = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
    for c in name:
        if c.isdigit():
            key.append((0, ord(c)))
        elif 'a' <= c <= 'z':
            key.append((1, ord(c)))
        elif c in ru_alphabet:
            key.append((2, ru_alphabet.index(c)))
        else:
            key.append((3, ord(c)))
    return key

def load_patterns():
    if os.path.exists(PATTERNS_FILE):
        try:
            with open(PATTERNS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return sorted(data, key=get_pattern_sort_key)
        except Exception:
            return []
    return []

def save_patterns_to_file(patterns_data):
    sorted_data = sorted(patterns_data, key=get_pattern_sort_key)
    with open(PATTERNS_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted_data, f, ensure_ascii=False, indent=2)

def get_next_pattern_name(patterns_data):
    existing_names = {p["name"] for p in patterns_data}
    idx = 1
    while f"pattern_{idx}" in existing_names:
        idx += 1
    return f"pattern_{idx}"