"""Shared styling for NEXUS — a restrained, editorial-terminal aesthetic.
No emoji anywhere; typographic marks and color do the signaling instead.

IMPORTANT: the CSS below is emitted as a single <style> block with NO blank
lines anywhere inside it. Streamlit's markdown renderer follows CommonMark's
raw-HTML-block rules, and a blank line terminates most HTML block types —
except script/style/pre/textarea, which read until their closing tag
regardless of blank lines. To rely on that safely, this string must (a)
start immediately with '<style' as the very first characters, so it's
recognized as that exception type, and (b) never mix in a '<link>' tag
before it, since <link> is a different block type that DOES end at a blank
line. The Google Font is loaded via @import inside the stylesheet instead
of a <link> tag for exactly this reason. Keep this file blank-line-free
inside CSS if you edit it."""
import streamlit as st

CSS = (
    "<style>"
    "@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');"
    ":root {"
    "--bg: #08080a; --panel: #131318; --panel-2: #17171e; --border: #26262f; --border-soft: #1d1d24;"
    "--text: #e9e7e2; --muted: #8b8b96; --muted-2: #5f5f6b;"
    "--gold: #c9a876; --gold-soft: #e4d3ab; --gold-dim: #8a7550;"
    "--green: #4fa87c; --red: #c2564c; --amber: #cf9f52; --blue: #6f93b8;"
    "}"
    "html, body, [class*='css'] { font-family: 'IBM Plex Mono', 'Consolas', monospace; }"
    ".stApp {"
    "background:"
    "radial-gradient(760px 420px at 12% -6%, rgba(201,168,118,0.10) 0%, transparent 60%),"
    "radial-gradient(900px 520px at 108% 6%, rgba(111,147,184,0.08) 0%, transparent 55%),"
    "radial-gradient(700px 500px at 50% 115%, rgba(201,168,118,0.05) 0%, transparent 60%),"
    "var(--bg);"
    "color: var(--text);"
    "}"
    "section[data-testid='stSidebar'] { background-color: var(--panel); border-right: 1px solid var(--border); }"
    "[data-testid='stSidebarNav'] li a span { font-size: 0.84rem; letter-spacing: 0.02em; }"
    "@keyframes fadeInUp { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }"
    "@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }"
    "@keyframes shimmer { to { background-position: 200% center; } }"
    "@keyframes growLine { from { width: 0; } to { width: 46px; } }"
    "@keyframes pulseRing { 0% { box-shadow: 0 0 0 0 rgba(79,168,124,0.35); } 70% { box-shadow: 0 0 0 6px rgba(79,168,124,0); } 100% { box-shadow: 0 0 0 0 rgba(79,168,124,0); } }"
    "@keyframes sheen { from { transform: translateX(-120%) skewX(-15deg); } to { transform: translateX(220%) skewX(-15deg); } }"
    "@keyframes softRise { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }"
    "@keyframes floatOrb { 0%, 100% { transform: translateY(0) translateX(0); } 50% { transform: translateY(-14px) translateX(6px); } }"
    ".stApp, [data-testid='stAppViewContainer'] > .main { animation: fadeIn 0.6s ease both; }"
    "div[data-testid='stVerticalBlockBorderWrapper'], .element-container { animation: softRise 0.4s ease both; }"
    ".nx-glow {"
    "position: fixed; border-radius: 50%; filter: blur(70px); pointer-events: none; z-index: 0; opacity: 0.55;"
    "animation: floatOrb 12s ease-in-out infinite;"
    "}"
    ".nx-glow-a { top: -120px; left: -80px; width: 360px; height: 360px; background: radial-gradient(circle, rgba(201,168,118,0.35), transparent 70%); }"
    ".nx-glow-b { top: 40px; right: -140px; width: 420px; height: 420px; background: radial-gradient(circle, rgba(111,147,184,0.28), transparent 70%); animation-delay: -6s; }"
    ".nx-header-title {"
    "position: relative; z-index: 1;"
    "font-family: 'Playfair Display', Georgia, serif; font-weight: 700;"
    "font-size: 2.7rem; letter-spacing: 0.05em; margin-bottom: 0; line-height: 1.08;"
    "background: linear-gradient(110deg, var(--gold-soft) 0%, var(--gold) 35%, var(--gold-dim) 55%, var(--gold) 75%, var(--gold-soft) 100%);"
    "background-size: 220% auto;"
    "-webkit-background-clip: text; -webkit-text-fill-color: transparent;"
    "animation: shimmer 8s linear infinite;"
    "}"
    ".nx-header-sub {"
    "font-family: 'IBM Plex Mono', monospace; color: var(--muted); font-size: 0.82rem;"
    "letter-spacing: 0.24em; text-transform: uppercase; margin-top: 4px;"
    "}"
    ".nx-section-title {"
    "position: relative; font-size: 0.78rem; letter-spacing: 0.18em; color: var(--muted-2);"
    "text-transform: uppercase; padding-bottom: 8px; margin: 28px 0 14px 0;"
    "border-bottom: 1px solid var(--border-soft);"
    "}"
    ".nx-section-title::after {"
    "content: ''; position: absolute; left: 0; bottom: -1px; height: 1px; width: 0;"
    "background: var(--gold); animation: growLine 0.9s cubic-bezier(.2,.7,.2,1) forwards; animation-delay: 0.1s;"
    "}"
    ".nx-card {"
    "position: relative; z-index: 1;"
    "background: linear-gradient(180deg, var(--panel-2) 0%, var(--panel) 100%);"
    "border: 1px solid var(--border); border-radius: 12px; padding: 17px 19px; margin-bottom: 12px;"
    "animation: fadeInUp 0.45s cubic-bezier(.2,.7,.2,1) both;"
    "transition: transform 0.28s ease, box-shadow 0.28s ease, border-color 0.28s ease;"
    "}"
    ".nx-card:hover {"
    "transform: translateY(-3px);"
    "box-shadow: 0 16px 34px -14px rgba(0,0,0,0.6), 0 0 0 1px rgba(201,168,118,0.14);"
    "border-color: var(--gold-dim);"
    "}"
    ".nx-nav-card {"
    "position: relative; overflow: hidden; z-index: 1;"
    "background: linear-gradient(160deg, var(--panel-2), var(--panel));"
    "border: 1px solid var(--border); border-radius: 14px; padding: 22px; height: 100%;"
    "transition: transform 0.32s cubic-bezier(.2,.7,.2,1), box-shadow 0.32s ease, border-color 0.32s ease;"
    "animation: fadeInUp 0.5s cubic-bezier(.2,.7,.2,1) both;"
    "}"
    ".nx-nav-card::before {"
    "content: ''; position: absolute; top: 0; left: -30%; width: 30%; height: 100%;"
    "background: linear-gradient(115deg, transparent, rgba(233,231,226,0.06), transparent);"
    "transform: translateX(-120%) skewX(-15deg); pointer-events: none;"
    "}"
    ".nx-nav-card:hover {"
    "transform: translateY(-6px); border-color: var(--gold-dim);"
    "box-shadow: 0 24px 46px -20px rgba(0,0,0,0.65);"
    "}"
    ".nx-nav-card:hover::before { animation: sheen 1.1s ease forwards; }"
    ".nx-nav-card h4 {"
    "margin: 6px 0 6px 0; color: var(--text); font-family: 'Playfair Display', serif;"
    "font-weight: 600; font-size: 1.14rem; letter-spacing: 0.02em;"
    "}"
    ".nx-nav-card p { color: var(--muted); font-size: 0.83rem; line-height: 1.55; margin: 0; }"
    ".nx-nav-card .nx-kicker { font-size: 0.68rem; letter-spacing: 0.2em; text-transform: uppercase; color: var(--gold-dim); }"
    ".nx-badge {"
    "display: inline-block; padding: 3px 12px; border-radius: 20px; font-weight: 600;"
    "font-size: 0.76rem; letter-spacing: 0.05em; transition: box-shadow 0.3s ease;"
    "}"
    ".nx-source-tag {"
    "display: inline-block; font-size: 0.65rem; padding: 2px 9px; border-radius: 20px;"
    "letter-spacing: 0.08em; font-weight: 700; text-transform: uppercase;"
    "}"
    ".nx-source-tag.is-live { animation: pulseRing 2.4s ease-in-out infinite; }"
    ".nx-row { display: flex; align-items: flex-start; gap: 9px; padding: 4px 0; font-size: 0.85rem; animation: fadeInUp 0.35s ease both; }"
    ".nx-dot { flex: 0 0 auto; width: 6px; height: 6px; border-radius: 50%; margin-top: 6px; }"
    ".nx-row-text { color: var(--text); line-height: 1.5; }"
    ".nx-warning-strip {"
    "border-left: 2px solid var(--amber); padding: 4px 0 4px 10px; margin: 4px 0;"
    "font-size: 0.83rem; color: var(--amber); background: linear-gradient(90deg, rgba(207,159,82,0.06), transparent);"
    "}"
    ".nx-trace-line {"
    "font-size: 0.8rem; color: var(--muted); padding: 2px 0; border-left: 1px solid var(--border-soft);"
    "padding-left: 10px; animation: fadeInUp 0.3s ease both;"
    "}"
    ".nx-disclaimer {"
    "font-size: 0.72rem; color: var(--muted-2); border-top: 1px solid var(--border-soft);"
    "padding-top: 10px; margin-top: 26px; letter-spacing: 0.01em;"
    "}"
    ".nx-evidence-src { font-size: 0.78rem; color: var(--blue); font-weight: 600; letter-spacing: 0.02em; }"
    ".nx-evidence-chunk { font-size: 0.83rem; color: var(--muted); font-style: italic; line-height: 1.55; }"
    ".stButton > button {"
    "border: 1px solid var(--border) !important; background: var(--panel-2) !important;"
    "color: var(--text) !important; border-radius: 24px !important;"
    "transition: all 0.25s ease !important; letter-spacing: 0.04em;"
    "}"
    ".stButton > button:hover {"
    "border-color: var(--gold) !important; color: var(--gold-soft) !important;"
    "transform: translateY(-1px); box-shadow: 0 8px 18px -8px rgba(201,168,118,0.4);"
    "}"
    "button[kind='primary'] {"
    "background: linear-gradient(120deg, var(--gold-dim), var(--gold)) !important;"
    "border: none !important; color: #12100b !important; font-weight: 600 !important;"
    "}"
    "button[kind='primary']:hover { box-shadow: 0 10px 24px -8px rgba(201,168,118,0.55) !important; }"
    "[data-testid='stMetricValue'] { transition: color 0.3s ease; }"
    "hr { border-color: var(--border-soft) !important; }"
    "</style>"
)

SIGNAL_COLORS = {
    "BULLISH": "#4fa87c", "BEARISH": "#c2564c", "NEUTRAL": "#8b8b96",
    "CAUTION": "#cf9f52", "MONITOR": "#c9a876", "ACCEPTABLE": "#4fa87c",
    "ACCUMULATE": "#4fa87c", "HOLD": "#6f93b8", "WATCH": "#cf9f52",
    "REDUCE": "#c47a45", "AVOID": "#c2564c",
    "CONFLICT_DETECTED": "#c2564c", "REVIEW_RECOMMENDED": "#cf9f52", "CONSISTENT": "#4fa87c",
    "UNAVAILABLE": "#5f5f6b",
}


def signal_color(signal: str) -> str:
    return SIGNAL_COLORS.get(signal, "#8b8b96")


def badge(text: str) -> str:
    color = signal_color(text)
    return f'<span class="nx-badge" style="background:{color}1f;color:{color};border:1px solid {color}55;">{text}</span>'


def source_tag(label: str) -> str:
    is_live = label.upper().startswith("LIVE")
    color = "#4fa87c" if is_live else "#8b8b96"
    cls = "nx-source-tag is-live" if is_live else "nx-source-tag"
    return f'<span class="{cls}" style="background:{color}1f;color:{color};border:1px solid {color}55;">{label}</span>'


def row(text: str, tone: str = "neutral") -> str:
    colors = {"positive": "#4fa87c", "negative": "#c2564c", "neutral": "#6f93b8"}
    color = colors.get(tone, colors["neutral"])
    return f'<div class="nx-row"><span class="nx-dot" style="background:{color};"></span><span class="nx-row-text">{text}</span></div>'


def warning_strip(text: str) -> str:
    return f'<div class="nx-warning-strip">{text}</div>'


def glow_orbs() -> str:
    """Two soft floating background glows for visual depth — call once per page."""
    return '<div class="nx-glow nx-glow-a"></div><div class="nx-glow nx-glow-b"></div>'


def safe_page_link(path: str, label: str) -> None:
    try:
        st.page_link(path, label=label)
    except Exception:
        st.caption(f"{label} — open from the sidebar navigation.")


def inject():
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(glow_orbs(), unsafe_allow_html=True)
