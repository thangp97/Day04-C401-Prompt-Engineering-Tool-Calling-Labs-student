from __future__ import annotations

import datetime
import json
import uuid
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent

# Load env before any other import
from env_loader import load_lab_env
load_lab_env(ROOT)

from providers import make_provider  # noqa: E402
from tools import TOOL_FUNCTIONS, load_tool_declarations, to_openai_tools  # noqa: E402
from agent import ResearchAgent  # noqa: E402

ARTIFACTS = ROOT / "artifacts"
SYSTEM_PROMPT_FILE = ARTIFACTS / "system_prompt.md"
TOOLS_FILE = ARTIFACTS / "tools.yaml"
LOGS_DIR = ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)

PROVIDERS = ["openrouter", "openai", "anthropic", "gemini"]
VERSIONS = ["v0", "v1", "v2", "v3", "v3new", "v4", "v5", "v6"]

_TOOL_GROUPS = {
    "Core":  ["clarify", "timeline", "social_search", "lookup", "fetch", "format"],
    "Bonus": ["send", "policy", "papers", "paper_text"],
    "New":   ["reddit_search", "github_trending", "translate", "summarize"],
}

_GROUP_COLORS = {
    "Core":  {"accent": "#6366f1", "bg": "rgba(99,102,241,0.12)",  "label": "#818cf8"},
    "Bonus": {"accent": "#f59e0b", "bg": "rgba(245,158,11,0.12)", "label": "#fbbf24"},
    "New":   {"accent": "#10b981", "bg": "rgba(16,185,129,0.12)", "label": "#34d399"},
}

SAMPLE_PROMPTS = [
    ("🌐", "Tin tức AI hôm nay có gì nổi bật?"),
    ("🐦", "Tweet mới nhất của Sam Altman là gì?"),
    ("🔴", "Mọi người đang bàn gì về ChatGPT trên Reddit?"),
    ("💻", "Tìm repo GitHub trending về AI agents viết bằng Python tuần này"),
    ("📄", "Tìm paper mới nhất về LLM agents trên arXiv"),
    ("🌍", "Dịch câu này sang tiếng Nhật: AI agents are the future"),
]


def load_agent(provider_name: str) -> ResearchAgent:
    system_prompt = SYSTEM_PROMPT_FILE.read_text(encoding="utf-8")
    declarations = load_tool_declarations(TOOLS_FILE)
    tools = to_openai_tools(declarations)
    provider = make_provider(provider_name)
    return ResearchAgent(provider, system_prompt=system_prompt, tools=tools)


def _save_log() -> None:
    log = {
        "session_id": st.session_state.session_id,
        "session_start": st.session_state.session_start,
        "last_updated": datetime.datetime.utcnow().isoformat() + "Z",
        "turn_count": len([m for m in st.session_state.messages if m["role"] == "user"]),
        "messages": [],
    }
    for m in st.session_state.messages:
        if m["role"] == "user":
            log["messages"].append({"role": "user", "content": m["content"]})
        else:
            tool_calls = []
            for tc in m.get("tool_calls", []):
                name = tc.name if hasattr(tc, "name") else tc.get("name", "")
                args = tc.args if hasattr(tc, "args") else tc.get("args", {})
                tool_calls.append({"name": name, "args": args})
            log["messages"].append({
                "role": "assistant",
                "tool_calls": tool_calls,
                "text": m.get("text", ""),
            })
    log_path = LOGS_DIR / f"chat_{st.session_state.session_id}.json"
    log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")


def render_tool_call(call, result: dict) -> None:
    tool_name = call.name if hasattr(call, "name") else call.get("name", "unknown")
    with st.expander(f"⚡ {tool_name}", expanded=False):
        st.markdown("**Args:**")
        args = call.args if hasattr(call, "args") else call.get("args", {})
        st.code(json.dumps(args, ensure_ascii=False, indent=2), language="json")
        st.markdown("**Result:**")
        items = result.get("result", result).get("items", [])
        if items:
            for item in items:
                title = item.get("title", "")
                url = item.get("url", "")
                summary = item.get("summary", "")[:200]
                source = item.get("source", "")
                st.markdown(f"- **{title}** ({source}){' — ' + summary if summary else ''}")
                if url:
                    st.markdown(f"  [{url}]({url})")
        else:
            st.code(json.dumps(result.get("result", result), ensure_ascii=False, indent=2)[:500], language="json")


def main() -> None:
    st.set_page_config(
        page_title="Research Agent",
        page_icon="🔍",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={"Get help": None, "Report a bug": None, "About": None},
    )

    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    /* ── Reset & base ─────────────────────────────────────────── */
    html, body, [class*="css"] {
        font-family: 'Space Grotesk', -apple-system, sans-serif !important;
    }
    code, pre, .stCode * {
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* ── Hide Streamlit chrome (NOT header — sidebar toggle lives there) */
    #MainMenu { visibility: hidden !important; }
    footer { visibility: hidden !important; }
    .stDeployButton { display: none !important; }
    [data-testid="stDecoration"] { display: none !important; }
    [data-testid="stStatusWidget"] { display: none !important; }
    /* Make header transparent so toggle button stays clickable */
    [data-testid="stHeader"] {
        background: transparent !important;
        border-bottom: none !important;
    }

    /* ── App background ───────────────────────────────────────── */
    .stApp {
        background: #06080f;
        background-image:
            radial-gradient(ellipse 80% 50% at 20% -10%, rgba(99,102,241,0.15) 0%, transparent 60%),
            radial-gradient(ellipse 60% 40% at 80% 110%, rgba(6,182,212,0.10) 0%, transparent 60%);
        background-attachment: fixed;
    }

    /* ── Main content ─────────────────────────────────────────── */
    .main .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 4rem !important;
        max-width: 920px !important;
    }

    /* ── Sidebar ──────────────────────────────────────────────── */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0b0f1e 0%, #080c19 100%) !important;
        border-right: 1px solid rgba(99,102,241,0.2) !important;
    }
    [data-testid="stSidebar"]::before {
        content: '';
        display: block;
        height: 3px;
        background: linear-gradient(90deg, #6366f1, #06b6d4, #8b5cf6);
    }
    [data-testid="stSidebar"] .stMarkdown p {
        font-size: 0.82rem;
        color: #64748b;
        line-height: 1.5;
    }
    [data-testid="stSidebar"] .stSelectbox label {
        color: #94a3b8 !important;
        font-size: 0.75rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.08em !important;
        text-transform: uppercase !important;
    }
    [data-testid="stSidebar"] .stSelectbox > div > div {
        background: rgba(255,255,255,0.03) !important;
        border: 1px solid rgba(99,102,241,0.25) !important;
        border-radius: 8px !important;
        color: #e2e8f0 !important;
    }

    /* ── Sidebar clear button ─────────────────────────────────── */
    [data-testid="stSidebar"] .stButton > button {
        background: rgba(239,68,68,0.08) !important;
        border: 1px solid rgba(239,68,68,0.25) !important;
        color: #f87171 !important;
        border-radius: 8px !important;
        font-size: 0.82rem !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background: rgba(239,68,68,0.18) !important;
        border-color: rgba(239,68,68,0.5) !important;
        box-shadow: 0 4px 12px rgba(239,68,68,0.2) !important;
    }

    /* ── Hero header ──────────────────────────────────────────── */
    .hero-wrap { padding: 1.5rem 0 1rem 0; }
    .hero-title {
        font-size: 2.6rem;
        font-weight: 700;
        line-height: 1.1;
        letter-spacing: -0.03em;
        margin-bottom: 0.5rem;
    }
    @keyframes gradient-pan {
        0%   { background-position: 0% 50%; }
        50%  { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    .gradient-text {
        background: linear-gradient(135deg, #818cf8 0%, #06b6d4 35%, #a78bfa 65%, #818cf8 100%);
        background-size: 300% 300%;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        animation: gradient-pan 6s ease infinite;
    }
    .hero-sub {
        font-size: 0.82rem;
        color: #3d4f6a;
        letter-spacing: 0.1em;
        margin-bottom: 1rem;
        font-weight: 500;
    }
    .hero-pills { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 0.5rem; }
    .hero-pill {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        padding: 3px 12px;
        border-radius: 999px;
        font-size: 0.74rem;
        font-weight: 600;
        letter-spacing: 0.04em;
    }
    .pill-indigo { background: rgba(99,102,241,0.12); border: 1px solid rgba(99,102,241,0.3); color: #818cf8; }
    .pill-cyan   { background: rgba(6,182,212,0.12);  border: 1px solid rgba(6,182,212,0.3);  color: #22d3ee; }
    .pill-violet { background: rgba(139,92,246,0.12); border: 1px solid rgba(139,92,246,0.3); color: #a78bfa; }
    .hero-divider {
        height: 1px;
        background: linear-gradient(90deg, rgba(99,102,241,0.4), rgba(6,182,212,0.2), transparent);
        margin-top: 1.2rem;
    }

    /* ── Tool group section headers ───────────────────────────── */
    .tool-section { margin: 10px 0 6px 0; }
    .tool-section-label {
        font-size: 0.63rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        margin-bottom: 6px;
        padding-left: 2px;
    }
    .tool-badges-row { display: flex; flex-wrap: wrap; gap: 4px; }
    .tool-badge {
        display: inline-block;
        padding: 3px 9px;
        border-radius: 5px;
        font-size: 0.7rem;
        font-family: 'JetBrains Mono', monospace;
        font-weight: 500;
        letter-spacing: 0.02em;
    }

    /* ── Sample prompt buttons ────────────────────────────────── */
    .prompt-grid-label {
        font-size: 0.78rem;
        font-weight: 600;
        color: #475569;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        margin-bottom: 12px;
        margin-top: 8px;
    }
    div[data-testid="stHorizontalBlock"] .stButton > button {
        background: rgba(255,255,255,0.02) !important;
        border: 1px solid rgba(99,102,241,0.2) !important;
        border-radius: 10px !important;
        color: #94a3b8 !important;
        font-size: 0.83rem !important;
        font-weight: 400 !important;
        text-align: left !important;
        padding: 0.6rem 0.85rem !important;
        line-height: 1.4 !important;
        min-height: 56px !important;
        transition: all 0.18s ease !important;
        white-space: normal !important;
    }
    div[data-testid="stHorizontalBlock"] .stButton > button:hover {
        background: rgba(99,102,241,0.08) !important;
        border-color: rgba(99,102,241,0.45) !important;
        color: #c7d2fe !important;
        box-shadow: 0 0 16px rgba(99,102,241,0.12) !important;
        transform: translateY(-1px) !important;
    }

    /* ── Chat messages ────────────────────────────────────────── */
    [data-testid="stChatMessage"] {
        border-radius: 12px !important;
        margin-bottom: 4px !important;
    }

    /* ── Tool call expanders ──────────────────────────────────── */
    [data-testid="stExpander"] {
        background: rgba(13,17,35,0.8) !important;
        border: 1px solid rgba(99,102,241,0.2) !important;
        border-left: 3px solid #6366f1 !important;
        border-radius: 8px !important;
        margin-bottom: 6px !important;
        backdrop-filter: blur(8px) !important;
    }
    [data-testid="stExpander"]:hover {
        border-color: rgba(99,102,241,0.4) !important;
        border-left-color: #818cf8 !important;
        box-shadow: 0 0 20px rgba(99,102,241,0.08) !important;
    }
    [data-testid="stExpander"] summary {
        font-size: 0.85rem !important;
        font-weight: 600 !important;
        color: #a5b4fc !important;
        letter-spacing: 0.02em !important;
    }
    [data-testid="stExpander"] summary svg { fill: #6366f1 !important; }

    /* ── Code blocks ──────────────────────────────────────────── */
    .stCode { border-radius: 8px !important; border: 1px solid rgba(255,255,255,0.06) !important; }
    .stCode > div { background: #0d1117 !important; }

    /* ── Chat input ───────────────────────────────────────────── */
    [data-testid="stChatInput"] {
        border-top: 1px solid rgba(99,102,241,0.15) !important;
        background: rgba(6,8,15,0.95) !important;
        backdrop-filter: blur(12px) !important;
    }
    [data-testid="stChatInput"] textarea {
        background: rgba(255,255,255,0.03) !important;
        border: 1px solid rgba(99,102,241,0.25) !important;
        border-radius: 10px !important;
        color: #e2e8f0 !important;
        font-size: 0.9rem !important;
        font-family: 'Space Grotesk', sans-serif !important;
        transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
    }
    [data-testid="stChatInput"] textarea:focus {
        border-color: rgba(99,102,241,0.6) !important;
        box-shadow: 0 0 0 3px rgba(99,102,241,0.12), 0 0 20px rgba(99,102,241,0.1) !important;
    }
    [data-testid="stChatInput"] textarea::placeholder { color: #2d3a4f !important; }

    /* ── Spinner ──────────────────────────────────────────────── */
    .stSpinner > div { border-top-color: #6366f1 !important; }

    /* ── Divider ──────────────────────────────────────────────── */
    hr { border-color: rgba(255,255,255,0.05) !important; margin: 0.75rem 0 !important; }

    /* ── Scrollbar ────────────────────────────────────────────── */
    ::-webkit-scrollbar { width: 5px; height: 5px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: rgba(99,102,241,0.3); border-radius: 99px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(99,102,241,0.5); }

    /* ── Scan line ────────────────────────────────────────────── */
    @keyframes scanline {
        0%   { top: -2%; }
        100% { top: 102%; }
    }
    .ra-scanline {
        position: fixed;
        left: 0; width: 100%; height: 2px;
        background: linear-gradient(90deg, transparent 0%, rgba(99,102,241,0.18) 30%, rgba(6,182,212,0.12) 70%, transparent 100%);
        animation: scanline 10s linear infinite;
        pointer-events: none;
        z-index: 2;
    }

    /* ── Pikachu mascot ──────────────────────────────────────── */
    @keyframes pika-float {
        0%, 100% { transform: translateY(0px); }
        50%       { transform: translateY(-13px); }
    }
    @keyframes cheek-pulse {
        0%, 100% { opacity: 0.75; }
        50%       { opacity: 1; filter: drop-shadow(0 0 5px #EF4444); }
    }
    @keyframes wing-l {
        0%, 100% { transform: rotate(0deg) scaleY(1); }
        50%       { transform: rotate(-22deg) scaleY(0.55); }
    }
    @keyframes wing-r {
        0%, 100% { transform: rotate(0deg) scaleY(1); }
        50%       { transform: rotate(22deg) scaleY(0.55); }
    }
    .ra-mascot {
        position: fixed;
        bottom: 88px; right: 18px;
        animation: pika-float 2s ease-in-out infinite;
        z-index: 1000;
        cursor: pointer;
        filter: drop-shadow(0 0 10px rgba(255,203,5,0.45));
        transition: filter 0.25s ease;
    }
    .ra-mascot:hover {
        filter: drop-shadow(0 0 28px rgba(255,203,5,0.9));
        animation-play-state: paused;
    }
    .pika-cheek { animation: cheek-pulse 1.4s ease-in-out infinite; }
    .pika-wl {
        transform-box: fill-box;
        transform-origin: right center;
        animation: wing-l 0.52s ease-in-out infinite;
    }
    .pika-wr {
        transform-box: fill-box;
        transform-origin: left center;
        animation: wing-r 0.52s ease-in-out infinite;
    }

    /* ── Rainbow textarea text ────────────────────────────────── */
    @keyframes rainbow-type {
        0%   { -webkit-text-fill-color: #ff6b6b; }
        14%  { -webkit-text-fill-color: #ffa94d; }
        28%  { -webkit-text-fill-color: #ffe066; }
        42%  { -webkit-text-fill-color: #69db7c; }
        57%  { -webkit-text-fill-color: #4dabf7; }
        71%  { -webkit-text-fill-color: #9775fa; }
        85%  { -webkit-text-fill-color: #f783ac; }
        100% { -webkit-text-fill-color: #ff6b6b; }
    }
    [data-testid="stChatInput"] textarea:not(:placeholder-shown) {
        animation: rainbow-type 1.8s linear infinite !important;
        caret-color: white !important;
    }

    /* ── Title flicker ────────────────────────────────────────── */
    @keyframes flicker {
        0%, 95%, 100% { opacity: 1; }
        96%            { opacity: 0.85; }
        97%            { opacity: 1; }
        98%            { opacity: 0.9; }
    }
    .gradient-text { animation: gradient-pan 6s ease infinite, flicker 8s ease-in-out infinite; }

    /* ── Pill float ───────────────────────────────────────────── */
    @keyframes pill-in {
        from { opacity: 0; transform: translateY(8px); }
        to   { opacity: 1; transform: translateY(0); }
    }
    .hero-pill:nth-child(1) { animation: pill-in 0.5s ease 0.2s both; }
    .hero-pill:nth-child(2) { animation: pill-in 0.5s ease 0.4s both; }
    .hero-pill:nth-child(3) { animation: pill-in 0.5s ease 0.6s both; }
    </style>
    """, unsafe_allow_html=True)

    # ── Particle network + cursor trail + mascot + scanline ──────────────────
    st.markdown("""
    <canvas id="ra-canvas" style="position:fixed;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:0;opacity:0.55;"></canvas>
    <div class="ra-scanline"></div>
    <div id="ra-trail" style="position:fixed;top:0;left:0;pointer-events:none;z-index:9998;"></div>

    <div class="ra-mascot" title="Pika pika!">
      <svg width="82" height="100" viewBox="0 0 82 100" fill="none" xmlns="http://www.w3.org/2000/svg">
        <!-- Left wings (behind everything) -->
        <g class="pika-wl">
          <ellipse cx="14" cy="52" rx="17" ry="11" fill="rgba(196,181,253,0.58)" stroke="#a78bfa" stroke-width="1.2" transform="rotate(-28 14 52)"/>
          <ellipse cx="11" cy="64" rx="13" ry="8"  fill="rgba(196,181,253,0.40)" stroke="#c084fc" stroke-width="1"   transform="rotate(-12 11 64)"/>
        </g>
        <!-- Right wings -->
        <g class="pika-wr">
          <ellipse cx="68" cy="52" rx="17" ry="11" fill="rgba(196,181,253,0.58)" stroke="#a78bfa" stroke-width="1.2" transform="rotate(28 68 52)"/>
          <ellipse cx="71" cy="64" rx="13" ry="8"  fill="rgba(196,181,253,0.40)" stroke="#c084fc" stroke-width="1"   transform="rotate(12 71 64)"/>
        </g>
        <!-- Body -->
        <ellipse cx="41" cy="78" rx="20" ry="18" fill="#FFCB05"/>
        <!-- Back stripes -->
        <path d="M32 69 Q36 63 41 69 Q46 63 50 69" stroke="#92400e" stroke-width="2.5" fill="none" stroke-linecap="round"/>
        <!-- Tail lightning bolt -->
        <path d="M55 84 L63 90 L57 87 L64 94" stroke="#FFCB05" stroke-width="4" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
        <!-- Head -->
        <ellipse cx="41" cy="44" rx="25" ry="23" fill="#FFCB05"/>
        <!-- Left ear (yellow body + black tip) -->
        <polygon points="20,27 14,4 30,22" fill="#FFCB05"/>
        <polygon points="21,26 17,7 29,22" fill="#1a1a2e"/>
        <!-- Right ear -->
        <polygon points="62,27 68,4 52,22" fill="#FFCB05"/>
        <polygon points="61,26 65,7 53,22" fill="#1a1a2e"/>
        <!-- Left eye -->
        <circle cx="29" cy="40" r="7"   fill="#1a1a2e"/>
        <circle cx="31" cy="37" r="3"   fill="white"/>
        <circle cx="33" cy="41" r="1.2" fill="white" opacity="0.7"/>
        <!-- Right eye -->
        <circle cx="53" cy="40" r="7"   fill="#1a1a2e"/>
        <circle cx="55" cy="37" r="3"   fill="white"/>
        <circle cx="57" cy="41" r="1.2" fill="white" opacity="0.7"/>
        <!-- Nose -->
        <ellipse cx="41" cy="47" rx="2.5" ry="2" fill="#1a1a2e"/>
        <!-- Smile -->
        <path d="M32 52 Q41 61 50 52" stroke="#1a1a2e" stroke-width="2.2" fill="none" stroke-linecap="round"/>
        <!-- Red cheeks -->
        <ellipse class="pika-cheek" cx="15" cy="49" rx="9" ry="7" fill="#EF4444" opacity="0.85"/>
        <ellipse class="pika-cheek" cx="67" cy="49" rx="9" ry="7" fill="#EF4444" opacity="0.85"/>
        <circle cx="14" cy="47" r="1.8" fill="white" opacity="0.45"/>
        <circle cx="66" cy="47" r="1.8" fill="white" opacity="0.45"/>
      </svg>
    </div>

    <script>
    (function() {
        var canvas = document.getElementById('ra-canvas');
        if (!canvas || canvas.dataset.init === '1') return;
        canvas.dataset.init = '1';

        var ctx = canvas.getContext('2d');
        var W, H;
        function resize() { W = canvas.width = window.innerWidth; H = canvas.height = window.innerHeight; }
        resize();
        window.addEventListener('resize', resize);

        var COLORS = ['99,102,241','6,182,212','139,92,246','59,130,246','168,85,247'];
        var N = 65;
        var pts = [];
        for (var i = 0; i < N; i++) {
            pts.push({
                x: Math.random()*1600, y: Math.random()*900,
                vx: (Math.random()-0.5)*0.32, vy: (Math.random()-0.5)*0.32,
                r: Math.random()*1.6+0.6,
                a: Math.random()*0.45+0.12,
                c: COLORS[Math.floor(Math.random()*COLORS.length)]
            });
        }

        var mx = -9999, my = -9999;
        document.addEventListener('mousemove', function(e){ mx = e.clientX; my = e.clientY; });

        function frame() {
            ctx.clearRect(0,0,W,H);
            for (var i = 0; i < pts.length; i++) {
                var p = pts[i];
                var dx = p.x-mx, dy = p.y-my, d = Math.sqrt(dx*dx+dy*dy);
                if (d < 120) { p.vx += dx/d*0.018; p.vy += dy/d*0.018; }
                p.vx *= 0.998; p.vy *= 0.998;
                p.x += p.vx; p.y += p.vy;
                if (p.x<0||p.x>W) p.vx*=-1;
                if (p.y<0||p.y>H) p.vy*=-1;
                ctx.beginPath();
                ctx.arc(p.x,p.y,p.r,0,Math.PI*2);
                ctx.fillStyle='rgba('+p.c+','+p.a+')';
                ctx.fill();
            }
            for (var i = 0; i < pts.length-1; i++) {
                for (var j = i+1; j < pts.length; j++) {
                    var dx=pts[i].x-pts[j].x, dy=pts[i].y-pts[j].y;
                    var dist=Math.sqrt(dx*dx+dy*dy);
                    if (dist<115) {
                        ctx.beginPath();
                        ctx.moveTo(pts[i].x,pts[i].y);
                        ctx.lineTo(pts[j].x,pts[j].y);
                        ctx.strokeStyle='rgba(99,102,241,'+(1-dist/115)*0.11+')';
                        ctx.lineWidth=0.5; ctx.stroke();
                    }
                }
            }
            if (mx>0) {
                for (var i=0;i<pts.length;i++) {
                    var dx=pts[i].x-mx, dy=pts[i].y-my;
                    var dist=Math.sqrt(dx*dx+dy*dy);
                    if (dist<160) {
                        ctx.beginPath(); ctx.moveTo(pts[i].x,pts[i].y); ctx.lineTo(mx,my);
                        ctx.strokeStyle='rgba(6,182,212,'+(1-dist/160)*0.22+')';
                        ctx.lineWidth=0.6; ctx.stroke();
                    }
                }
            }
            requestAnimationFrame(frame);
        }
        frame();

        /* ── FAAHHHH sound on keypress ── */
        var _actx = null;
        var _lastFaah = 0;
        function playFaah() {
            var now = Date.now();
            if (now - _lastFaah < 75) return;
            _lastFaah = now;
            try {
                if (!_actx) _actx = new (window.AudioContext || window.webkitAudioContext)();
                if (_actx.state === 'suspended') _actx.resume();
                var t = _actx.currentTime;
                var osc  = _actx.createOscillator();
                var gain = _actx.createGain();
                var filt = _actx.createBiquadFilter();
                osc.type = 'sawtooth';
                osc.frequency.setValueAtTime(320, t);
                osc.frequency.exponentialRampToValueAtTime(55, t + 0.22);
                filt.type = 'bandpass';
                filt.frequency.setValueAtTime(900, t);
                filt.frequency.exponentialRampToValueAtTime(280, t + 0.22);
                filt.Q.value = 5;
                gain.gain.setValueAtTime(0.001, t);
                gain.gain.linearRampToValueAtTime(0.22, t + 0.015);
                gain.gain.exponentialRampToValueAtTime(0.001, t + 0.25);
                osc.connect(filt); filt.connect(gain); gain.connect(_actx.destination);
                osc.start(t); osc.stop(t + 0.28);
            } catch(e) {}
        }
        function attachFaah(el) {
            if (!el || el.dataset.faah === '1') return;
            el.dataset.faah = '1';
            el.addEventListener('keydown', function(e) {
                if (e.key.length === 1 || e.key === 'Backspace') playFaah();
            });
        }
        var _faahObs = new MutationObserver(function() {
            attachFaah(document.querySelector('[data-testid="stChatInput"] textarea'));
        });
        _faahObs.observe(document.body, {childList:true, subtree:true});
        attachFaah(document.querySelector('[data-testid="stChatInput"] textarea'));

        /* ── Cursor trail ── */
        var trail = document.getElementById('ra-trail');
        var TLEN = 14;
        var tdots = [];
        for (var i=0;i<TLEN;i++) {
            var d=document.createElement('div');
            var sz=Math.max(2, 7-i*0.4);
            d.style.cssText='position:fixed;width:'+sz+'px;height:'+sz+'px;border-radius:50%;pointer-events:none;transform:translate(-50%,-50%);transition:opacity 0.08s;';
            trail.appendChild(d);
            tdots.push(d);
        }
        var tpos=Array(TLEN).fill().map(function(){return{x:0,y:0};});
        document.addEventListener('mousemove',function(e){
            tpos.unshift({x:e.clientX,y:e.clientY});
            tpos.pop();
            tdots.forEach(function(dot,i){
                dot.style.left=tpos[i].x+'px';
                dot.style.top=tpos[i].y+'px';
                var t=1-i/TLEN;
                dot.style.opacity=t*0.75;
                var h=i<TLEN/2?'99,102,241':'6,182,212';
                dot.style.background='rgba('+h+','+t+')';
                dot.style.boxShadow='0 0 '+(4*t)+'px rgba(99,102,241,'+(t*0.5)+')';
            });
        });
    })();
    </script>
    """, unsafe_allow_html=True)

    # ── Hero header ──────────────────────────────────────────────────────────
    st.markdown("""
    <div class="hero-wrap">
        <div class="hero-title"><span class="gradient-text">Research Agent</span></div>
        <div class="hero-sub">WEB &nbsp;·&nbsp; TWITTER &nbsp;·&nbsp; REDDIT &nbsp;·&nbsp; GITHUB &nbsp;·&nbsp; ARXIV &nbsp;·&nbsp; TRANSLATE &nbsp;·&nbsp; TELEGRAM</div>
        <div class="hero-pills">
            <span class="hero-pill pill-indigo">⚡ 14 tools</span>
            <span class="hero-pill pill-cyan">🤖 GPT-4o-mini</span>
            <span class="hero-pill pill-violet">🔄 Multi-turn</span>
        </div>
        <div class="hero-divider"></div>
    </div>
    """, unsafe_allow_html=True)

    # ── Sidebar ──────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("""
        <div style="padding:1rem 0 0.5rem 0;">
            <div style="font-size:1.05rem;font-weight:700;color:#e2e8f0;letter-spacing:-0.01em;">⚙️ &nbsp;Config</div>
        </div>
        """, unsafe_allow_html=True)

        provider_name = st.selectbox("PROVIDER", PROVIDERS, index=0, label_visibility="visible")
        st.markdown('<div style="font-size:0.73rem;color:#2d3a4f;margin-top:-8px;padding-left:2px;">openai/gpt-4o-mini via OpenRouter</div>', unsafe_allow_html=True)

        st.divider()

        st.markdown('<div style="font-size:0.7rem;font-weight:700;color:#64748b;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:4px;">Tools Available</div>', unsafe_allow_html=True)

        for group_label, names in _TOOL_GROUPS.items():
            active = [n for n in names if n in TOOL_FUNCTIONS]
            if not active:
                continue
            c = _GROUP_COLORS[group_label]
            badges_html = "".join(
                f'<span class="tool-badge" style="background:{c["bg"]};border:1px solid {c["accent"]}40;color:{c["accent"]};">{n}</span>'
                for n in active
            )
            st.markdown(f"""
            <div class="tool-section">
                <div class="tool-section-label" style="color:{c['label']};">{group_label}</div>
                <div class="tool-badges-row">{badges_html}</div>
            </div>
            """, unsafe_allow_html=True)

        st.divider()

        # ── Log viewer ───────────────────────────────────────────
        log_files = sorted(LOGS_DIR.glob("chat_*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
        st.markdown(f'<div style="font-size:0.7rem;font-weight:700;color:#64748b;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px;">Chat Logs ({len(log_files)})</div>', unsafe_allow_html=True)
        if log_files:
            with st.expander(f"📋 Xem {min(len(log_files), 5)} session gần nhất", expanded=False):
                for lf in log_files[:5]:
                    try:
                        data = json.loads(lf.read_text(encoding="utf-8"))
                        ts = data.get("last_updated", "")[:16].replace("T", " ")
                        turns = data.get("turn_count", 0)
                        sid = data.get("session_id", lf.stem)[:8]
                        st.markdown(f'<div style="font-size:0.75rem;color:#475569;padding:3px 0;border-bottom:1px solid rgba(255,255,255,0.04);">🔹 <code style="color:#6366f1;">{sid}</code> — {turns} turn{"s" if turns!=1 else ""} &nbsp;<span style="color:#334155;">{ts}</span></div>', unsafe_allow_html=True)
                    except Exception:
                        pass
        else:
            st.markdown('<div style="font-size:0.75rem;color:#2d3a4f;">Chưa có log nào.</div>', unsafe_allow_html=True)

        st.divider()

        if st.button("🗑️ Xoá lịch sử chat", use_container_width=True, type="secondary"):
            st.session_state.messages = []
            st.session_state.history = []
            st.rerun()

    # ── Session state ─────────────────────────────────────────────────────────
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "history" not in st.session_state:
        st.session_state.history = []
    if "session_id" not in st.session_state:
        st.session_state.session_id = uuid.uuid4().hex[:12]
        st.session_state.session_start = datetime.datetime.utcnow().isoformat() + "Z"

    # ── Sample prompts (only when chat is empty) ──────────────────────────────
    if not st.session_state.messages:
        st.markdown('<div class="prompt-grid-label">✦ &nbsp;Thử ngay</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        cols = [col1, col2]
        for i, (emoji, prompt) in enumerate(SAMPLE_PROMPTS):
            with cols[i % 2]:
                if st.button(f"{emoji}  {prompt}", key=f"preset_{i}", use_container_width=True):
                    st.session_state.preset_input = prompt
                    st.rerun()

    # ── Render existing messages ──────────────────────────────────────────────
    for msg in st.session_state.messages:
        role = msg["role"]
        with st.chat_message(role):
            if role == "assistant":
                if msg.get("tool_calls"):
                    for tc, tr in zip(msg["tool_calls"], msg["tool_results"]):
                        render_tool_call(tc, tr)
                if msg.get("text"):
                    st.markdown(msg["text"])
            else:
                st.markdown(msg["content"])

    # ── Chat input ────────────────────────────────────────────────────────────
    preset = st.session_state.pop("preset_input", None)
    user_input = st.chat_input("Hỏi gì đó... vd: Tin tức AI hôm nay có gì nổi bật?") or preset

    if user_input:
        # Display user message
        with st.chat_message("user"):
            st.markdown(user_input)
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.session_state.history.append({"role": "user", "content": user_input})

        # Run agent
        with st.chat_message("assistant"):
            with st.spinner("Đang xử lý..."):
                try:
                    agent = load_agent(provider_name)
                    run = agent.run(st.session_state.history)
                except Exception as exc:
                    st.error(f"Lỗi: {exc}")
                    st.stop()

            # Show tool calls
            tool_calls_data = []
            tool_results_data = []
            for tc, tr in zip(run.tool_calls, run.tool_results):
                render_tool_call(tc, tr)
                tool_calls_data.append({"name": tc.name, "args": tc.args})
                tool_results_data.append(tr)

            # Show text response
            if run.text:
                st.markdown(run.text)

        # Save to session
        st.session_state.messages.append({
            "role": "assistant",
            "tool_calls": run.tool_calls,
            "tool_results": run.tool_results,
            "text": run.text,
        })

        # Build assistant history message
        assistant_content = run.text or ""
        st.session_state.history.append({"role": "assistant", "content": assistant_content})

        # Persist chat log
        _save_log()


if __name__ == "__main__":
    main()
