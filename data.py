"""Acesso a dados: Open-Meteo, RainViewer, INMET (alertas) e cálculos astronômicos."""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests
import streamlit as st

TZ = "America/Sao_Paulo"
HEADERS = {"User-Agent": "RioAoVivo/1.0 (streamlit)"}

# nome -> (lat, lon, lat_mar, lon_mar, UF, código IBGE do município)
LOCAIS: dict[str, tuple[float, float, float, float, str, int]] = {
    "Rio de Janeiro · Copacabana": (-22.971, -43.186, -23.05, -43.17, "RJ", 3304557),
    "Rio de Janeiro · Barra da Tijuca": (-23.012, -43.32, -23.10, -43.32, "RJ", 3304557),
    "Rio de Janeiro · Centro": (-22.906, -43.173, -23.05, -43.17, "RJ", 3304557),
    "Niterói": (-22.883, -43.104, -22.98, -43.08, "RJ", 3303302),
    "Cabo Frio": (-22.879, -42.019, -23.00, -42.00, "RJ", 3300704),
    "Angra dos Reis": (-23.007, -44.318, -23.12, -44.30, "RJ", 3300100),
    "Santos": (-23.960, -46.333, -24.06, -46.30, "SP", 3548500),
    "Vitória": (-20.315, -40.312, -20.40, -40.25, "ES", 3205309),
    "Salvador": (-12.971, -38.501, -13.05, -38.45, "BA", 2927408),
    "Florianópolis": (-27.595, -48.548, -27.65, -48.40, "SC", 4205407),
}

# Cidades exibidas como "bolhas" no mapa
CIDADES_MAPA = {
    "Rio": (-22.906, -43.173), "Niterói": (-22.883, -43.104),
    "Petrópolis": (-22.505, -43.178), "Nova Iguaçu": (-22.759, -43.451),
    "Angra": (-23.007, -44.318), "Cabo Frio": (-22.879, -42.019),
    "Macaé": (-22.371, -41.787), "Campos": (-21.754, -41.324),
    "Volta Redonda": (-22.523, -44.104), "Teresópolis": (-22.412, -42.966),
}

WMO = {
    0: ("Céu limpo", "☀️", "🌙"), 1: ("Predomínio de sol", "🌤️", "🌙"),
    2: ("Parcialmente nublado", "⛅", "☁️"), 3: ("Nublado", "☁️", "☁️"),
    45: ("Nevoeiro", "🌫️", "🌫️"), 48: ("Nevoeiro gelado", "🌫️", "🌫️"),
    51: ("Garoa fraca", "🌦️", "🌧️"), 53: ("Garoa", "🌦️", "🌧️"), 55: ("Garoa forte", "🌧️", "🌧️"),
    56: ("Garoa gelada", "🌧️", "🌧️"), 57: ("Garoa gelada forte", "🌧️", "🌧️"),
    61: ("Chuva fraca", "🌦️", "🌧️"), 63: ("Chuva moderada", "🌧️", "🌧️"), 65: ("Chuva forte", "🌧️", "🌧️"),
    66: ("Chuva gelada", "🌧️", "🌧️"), 67: ("Chuva gelada forte", "🌧️", "🌧️"),
    71: ("Neve fraca", "🌨️", "🌨️"), 73: ("Neve", "🌨️", "🌨️"), 75: ("Neve forte", "❄️", "❄️"),
    77: ("Granizo fino", "🌨️", "🌨️"),
    80: ("Pancadas fracas", "🌦️", "🌧️"), 81: ("Pancadas de chuva", "🌧️", "🌧️"), 82: ("Pancadas violentas", "⛈️", "⛈️"),
    85: ("Pancadas de neve", "🌨️", "🌨️"), 86: ("Pancadas de neve fortes", "❄️", "❄️"),
    95: ("Trovoadas", "⛈️", "⛈️"), 96: ("Trovoadas c/ granizo", "⛈️", "⛈️"), 99: ("Trovoadas c/ granizo forte", "⛈️", "⛈️"),
}


def descricao(code: int, is_day: bool = True) -> tuple[str, str]:
    txt, dia, noite = WMO.get(int(code), ("—", "🌡️", "🌡️"))
    return txt, (dia if is_day else noite)


def direcao_vento(graus: float) -> str:
    pts = ["N", "NE", "L", "SE", "S", "SO", "O", "NO"]
    return pts[int((graus % 360) / 45 + 0.5) % 8]


def escala_beaufort(kmh: float) -> str:
    lim = [(1, "Calmaria"), (6, "Aragem"), (12, "Brisa leve"), (20, "Brisa fraca"), (29, "Brisa moderada"),
           (39, "Brisa forte"), (50, "Vento fresco"), (62, "Vento forte"), (75, "Ventania"), (89, "Ventania forte")]
    for limite, nome in lim:
        if kmh < limite:
            return nome
    return "Tempestade"


# ----------------------------------------------------------------------------- APIs
def _get(url: str, params: dict | None = None, timeout: int = 15):
    r = requests.get(url, params=params, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    return r.json()


@st.cache_data(ttl=300, show_spinner=False)
def previsao(lat: float, lon: float) -> dict:
    return _get("https://api.open-meteo.com/v1/forecast", {
        "latitude": lat, "longitude": lon, "timezone": TZ, "forecast_days": 7, "wind_speed_unit": "kmh",
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,is_day,precipitation,weather_code,"
                   "cloud_cover,pressure_msl,wind_speed_10m,wind_direction_10m,wind_gusts_10m",
        "hourly": "temperature_2m,relative_humidity_2m,precipitation_probability,precipitation,weather_code,"
                  "wind_speed_10m,wind_gusts_10m,wind_direction_10m,uv_index,visibility",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,sunrise,sunset,precipitation_sum,"
                 "precipitation_probability_max,wind_speed_10m_max,uv_index_max",
    })


@st.cache_data(ttl=900, show_spinner=False)
def mare(lat: float, lon: float) -> dict:
    return _get("https://marine-api.open-meteo.com/v1/marine", {
        "latitude": lat, "longitude": lon, "timezone": TZ, "forecast_days": 3,
        "hourly": "sea_level_height_msl,wave_height,wave_period,wave_direction,sea_surface_temperature",
    })


@st.cache_data(ttl=900, show_spinner=False)
def qualidade_ar(lat: float, lon: float) -> dict:
    return _get("https://air-quality-api.open-meteo.com/v1/air-quality", {
        "latitude": lat, "longitude": lon, "timezone": TZ, "current": "us_aqi,pm2_5,pm10",
    })


@st.cache_data(ttl=600, show_spinner=False)
def temperaturas_mapa() -> list[dict]:
    nomes = list(CIDADES_MAPA)
    lats = ",".join(str(CIDADES_MAPA[n][0]) for n in nomes)
    lons = ",".join(str(CIDADES_MAPA[n][1]) for n in nomes)
    js = _get("https://api.open-meteo.com/v1/forecast", {
        "latitude": lats, "longitude": lons, "timezone": TZ, "wind_speed_unit": "kmh",
        "current": "temperature_2m,precipitation,weather_code,wind_speed_10m,is_day",
    })
    js = js if isinstance(js, list) else [js]
    return [{"nome": n, "lat": CIDADES_MAPA[n][0], "lon": CIDADES_MAPA[n][1], **j["current"]}
            for n, j in zip(nomes, js)]


@st.cache_data(ttl=300, show_spinner=False)
def radar() -> dict:
    js = _get("https://api.rainviewer.com/public/weather-maps.json")
    frames = js["radar"]["past"] + js["radar"].get("nowcast", [])
    return {"host": js["host"], "frames": frames}


@st.cache_data(ttl=86400, show_spinner=False)
def municipios_uf(uf: str) -> dict[int, str]:
    js = _get("https://radarmeteorologico.com.br/api/v1/cidades", {"uf": uf}, timeout=20)
    return {c["ibge"]: c["nome"] for c in js.get("cidades", [])}


@st.cache_data(ttl=300, show_spinner=False)
def alertas(uf: str, ibge: int | None = None, _v: int = 2) -> list[dict]:  # _v invalida cache antigo
    """Avisos oficiais do INMET (base dos alertas da Defesa Civil) via API pública do RadarMeteorológico."""
    js = _get("https://radarmeteorologico.com.br/api/v1/alertas", {"uf": uf}, timeout=20)
    saida = []
    for a in js.get("alertas", []):
        saida.append({
            "titulo": a.get("evento") or "Aviso meteorológico",
            "severidade": str(a.get("severidade") or ""),
            "nivel": a.get("nivel") or 0,
            "inicio": a.get("inicio") or "", "fim": a.get("fim") or "",
            "futuro": bool(a.get("futuro")),
            "riscos": a.get("riscos") or [], "instrucoes": a.get("instrucoes") or [],
            "municipios": a.get("municipios_afetados") or 0,
            "url": a.get("url") or "",
            "geocodes": set(a.get("geocodes") or []),
            "atinge_local": bool(ibge and ibge in (a.get("geocodes") or [])),
        })
    saida.sort(key=lambda x: (not x["atinge_local"], x["futuro"], -x["nivel"]))
    return saida


# ----------------------------------------------------------------------------- Astronomia
SINODICO = 29.530588853
_LUA_NOVA_REF = datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)


def lua(agora: datetime | None = None) -> dict:
    agora = (agora or datetime.now(timezone.utc)).astimezone(timezone.utc)
    idade = ((agora - _LUA_NOVA_REF).total_seconds() / 86400) % SINODICO
    fase = idade / SINODICO
    ilum = (1 - math.cos(2 * math.pi * fase)) / 2
    nomes = [(0.03, "Lua Nova", "🌑"), (0.22, "Lua Crescente", "🌒"), (0.28, "Quarto Crescente", "🌓"),
             (0.47, "Crescente Gibosa", "🌔"), (0.53, "Lua Cheia", "🌕"), (0.72, "Minguante Gibosa", "🌖"),
             (0.78, "Quarto Minguante", "🌗"), (0.97, "Lua Minguante", "🌘"), (1.01, "Lua Nova", "🌑")]
    nome, emoji = next((n, e) for lim, n, e in nomes if fase < lim)
    inicio_ciclo = agora - timedelta(days=idade)

    def proximo(alvo: float) -> datetime:
        d = inicio_ciclo + timedelta(days=SINODICO * alvo)
        return d if d > agora else d + timedelta(days=SINODICO)

    return {"idade": idade, "fase": fase, "iluminacao": ilum, "nome": nome, "emoji": emoji,
            "proxima_nova": proximo(0), "proxima_cheia": proximo(0.5)}


def svg_lua(fase: float, tamanho: int = 150) -> str:
    """Lua desenhada em SVG, orientada para o Hemisfério Sul (crescente iluminada à esquerda)."""
    r = tamanho / 2 - 8
    c = tamanho / 2
    crescente = fase < 0.5
    ilum_direita = not crescente  # no Hemisfério Sul a lua crescente aparece iluminada à esquerda
    pouca_luz = abs(fase - 0.5) > 0.25
    s1 = 1 if ilum_direita else 0
    s2 = (1 - s1) if pouca_luz else s1
    rx = r * abs(math.cos(2 * math.pi * fase))
    path = f"M {c} {c - r} A {r} {r} 0 0 {s1} {c} {c + r} A {rx:.2f} {r} 0 0 {s2} {c} {c - r} Z"
    svg = f"""<svg width="{tamanho}" height="{tamanho}" viewBox="0 0 {tamanho} {tamanho}" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <radialGradient id="lg" cx="40%" cy="38%"><stop offset="0%" stop-color="#fffdf2"/><stop offset="100%" stop-color="#d9d4b8"/></radialGradient>
        <filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="5" result="b"/>
          <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
      </defs>
      <circle cx="{c}" cy="{c}" r="{r}" fill="#111a2e" stroke="#25324d" stroke-width="1.5"/>
      <path d="{path}" fill="url(#lg)" filter="url(#glow)"/>
    </svg>"""
    return "".join(l.strip() for l in svg.splitlines())


# ----------------------------------------------------------------------------- Maré
def extremos_mare(df: pd.DataFrame, col: str = "nivel") -> pd.DataFrame:
    """Detecta preamares e baixa-mares (extremos locais) na série horária."""
    s = df[col].reset_index(drop=True)
    linhas = []
    for i in range(1, len(s) - 1):
        if s[i] >= s[i - 1] and s[i] > s[i + 1]:
            linhas.append((df["hora"].iloc[i], s[i], "Preamar"))
        elif s[i] <= s[i - 1] and s[i] < s[i + 1]:
            linhas.append((df["hora"].iloc[i], s[i], "Baixa-mar"))
    return pd.DataFrame(linhas, columns=["hora", "nivel", "tipo"])
