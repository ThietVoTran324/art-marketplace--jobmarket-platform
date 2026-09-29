import { defineStore } from "pinia";
import { ref, watch } from "vue";
import axios from "axios";

const PREFS_KEY = "pinterest_chat_prefs_v1";

const ACCENT = {
  red: { solid: "#e11d48", soft: "#fff1f2", muted: "#fda4af" },
  blue: { solid: "#2563eb", soft: "#eff6ff", muted: "#93c5fd" },
  lime: { solid: "#65a30d", soft: "#f7fee7", muted: "#bef264" },
  yellow: { solid: "#ca8a04", soft: "#fefce8", muted: "#fde047" },
  purple: { solid: "#7c3aed", soft: "#f5f3ff", muted: "#d8b4fe" },
};

function loadPrefs() {
  try {
    const raw = localStorage.getItem(PREFS_KEY);
    if (!raw) return { muted: [], pinned: [] };
    const parsed = JSON.parse(raw);
    return {
      muted: Array.isArray(parsed.muted) ? parsed.muted.map(Number) : [],
      pinned: Array.isArray(parsed.pinned) ? parsed.pinned.map(Number) : [],
    };
  } catch {
    return { muted: [], pinned: [] };
  }
}

function applyAccent(color) {
  const a = ACCENT[color] || ACCENT.blue;
  document.documentElement.style.setProperty("--msg-accent", a.solid);
  document.documentElement.style.setProperty("--msg-accent-soft", a.soft);
  document.documentElement.style.setProperty("--msg-accent-muted", a.muted);
  document.documentElement.style.setProperty("--scrollbar-thumb-bg", a.solid);
  document.documentElement.style.setProperty("--scrollbar-thumb-bg-chats", a.solid);
  document.documentElement.style.setProperty("--scrollbar-track-bg", "#f3f4f6");
  document.documentElement.style.setProperty("--selection-bg", a.muted);
}

export const useChatStore = defineStore("chat", () => {
  const bgColor = ref(null);
  const size = ref(320);
  const side = ref(false);
  const prefs = ref(loadPrefs());

  function persistPrefs() {
    localStorage.setItem(
      PREFS_KEY,
      JSON.stringify({
        muted: prefs.value.muted,
        pinned: prefs.value.pinned,
      })
    );
  }

  const isMuted = (chatId) => prefs.value.muted.includes(Number(chatId));
  const isPinned = (chatId) => prefs.value.pinned.includes(Number(chatId));

  function toggleMute(chatId) {
    const id = Number(chatId);
    const set = new Set(prefs.value.muted);
    if (set.has(id)) set.delete(id);
    else set.add(id);
    prefs.value = { ...prefs.value, muted: [...set] };
    persistPrefs();
  }

  function togglePin(chatId) {
    const id = Number(chatId);
    const set = new Set(prefs.value.pinned);
    if (set.has(id)) set.delete(id);
    else set.add(id);
    prefs.value = { ...prefs.value, pinned: [...set] };
    persistPrefs();
  }

  watch(bgColor, (c) => {
    if (c) applyAccent(c);
  });

  const fetchSide = async () => {
    try {
      const response = await axios.get("/api/chats/side", { withCredentials: true });
      side.value = response.data;
    } catch (error) {
      console.error("Failed to load chat side:", error);
    }
  };

  const setSide = (next) => {
    side.value = next;
  };

  const fetchChatColor = async () => {
    try {
      const response = await axios.get("/api/chats/color", { withCredentials: true });
      bgColor.value = response.data || "blue";
      applyAccent(bgColor.value);
    } catch (error) {
      console.error("Failed to load chat color:", error);
      bgColor.value = "blue";
      applyAccent("blue");
    }
  };

  const setChatColor = (color) => {
    bgColor.value = color;
    applyAccent(color);
  };

  const fetchChatSize = async () => {
    try {
      const response = await axios.get("/api/chats/size", { withCredentials: true });
      const n = Number(response.data);
      size.value = Number.isFinite(n) && n >= 280 ? n : 320;
    } catch (error) {
      console.error("Failed to load chat size:", error);
      size.value = 320;
    }
  };

  const setChatSize = (next) => {
    size.value = next;
  };

  return {
    bgColor,
    fetchChatColor,
    setChatColor,
    size,
    fetchChatSize,
    setChatSize,
    fetchSide,
    setSide,
    side,
    prefs,
    isMuted,
    isPinned,
    toggleMute,
    togglePin,
  };
});
