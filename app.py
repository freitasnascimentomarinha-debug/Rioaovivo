"""Rio ao Vivo — painel meteorológico em tempo real (Streamlit)."""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import folium
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium

import data
import style

st.set_page_config(page_title="Rio ao Vivo · Clima em tempo real", page_icon="🌊", layout="wide",
                   initial_sidebar_state="expanded")
style.aplicar()

TZ = ZoneInfo(data.TZ)
DIAS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
AZUL, ROXO, AMBAR, VERDE = "#38bdf8", "#818cf8", "#fbbf24", "#34d399"


def estilo_fig(fig: go.Figure, h: int = 340) -> go.Figure:
    fig.update_layout(
        height=h, margin=dict(l=8, r=8, t=24, b=8), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", color="#cbd5e1"), hovermode="x unified",
        legend=dict(orientation="h", y=1.12, x=0), hoverlabel=dict(bgcolor="#0f172a", bordercolor="#334155"))
    fig.update_xaxes(gridcolor="rgba(148,163,184,.08)", zeroline=False)
    fig.update_yaxes(gridcolor="rgba(148,163,184,.10)", zeroline=False)
    return fig


def linha_agora(fig: go.Figure, agora: datetime):
    fig.add_vline(x=agora.replace(tzinfo=None), line=dict(color="#f472b6", width=1.5, dash="dot"),
                  annotation_text="agora", annotation_font_color="#f472b6")


# ----------------------------------------------------------------------------- Sidebar
with st.sidebar:
    st.markdown("## 🌊 Rio ao Vivo")
    st.caption("Clima, mar, céu e alertas em tempo real.")
    nome = st.selectbox("📍 Local", list(data.LOCAIS) + ["Personalizado…"], index=0)
    if nome == "Personalizado…":
        lat = st.number_input("Latitude", value=-22.97, format="%.4f")
        lon = st.number_input("Longitude", value=-43.19, format="%.4f")
        lat_m, lon_m, uf, ibge = lat, lon, st.text_input("UF (para alertas)", "RJ").upper(), None
    else:
        lat, lon, lat_m, lon_m, uf, ibge = data.LOCAIS[nome]
    st.divider()
    auto = st.toggle("🔄 Atualização automática (5 min)", value=True)
    st.caption("Fontes: Open-Meteo · RainViewer · INMET via [RadarMeteorológico](https://radarmeteorologico.com.br) · Esri/OSM")
    st.markdown("🚨 **Emergência:** Defesa Civil **199** · Bombeiros **193**")


# ----------------------------------------------------------------------------- Painel
@st.fragment(run_every="5m" if auto else None)
def painel():
    try:
        w = data.previsao(lat, lon)
    except Exception as e:  # noqa: BLE001
        st.error("Não foi possível obter a previsão agora. Tente novamente em instantes.")
        st.caption(f"Detalhe técnico: {e}")
        return

    agora = datetime.now(TZ)
    c = w["current"]
    dia = bool(c["is_day"])
    txt, emoji = data.descricao(c["weather_code"], dia)

    h = pd.DataFrame(w["hourly"])
    h["time"] = pd.to_datetime(h["time"])
    d = pd.DataFrame(w["daily"])
    d["time"] = pd.to_datetime(d["time"])
    hoje = d.iloc[0]
    nascer, por = pd.to_datetime(hoje["sunrise"]), pd.to_datetime(hoje["sunset"])
    idx_h = int((h["time"] - agora.replace(tzinfo=None)).abs().idxmin())

    # --- Hero
    st.markdown(f"""
    <div class="hero">
      <div>
        <span class="live"><i></i>AO VIVO</span>
        <div class="local" style="margin-top:14px">📍 {nome if nome != 'Personalizado…' else f'{lat:.2f}, {lon:.2f}'}</div>
        <div class="temp">{c['temperature_2m']:.0f}°</div>
        <div class="cond">{txt} · sensação {c['apparent_temperature']:.0f}° · máx {hoje['temperature_2m_max']:.0f}° / mín {hoje['temperature_2m_min']:.0f}°</div>
        <div style="opacity:.6;font-size:.82rem;margin-top:8px">Atualizado às {agora:%H:%M} · {DIAS[agora.weekday()]}, {agora:%d/%m/%Y}</div>
      </div>
      <div class="emoji">{emoji}</div>
    </div>""", unsafe_allow_html=True)
    st.write("")

    # --- Alerta destacado
    try:
        avisos = data.alertas(uf, ibge)
        avisos_ok = True
    except Exception:  # noqa: BLE001
        avisos, avisos_ok = [], False
    try:
        nomes_mun = data.municipios_uf(uf)
    except Exception:  # noqa: BLE001
        nomes_mun = {}
    cidade = nomes_mun.get(ibge) or (nome.split("·")[0].strip() if ibge else "sua cidade")
    agora_av = [x for x in avisos if not x["futuro"]]
    locais = [x for x in agora_av if x["atinge_local"]]
    if locais:
        mais = max(locais, key=lambda x: x["nivel"])
        extra = f" (+{len(locais) - 1})" if len(locais) > 1 else ""
        st.markdown(f'<div class="alert" style="--c:#ef4444"><span class="badge">⚠️ {cidade.upper()} EM ALERTA</span>'
                    f'<b>{mais["titulo"]} · {mais["severidade"]}</b>{extra} até {mais["fim"][-5:]} — veja a aba “Alertas”.</div>',
                    unsafe_allow_html=True)
    elif ibge and avisos_ok:
        st.markdown(f'<div class="alert ok"><span class="badge">✅ SEM ALERTA</span>'
                    f'<b>{cidade}</b> não está em nenhum aviso em vigor agora.</div>', unsafe_allow_html=True)

    # --- KPIs
    try:
        ar = data.qualidade_ar(lat, lon)["current"]
        aqi = ar.get("us_aqi")
    except Exception:  # noqa: BLE001
        aqi = None
    uv = h.loc[idx_h, "uv_index"]
    vis = h.loc[idx_h, "visibility"] / 1000
    prob = h.loc[idx_h, "precipitation_probability"]
    k = st.columns(4)
    with k[0]:
        style.kpi("💧", "Umidade do ar", f"{c['relative_humidity_2m']:.0f}", "%",
                  "Seco" if c["relative_humidity_2m"] < 40 else "Confortável" if c["relative_humidity_2m"] < 70 else "Úmido",
                  c["relative_humidity_2m"])
    with k[1]:
        seta = f'<span class="arrow" style="transform:rotate({c["wind_direction_10m"] + 180}deg)">➤</span>'
        style.kpi("🌬️", "Vento", f"{c['wind_speed_10m']:.0f}", "km/h",
                  f"{seta} {data.direcao_vento(c['wind_direction_10m'])} · rajadas {c['wind_gusts_10m']:.0f} · {data.escala_beaufort(c['wind_speed_10m'])}",
                  min(c["wind_speed_10m"] / 80 * 100, 100))
    with k[2]:
        style.kpi("🌧️", "Precipitação", f"{c['precipitation']:.1f}", "mm",
                  f"Chance agora {prob:.0f}% · hoje {hoje['precipitation_sum']:.1f} mm", prob)
    with k[3]:
        style.kpi("🧭", "Pressão", f"{c['pressure_msl']:.0f}", "hPa", f"Nuvens {c['cloud_cover']:.0f}% · visib. {vis:.0f} km",
                  c["cloud_cover"])
    st.write("")
    k = st.columns(4)
    with k[0]:
        style.kpi("🌅", "Nascer do sol", f"{nascer:%H:%M}", "", f"Dia com {(por - nascer).seconds // 3600}h{((por - nascer).seconds // 60) % 60:02d}")
    with k[1]:
        style.kpi("🌇", "Pôr do sol", f"{por:%H:%M}", "", "Hora dourada às " + f"{(por - pd.Timedelta(minutes=60)):%H:%M}")
    with k[2]:
        rotulo_uv = "Baixo" if uv < 3 else "Moderado" if uv < 6 else "Alto" if uv < 8 else "Muito alto" if uv < 11 else "Extremo"
        style.kpi("☀️", "Índice UV", f"{uv:.0f}", "", f"{rotulo_uv} · máx. hoje {hoje['uv_index_max']:.0f}", min(uv / 11 * 100, 100))
    with k[3]:
        if aqi is not None:
            q = "Boa" if aqi <= 50 else "Moderada" if aqi <= 100 else "Ruim p/ sensíveis" if aqi <= 150 else "Ruim"
            style.kpi("🍃", "Qualidade do ar", f"{aqi:.0f}", "AQI", q, min(aqi / 200 * 100, 100))
        else:
            style.kpi("🍃", "Qualidade do ar", "—", "", "Indisponível")
    st.write("")

    tabs = st.tabs(["📈 Previsão", "🌧️ Chuva & Vento", "🌊 Maré", "🌙 Sol & Lua", "🚨 Alertas", "🗺️ Mapa"])

    # ---------------- Previsão
    with tabs[0]:
        style.titulo("Próximas 48 horas")
        p = h[(h["time"] >= agora.replace(tzinfo=None, minute=0, second=0, microsecond=0)) &
              (h["time"] < agora.replace(tzinfo=None) + pd.Timedelta(hours=48))]
        fig = go.Figure()
        fig.add_bar(x=p["time"], y=p["precipitation_probability"], name="Chance de chuva (%)", yaxis="y2",
                    marker_color="rgba(56,189,248,.28)")
        fig.add_scatter(x=p["time"], y=p["temperature_2m"], name="Temperatura (°C)", mode="lines",
                        line=dict(color=AMBAR, width=3, shape="spline"), fill="tozeroy", fillcolor="rgba(251,191,36,.07)")
        fig.update_layout(yaxis2=dict(overlaying="y", side="right", range=[0, 100], showgrid=False, ticksuffix="%"),
                          yaxis=dict(ticksuffix="°"))
        linha_agora(fig, agora)
        st.plotly_chart(estilo_fig(fig), width="stretch")

        style.titulo("Próximos 7 dias")
        cols = st.columns(7)
        for col, (_, r) in zip(cols, d.iterrows()):
            _, em = data.descricao(r["weather_code"])
            with col:
                st.markdown(f"""<div class="glass day"><div class="d">{DIAS[r['time'].weekday()]} {r['time']:%d}</div>
                <div class="e">{em}</div><div class="t">{r['temperature_2m_max']:.0f}° <span>{r['temperature_2m_min']:.0f}°</span></div>
                <div class="r">💧 {r['precipitation_probability_max']:.0f}% · {r['precipitation_sum']:.1f} mm</div></div>""",
                            unsafe_allow_html=True)

    # ---------------- Chuva & vento
    with tabs[1]:
        a, b = st.columns(2)
        p = h[(h["time"] >= agora.replace(tzinfo=None) - pd.Timedelta(hours=1)) &
              (h["time"] < agora.replace(tzinfo=None) + pd.Timedelta(hours=36))]
        with a:
            style.titulo("🌧️ Precipitação (mm/h)")
            fig = go.Figure(go.Bar(x=p["time"], y=p["precipitation"], marker=dict(color=p["precipitation"],
                            colorscale=[[0, "#38bdf8"], [.5, "#6366f1"], [1, "#e879f9"]]), name="mm"))
            linha_agora(fig, agora)
            st.plotly_chart(estilo_fig(fig, 320), width="stretch")
            total = p["precipitation"].sum()
            st.caption(f"Acumulado previsto nas próximas 36 h: **{total:.1f} mm**")
        with b:
            style.titulo("🌬️ Vento e rajadas (km/h)")
            fig = go.Figure()
            fig.add_scatter(x=p["time"], y=p["wind_gusts_10m"], name="Rajadas", line=dict(color=ROXO, width=2, dash="dot", shape="spline"))
            fig.add_scatter(x=p["time"], y=p["wind_speed_10m"], name="Vento", line=dict(color=AZUL, width=3, shape="spline"),
                            fill="tonexty", fillcolor="rgba(129,140,248,.10)")
            linha_agora(fig, agora)
            st.plotly_chart(estilo_fig(fig, 320), width="stretch")
        a, b = st.columns(2)
        with a:
            style.titulo("💧 Umidade relativa (%)")
            fig = go.Figure(go.Scatter(x=p["time"], y=p["relative_humidity_2m"], line=dict(color=VERDE, width=3, shape="spline"),
                                       fill="tozeroy", fillcolor="rgba(52,211,153,.10)"))
            fig.update_yaxes(range=[0, 100])
            linha_agora(fig, agora)
            st.plotly_chart(estilo_fig(fig, 280), width="stretch")
        with b:
            style.titulo("🧭 Rosa dos ventos (24 h)")
            q = h[(h["time"] >= agora.replace(tzinfo=None)) & (h["time"] < agora.replace(tzinfo=None) + pd.Timedelta(hours=24))]
            fig = go.Figure(go.Barpolar(r=q["wind_speed_10m"], theta=q["wind_direction_10m"], marker=dict(
                color=q["wind_speed_10m"], colorscale="Tealgrn", line=dict(color="#0f172a", width=1)), opacity=.9))
            fig.update_layout(polar=dict(bgcolor="rgba(0,0,0,0)", angularaxis=dict(direction="clockwise", rotation=90,
                              tickvals=[0, 90, 180, 270], ticktext=["N", "L", "S", "O"], gridcolor="rgba(148,163,184,.15)"),
                              radialaxis=dict(gridcolor="rgba(148,163,184,.15)", ticksuffix="")))
            st.plotly_chart(estilo_fig(fig, 280), width="stretch")

    # ---------------- Maré
    with tabs[2]:
        try:
            m = pd.DataFrame(data.mare(lat_m, lon_m)["hourly"])
            m["time"] = pd.to_datetime(m["time"])
            m = m.dropna(subset=["sea_level_height_msl"]).rename(columns={"time": "hora", "sea_level_height_msl": "nivel"})
            ext = data.extremos_mare(m)
            fut = ext[ext["hora"] > agora.replace(tzinfo=None)].head(4)
            i = (m["hora"] - agora.replace(tzinfo=None)).abs().idxmin()
            nivel_agora = m.loc[i, "nivel"]
            subindo = m.loc[min(i + 1, len(m) - 1), "nivel"] > nivel_agora
            a, b = st.columns([2, 1])
            with a:
                style.titulo("🌊 Nível do mar (m) — 72 h")
                fig = go.Figure(go.Scatter(x=m["hora"], y=m["nivel"], line=dict(color=AZUL, width=3, shape="spline"),
                                           fill="tozeroy", fillcolor="rgba(56,189,248,.14)", name="Nível"))
                fig.add_scatter(x=ext["hora"], y=ext["nivel"], mode="markers+text", showlegend=False, textposition="top center",
                                text=[f"{v:+.2f}" for v in ext["nivel"]], marker=dict(color="#f472b6", size=9),
                                textfont=dict(size=10, color="#f9a8d4"))
                linha_agora(fig, agora)
                st.plotly_chart(estilo_fig(fig, 360), width="stretch")
            with b:
                style.kpi("🌊", "Maré agora", f"{nivel_agora:+.2f}", "m", "⬆️ Enchendo" if subindo else "⬇️ Vazando")
                st.write("")
                linhas = "".join(
                    f'<div class="tide-row"><span><span class="pill {"hi" if r.tipo == "Preamar" else "lo"}">{r.tipo}</span></span>'
                    f'<span>{r.hora:%a %H:%M}</span><b>{r.nivel:+.2f} m</b></div>' for r in fut.itertuples())
                st.markdown(f'<div class="glass"><div class="kpi"><div class="label">📅 Próximas marés</div></div>{linhas}</div>',
                            unsafe_allow_html=True)
            ondas = m.loc[i]
            k = st.columns(3)
            with k[0]:
                style.kpi("🏄", "Altura das ondas", f"{ondas['wave_height']:.1f}", "m", f"Período {ondas['wave_period']:.0f} s")
            with k[1]:
                style.kpi("🧭", "Direção das ondas", data.direcao_vento(ondas["wave_direction"]), "", f"{ondas['wave_direction']:.0f}°")
            with k[2]:
                style.kpi("🌡️", "Temp. da água", f"{ondas['sea_surface_temperature']:.0f}", "°C", "Superfície do mar")
            st.caption("Nível relativo ao nível médio do mar (modelo global Open-Meteo). Valores aproximados — "
                       "para navegação use a Tábua de Marés oficial da Marinha do Brasil (DHN).")
        except Exception as e:  # noqa: BLE001
            st.warning("Dados de maré indisponíveis para este ponto (precisa ser uma localização costeira).")
            st.caption(str(e))

    # ---------------- Sol & Lua
    with tabs[3]:
        a, b = st.columns([3, 2])
        with a:
            style.titulo("☀️ Trajetória do sol")
            xs = pd.date_range(nascer - pd.Timedelta(minutes=30), por + pd.Timedelta(minutes=30), periods=120)
            import numpy as np
            frac = ((xs - nascer) / (por - nascer)).astype(float)
            ys = np.maximum(np.sin(np.pi * frac), 0)
            fig = go.Figure()
            fig.add_scatter(x=xs, y=ys, line=dict(color="rgba(251,191,36,.7)", width=3, shape="spline"), fill="tozeroy",
                            fillcolor="rgba(251,191,36,.10)", hoverinfo="skip")
            n = agora.replace(tzinfo=None)
            if nascer <= n <= por:
                fy = float(np.sin(np.pi * (n - nascer) / (por - nascer)))
                fig.add_scatter(x=[n], y=[fy], mode="markers+text", text=["☀️"], textfont=dict(size=26),
                                marker=dict(size=1, color="rgba(0,0,0,0)"), hoverinfo="skip")
            fig.add_scatter(x=[nascer, por], y=[0, 0], mode="markers+text", text=[f"🌅 {nascer:%H:%M}", f"🌇 {por:%H:%M}"],
                            textposition="bottom center", marker=dict(color=AMBAR, size=10))
            fig.update_yaxes(visible=False, range=[-0.3, 1.3])
            fig.update_xaxes(tickformat="%H:%M")
            fig.update_layout(showlegend=False, hovermode=False)
            st.plotly_chart(estilo_fig(fig, 320), width="stretch")
        with b:
            L = data.lua()
            style.titulo("🌙 Fase da lua")
            st.markdown(f"""<div class="glass" style="text-align:center">
              {data.svg_lua(L['fase'], 170)}
              <div style="font-size:1.4rem;font-weight:700;margin-top:6px">{L['nome']}</div>
              <div style="opacity:.7">{L['iluminacao'] * 100:.0f}% iluminada · {L['idade']:.1f} dias</div>
              <div class="bar"><span style="width:{L['iluminacao'] * 100:.0f}%;background:linear-gradient(90deg,#64748b,#fef9c3)"></span></div>
              <div style="display:flex;justify-content:space-around;margin-top:14px;font-size:.88rem">
                <div>🌑 Nova<br><b>{L['proxima_nova'].astimezone(TZ):%d/%m}</b></div>
                <div>🌕 Cheia<br><b>{L['proxima_cheia'].astimezone(TZ):%d/%m}</b></div></div></div>""", unsafe_allow_html=True)

    # ---------------- Alertas
    with tabs[4]:
        style.titulo(f"🚨 Avisos meteorológicos — {uf}")
        cores = {"perigo potencial": "#fbbf24", "perigo": "#fb923c", "grande perigo": "#ef4444"}

        def fmt(s: str) -> str:  # 2026-10-29 09:00 -> 29/10 09:00
            try:
                return datetime.strptime(s, "%Y-%m-%d %H:%M").strftime("%d/%m %H:%M")
            except ValueError:
                return s

        if not avisos_ok:
            st.warning("Não foi possível consultar os avisos agora. Consulte também o app **Defesa Civil Alerta** "
                       "(SMS **40199**) e o **Alerta Rio** (alertario.rio.rj.gov.br).")
        else:
            if ibge:
                if locais:
                    resumo = " · ".join(f'{x["titulo"]} ({x["severidade"]})' for x in locais)
                    st.markdown(f'<div class="alert" style="--c:#ef4444"><div class="h">⚠️ {cidade} ESTÁ em alerta agora</div>'
                                f'<div class="m">{resumo}</div></div>', unsafe_allow_html=True)
                else:
                    prox = [x for x in avisos if x["futuro"] and x["atinge_local"]]
                    extra = (f" Há {len(prox)} aviso(s) previsto(s) para os próximos dias que incluem {cidade}." if prox else "")
                    st.markdown(f'<div class="alert ok"><div class="h">✅ {cidade} NÃO está em nenhum aviso em vigor agora</div>'
                                f'<div class="m">Os avisos abaixo valem para outras cidades de {uf}.{extra}</div></div>',
                                unsafe_allow_html=True)
            if not avisos:
                st.info(f"Nenhum aviso ativo do INMET para {uf} neste momento.")

            def cartao(a: dict):
                cor = cores.get(a["severidade"].lower(), "#fb923c")
                if ibge:
                    pill = (f'<span class="badge" style="background:#ef4444;color:#fff">📍 ATINGE {cidade.upper()}</span>'
                            if a["atinge_local"] else
                            f'<span class="badge" style="background:#334155;color:#cbd5e1">NÃO atinge {cidade}</span>')
                else:
                    pill = ""
                ativos = [nomes_mun[g] for g in a.get("geocodes", ()) if g in nomes_mun]
                dim = "" if (a["atinge_local"] or not ibge) else "opacity:.6;"
                st.markdown(f"""<div class="alert" style="--c:{cor};{dim}"><div style="margin-bottom:8px">{pill}</div>
                    <div class="h"><span class="badge">{a['severidade'] or 'AVISO'}</span>{a['titulo']}</div>
                    <div class="m">{'🔜 Previsto' if a['futuro'] else '🕒 Em vigor'}: {fmt(a['inicio'])} → {fmt(a['fim'])}
                    · {len(ativos)} de {len(nomes_mun) or '—'} municípios de {uf} (Brasil: {a['municipios']})</div>
                    <div class="m">{' '.join(a['riscos'][:1])}</div></div>""", unsafe_allow_html=True)
                if ativos:
                    with st.expander(f"Municípios de {uf} neste aviso ({len(ativos)})"):
                        st.write(", ".join(sorted(ativos)))

            for titulo_sec, lista in (("🕒 Em vigor agora", agora_av), ("🔜 Previstos", [x for x in avisos if x["futuro"]])):
                if lista:
                    st.markdown(f"##### {titulo_sec}")
                    for a in lista:
                        cartao(a)
        st.info("📱 Cadastre-se no alerta por SMS da Defesa Civil: envie seu **CEP** para **40199**. Emergência: **199**.")

    # ---------------- Mapa
    with tabs[5]:
        style.titulo("🗺️ Mapa interativo · radar de chuva ao vivo")
        mp = folium.Map(location=[lat, lon], zoom_start=8, tiles=None, control_scale=True)
        folium.TileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}",
                         attr="Esri, HERE, Garmin", name="🌑 Escuro", max_zoom=16).add_to(mp)
        folium.TileLayer("OpenStreetMap", name="🗺️ Ruas", show=False).add_to(mp)
        folium.TileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                         attr="Esri", name="🛰️ Satélite", show=False).add_to(mp)
        try:
            rd = data.radar()
            f = [x for x in rd["frames"]][-1]
            folium.TileLayer(f"{rd['host']}{f['path']}/256/{{z}}/{{x}}/{{y}}/6/1_1.png", attr="RainViewer", name="🌧️ Radar de chuva",
                             opacity=.75, overlay=True, max_native_zoom=7, max_zoom=12).add_to(mp)
        except Exception:  # noqa: BLE001
            st.caption("Radar indisponível no momento.")
        grupo = folium.FeatureGroup(name="🌡️ Temperaturas")
        try:
            for t in data.temperaturas_mapa():
                _, em = data.descricao(t["weather_code"], bool(t["is_day"]))
                html = (f'<div style="background:rgba(15,23,42,.88);color:#fff;border:1px solid #38bdf8;border-radius:14px;'
                        f'padding:3px 9px;font:600 12px Inter,sans-serif;white-space:nowrap;box-shadow:0 4px 14px #0008">'
                        f'{em} {t["temperature_2m"]:.0f}° <span style="opacity:.6">{t["nome"]}</span></div>')
                folium.Marker([t["lat"], t["lon"]], icon=folium.DivIcon(html=html, icon_anchor=(40, 12)),
                              tooltip=f'{t["nome"]}: {t["temperature_2m"]:.0f}°C · vento {t["wind_speed_10m"]:.0f} km/h · {t["precipitation"]:.1f} mm').add_to(grupo)
        except Exception:  # noqa: BLE001
            pass
        grupo.add_to(mp)
        folium.CircleMarker([lat, lon], radius=9, color="#f472b6", fill=True, fill_opacity=.9,
                            tooltip=f"📍 {nome}").add_to(mp)
        folium.LayerControl(collapsed=False).add_to(mp)
        st_folium(mp, height=560, width="stretch", returned_objects=[], key=f"mapa-{lat}-{lon}")
        st.caption("Radar: RainViewer · Camadas alternáveis no canto superior direito do mapa.")

    st.markdown(f'<div class="footer">Rio ao Vivo · dados atualizados às {agora:%H:%M:%S} · Open-Meteo · RainViewer · INMET via <a href="https://radarmeteorologico.com.br" style="color:inherit">RadarMeteorológico</a></div>',
                unsafe_allow_html=True)


painel()
