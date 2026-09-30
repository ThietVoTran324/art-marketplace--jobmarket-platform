#!/usr/bin/env python3
import json
from pathlib import Path

vi_path = Path("vuejs/src/i18n/locales/vi.json")
en_path = Path("vuejs/src/i18n/locales/en.json")
vi = json.loads(vi_path.read_text(encoding="utf-8"))
en = json.loads(en_path.read_text(encoding="utf-8"))

FIXES = {
    "common.ok": "OK",
    "pin.card.gifBadge": "Gif",
    "pin.card.pinImageAlt": "Ảnh pin",
    "pin.pinView.okUnderstand": "Đã hiểu",
    "jobMarket.cvTab.title": "CV",
    "settings.payment.binPrefix": "BIN",
    "settings.payment.payoutPin": "Pin #{pinId}",
    "settings.payment.payoutAmountVnd": "{amount} VND",
    "authModal.common.ok": "OK",
    "admin.nav.kyc": "KYC",
    "admin.content.deletePin.toast.success": "Đã xóa pin #{id}",
    "admin.copyright.table.pin": "Pin",
    "admin.paymentMethods.table.binPrefix": "BIN {bankCode} · ",
    "admin.payouts.table.pin": "Pin",
    "admin.payouts.table.amountVnd": "Số tiền VND",
    "admin.payouts.table.binPrefix": "BIN {payoutBankCode} · ",
    "createPin.documentTitle.default": "Pinterest",
    "createPin.fileErrorModal.confirm": "Đã hiểu",
    "createPin.marketplace.currencyUsd": "USD",
    "createPin.marketplace.currencyVnd": "VND",
    "explore.filters.currencyVnd": "VND",
    "explore.filters.currencyUsd": "USD",
    "chat.userChat.gif": "Gif",
    "chat.newMessageToast.gif": "Gif",
    "chat.websocketChat.ok": "OK",
    "chat.websocketChat.messagePlaceholder": "Aa",
    "chat.websocketChat.pinConversation": "Ghim cuộc trò chuyện",
    "home.pinFeedCard.pinAlt": "Pin",
    "profile.tabs.cv": "CV",
    "profile.errors.okUnderstand": "Đã hiểu",
    "comments.commentSection.okUnderstand": "Đã hiểu",
    "social.activityFeed.pinAlt": "Pin",
}


def set_path(d, dotted, value):
    parts = dotted.split(".")
    cur = d
    for p in parts[:-1]:
        cur = cur[p]
    cur[parts[-1]] = value


for k, v in FIXES.items():
    set_path(vi, k, v)

vi.setdefault("home", {}).setdefault("search", {})["noResults"] = "Không tìm thấy kết quả"
vi.setdefault("home", {}).setdefault("search", {})["loading"] = "Đang tải…"
en.setdefault("home", {}).setdefault("search", {})["noResults"] = "No results found"
en.setdefault("home", {}).setdefault("search", {})["loading"] = "Loading…"

vi_path.write_text(json.dumps(vi, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
en_path.write_text(json.dumps(en, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

# verify no more GIỮ
left = []


def walk(d, p=""):
    for k, v in d.items():
        path = f"{p}{k}"
        if isinstance(v, dict):
            walk(v, path + ".")
        elif isinstance(v, str) and ("GIỮ" in v or v.startswith("__")):
            left.append((path, v))


walk(vi)
print("fixed", len(FIXES), "remaining_bad", len(left))
for x in left:
    print(x)
