from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .schemas import UserPreference


class PreferencesManager:
    def __init__(self) -> None:
        self.preferences: dict[str, dict[str, UserPreference]] = {}

    def set_preference(
        self, user_id: str, key: str, value: Any, category: str = "general"
    ) -> dict:
        if user_id not in self.preferences:
            self.preferences[user_id] = {}
        if key in self.preferences[user_id]:
            pref = self.preferences[user_id][key]
            pref.value = value
            pref.category = category
            pref.updated_at = datetime.now(timezone.utc)
        else:
            pref = UserPreference(key=key, value=value, category=category)
            self.preferences[user_id][key] = pref
        return pref.to_dict()

    def get_preference(self, user_id: str, key: str, default: Any = None) -> Any:
        user_prefs = self.preferences.get(user_id, {})
        pref = user_prefs.get(key)
        return pref.value if pref else default

    def get_all_preferences(
        self, user_id: str, category: str | None = None
    ) -> list[dict]:
        user_prefs = self.preferences.get(user_id, {})
        result = list(user_prefs.values())
        if category:
            result = [p for p in result if p.category == category]
        return [p.to_dict() for p in result]

    def delete_preference(self, user_id: str, key: str) -> bool:
        user_prefs = self.preferences.get(user_id, {})
        if key in user_prefs:
            del user_prefs[key]
            return True
        return False

    def get_categories(self, user_id: str) -> list[str]:
        user_prefs = self.preferences.get(user_id, {})
        return sorted({p.category for p in user_prefs.values()})

    def to_dict(self) -> dict:
        return {
            uid: {k: v.to_dict() for k, v in prefs.items()}
            for uid, prefs in self.preferences.items()
        }
