from typing import Literal

from pydantic import BaseModel, EmailStr


class UserIn(BaseModel):
    username: str
    password: str
    email: EmailStr | None = None


class UserOut(BaseModel):
    id: int
    username: str
    image: str | None = None
    email: EmailStr | None = None
    verified: bool | None = None
    banner_image: str | None = None
    description: str | None = None
    instagram: str | None = None
    tiktok: str | None = None
    telegram: str | None = None
    pinterest: str | None = None
    account_kind: str = "personal"
    company_id: int | None = None
    show_saved_boards: bool = True


class UserPatch(BaseModel):
    username: str | None = None
    email: EmailStr | None = None
    description: str | None = None
    instagram: str | None = None
    tiktok: str | None = None
    telegram: str | None = None
    pinterest: str | None = None


class PasswordResetRequestModel(BaseModel):
    username: str
    email: EmailStr
    password: str


class NotificationPrefsOut(BaseModel):
    likes: bool = True
    comments: bool = True
    follows: bool = True
    messages: bool = True
    jobApps: bool = True
    marketplace: bool = True


class PrivacyPrefsOut(BaseModel):
    profileDiscoverable: bool = True
    showSavedBoards: bool = True
    allowMessagesFrom: Literal["everyone", "followers", "none"] = "everyone"


class UserPreferencesOut(BaseModel):
    notifications: NotificationPrefsOut
    privacy: PrivacyPrefsOut
    initialized: bool = False


class NotificationPrefsPatch(BaseModel):
    likes: bool | None = None
    comments: bool | None = None
    follows: bool | None = None
    messages: bool | None = None
    jobApps: bool | None = None
    marketplace: bool | None = None


class PrivacyPrefsPatch(BaseModel):
    profileDiscoverable: bool | None = None
    showSavedBoards: bool | None = None
    allowMessagesFrom: Literal["everyone", "followers", "none"] | None = None


class UserPreferencesPatch(BaseModel):
    notifications: NotificationPrefsPatch | None = None
    privacy: PrivacyPrefsPatch | None = None
