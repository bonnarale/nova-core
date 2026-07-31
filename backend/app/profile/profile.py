from __future__ import annotations

from datetime import datetime, timezone

from .schemas import UserProfile


class ProfileManager:
    def __init__(self) -> None:
        self.profiles: dict[str, UserProfile] = {}

    def create_profile(
        self,
        user_id: str,
        username: str,
        email: str = "",
        display_name: str = "",
        role: str = "user",
    ) -> dict:
        profile = UserProfile(
            id=user_id,
            username=username,
            email=email,
            display_name=display_name,
            role=role,
        )
        self.profiles[user_id] = profile
        return profile.to_dict()

    def get_profile(self, user_id: str) -> dict | None:
        profile = self.profiles.get(user_id)
        return profile.to_dict() if profile else None

    def update_profile(self, user_id: str, **kwargs) -> dict | None:
        profile = self.profiles.get(user_id)
        if not profile:
            return None
        for key, value in kwargs.items():
            if hasattr(profile, key) and key not in ("id", "created_at"):
                setattr(profile, key, value)
        profile.updated_at = datetime.now(timezone.utc)
        return profile.to_dict()

    def delete_profile(self, user_id: str) -> bool:
        if user_id in self.profiles:
            del self.profiles[user_id]
            return True
        return False

    def list_profiles(self) -> list[dict]:
        return [p.to_dict() for p in self.profiles.values()]

    def to_dict(self) -> dict:
        return {uid: p.to_dict() for uid, p in self.profiles.items()}
