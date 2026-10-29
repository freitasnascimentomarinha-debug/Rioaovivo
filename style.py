"""CSS global (glassmorphism / aurora) e componentes HTML reutilizáveis."""
import streamlit as st

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
html, body, [class*="css"], .stApp { font-family: 'Inter', sans-serif; }
.stApp {
  background:
    radial-gradient(900px 500px at 8% -10%, rgba(56,189,248,.20), transparent 60%),
    radial-gradient(800px 500px at 95% 0%, rgba(167,139,250,.18), transparent 60%),
    radial-gradient(700px 600px at 50% 110%, rgba(52,211,153,.10), transparent 60%),
    #070b17;
}
#MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; height: 0; }
.block-container { padding-top: 1.6rem; max-width: 1280px; }
section[data-testid="stSidebar"] { background: rgba(10,15,30,.85); border-right: 1px solid rgba(148,163,184,.12); }

.glass {
  background: linear-gradient(145deg, rgba(30,41,67,.55), rgba(15,23,42,.55));
  border: 1px solid rgba(148,163,184,.16);
  border-radius: 22px; padding: 18px 20px;
  backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
  box-shadow: 0 10px 40px rgba(0,0,0,.35), inset 0 1px 0 rgba(255,255,255,.05);
  transition: transform .25s ease, border-color .25s ease;
}
.glass:hover { transform: translateY(-3px); border-color: rgba(56,189,248,.45); }

.hero { display:flex; flex-wrap:wrap; gap:24px; align-items:center; justify-content:space-between;
  padding: 28px 32px; border-radius: 28px; position:relative; overflow:hidden;
  background: linear-gradient(120deg, rgba(14,165,233,.28), rgba(99,102,241,.25) 55%, rgba(168,85,247,.22));
  border: 1px solid rgba(255,255,255,.14); box-shadow: 0 20px 60px rgba(14,165,233,.15); }
.hero::after { content:""; position:absolute; width:380px; height:380px; right:-120px; top:-160px;
  background: radial-gradient(circle, rgba(255,255,255,.18), transparent 65%); }
.hero .local { font-size:.95rem; letter-spacing:.14em; text-transform:uppercase; opacity:.8; font-weight:600; }
.hero .temp { font-size: clamp(3.6rem, 9vw, 6.2rem); font-weight:800; line-height:1; letter-spacing:-.04em;
  background: linear-gradient(180deg,#fff,#bae6fd); -webkit-background-clip:text; background-clip:text; color:transparent; }
.hero .cond { font-size:1.25rem; font-weight:500; opacity:.95; margin-top:6px; }
.hero .emoji { font-size: clamp(4.5rem, 11vw, 7.5rem); filter: drop-shadow(0 10px 30px rgba(0,0,0,.4)); animation: float 5s ease-in-out infinite; }
@keyframes float { 0%,100%{ transform:translateY(0) } 50%{ transform:translateY(-10px) } }
.live { display:inline-flex; align-items:center; gap:8px; font-size:.78rem; font-weight:600; letter-spacing:.1em;
  padding:5px 12px; border-radius:999px; background:rgba(16,185,129,.16); color:#6ee7b7; border:1px solid rgba(16,185,129,.35); }
.live i { width:8px; height:8px; border-radius:50%; background:#34d399; box-shadow:0 0 0 0 rgba(52,211,153,.7); animation:pulse 1.8s infinite; }
@keyframes pulse { 70%{ box-shadow:0 0 0 10px rgba(52,211,153,0) } 100%{ box-shadow:0 0 0 0 rgba(52,211,153,0) } }

.kpi { min-height: 150px; }
.kpi .label { font-size:.74rem; letter-spacing:.12em; text-transform:uppercase; opacity:.6; font-weight:600; display:flex; gap:8px; align-items:center; }
.kpi .value { font-size:2rem; font-weight:700; margin-top:6px; letter-spacing:-.02em; }
.kpi .value small { font-size:.9rem; font-weight:500; opacity:.65; margin-left:4px; }
.kpi .sub { font-size:.85rem; opacity:.7; margin-top:2px; }
.bar { height:6px; border-radius:99px; background:rgba(148,163,184,.18); margin-top:12px; overflow:hidden; }
.bar > span { display:block; height:100%; border-radius:99px; background:linear-gradient(90deg,#38bdf8,#818cf8); }
.arrow { display:inline-block; transition: transform .6s; color:#38bdf8; }

.section-title { font-size:1.15rem; font-weight:700; margin: 6px 0 12px; display:flex; align-items:center; gap:10px; }
.section-title::after { content:""; flex:1; height:1px; background:linear-gradient(90deg, rgba(148,163,184,.3), transparent); }

.day { text-align:center; padding:14px 8px; }
.day .d { font-weight:600; opacity:.75; font-size:.85rem; text-transform:uppercase; letter-spacing:.08em; }
.day .e { font-size:2.1rem; margin:6px 0; }
.day .t { font-weight:700; } .day .t span { opacity:.5; font-weight:500; }
.day .r { font-size:.78rem; color:#7dd3fc; margin-top:4px; }

.alert { border-left:5px solid var(--c); background:linear-gradient(90deg, color-mix(in srgb, var(--c) 18%, transparent), rgba(15,23,42,.5));
  border-radius:16px; padding:16px 20px; margin-bottom:12px; border-top:1px solid rgba(148,163,184,.12); border-right:1px solid rgba(148,163,184,.12); border-bottom:1px solid rgba(148,163,184,.12); }
.alert .h { font-weight:700; font-size:1.05rem; } .alert .m { opacity:.75; font-size:.85rem; margin-top:4px; }
.alert .badge { display:inline-block; padding:2px 10px; border-radius:99px; background:var(--c); color:#0b1020; font-weight:700; font-size:.72rem; margin-right:8px; }
.ok { --c:#34d399; }

.tide-row { display:flex; justify-content:space-between; align-items:center; padding:10px 0; border-bottom:1px dashed rgba(148,163,184,.18); }
.tide-row:last-child { border:none; }
.pill { padding:3px 10px; border-radius:99px; font-size:.75rem; font-weight:600; }
.pill.hi { background:rgba(56,189,248,.18); color:#7dd3fc; } .pill.lo { background:rgba(251,191,36,.16); color:#fcd34d; }

.stTabs [data-baseweb="tab-list"] { gap:6px; background:rgba(15,23,42,.6); padding:6px; border-radius:16px; border:1px solid rgba(148,163,184,.14); flex-wrap:wrap; }
.stTabs [data-baseweb="tab"] { border-radius:12px; padding:8px 16px; height:auto; font-weight:600; }
.stTabs [aria-selected="true"] { background:linear-gradient(135deg,#0ea5e9,#6366f1); color:#fff !important; }
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display:none; }
.footer { text-align:center; opacity:.45; font-size:.78rem; margin:34px 0 8px; }
iframe { border-radius: 20px; }
</style>
"""


def aplicar():
    st.markdown(CSS, unsafe_allow_html=True)


def kpi(icone: str, label: str, valor: str, unidade: str = "", sub: str = "", barra: float | None = None):
    b = f'<div class="bar"><span style="width:{max(0, min(100, barra)):.0f}%"></span></div>' if barra is not None else ""
    st.markdown(
        f'<div class="glass kpi"><div class="label"><span>{icone}</span>{label}</div>'
        f'<div class="value">{valor}<small>{unidade}</small></div><div class="sub">{sub}</div>{b}</div>',
        unsafe_allow_html=True)


def titulo(texto: str):
    st.markdown(f'<div class="section-title">{texto}</div>', unsafe_allow_html=True)
