"""Abas 'Cidade ao vivo': trânsito, chuva/alagamentos e segurança."""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import folium
import streamlit as st
from branca.element import MacroElement
from jinja2 import Template
from streamlit_folium import st_folium

import data
import style

ESRI_DARK = "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}"


class ArcGISExport(MacroElement):
    """Camada dinâmica ArcGIS (operação 'export') como tiles Leaflet."""

    _template = Template("""{% macro script(this, kwargs) %}
        var {{ this.get_name() }} = L.tileLayer('', {opacity: {{ this.opacity }}, tileSize: 256, attribution: 'GeoRio / Prefeitura do Rio'});
        {{ this.get_name() }}.getTileUrl = function(c) {
            var n = Math.pow(2, c.z), s = 40075016.68557849 / n, minx = -20037508.342789244 + c.x * s, maxy = 20037508.342789244 - c.y * s;
            return '{{ this.url }}/export?bbox=' + minx + ',' + (maxy - s) + ',' + (minx + s) + ',' + maxy +
                   '&bboxSR=3857&imageSR=3857&size=256,256&format=png32&transparent=true&f=image';
        };
        {{ this.get_name() }}.addTo({{ this._parent.get_name() }});
    {% endmacro %}""")

    def __init__(self, url: str, opacity: float = 0.55):
        super().__init__()
        self._name = "ArcGISExport"
        self.url, self.opacity = url, opacity


def mapa_base(lat: float, lon: float, zoom: int) -> folium.Map:
    m = folium.Map(location=[lat, lon], zoom_start=zoom, tiles=None, control_scale=True)
    folium.TileLayer(ESRI_DARK, attr="Esri, HERE, Garmin", name="Escuro", max_zoom=16).add_to(m)
    return m


# ----------------------------------------------------------------------------- Trânsito
def transito(lat: float, lon: float, nome: str, rio: bool = False):
    if rio:
        modo = st.radio("Fonte", ["Waze ao vivo", "Ônibus do Rio (lentidão)"], horizontal=True, label_visibility="collapsed")
        if modo != "Waze ao vivo":
            return onibus(lat, lon)
    style.titulo("🚦 Trânsito ao vivo")
    zoom = st.slider("Zoom", 9, 16, 12, key="zoom_waze")
    url = f"https://embed.waze.com/iframe?zoom={zoom}&lat={lat}&lon={lon}&ct=livemap"
    if hasattr(st, "iframe"):
        st.iframe(url, height=560)
    else:  # Streamlit mais antigo
        import streamlit.components.v1 as components
        components.iframe(url, height=560)
    c1, c2, c3 = st.columns(3)
    c1.link_button("🗺️ Google Maps (trânsito)", f"https://www.google.com/maps/@{lat},{lon},12z/data=!5m1!1e1", width="stretch")
    c2.link_button("🚗 Abrir no Waze", f"https://www.waze.com/live-map/directions?latlng={lat}%2C{lon}", width="stretch")
    c3.link_button("📹 Câmeras do COR Rio", "https://cor.rio/", width="stretch")
    st.caption("Mapa do Waze (colaborativo). Para reforçar o app com camada própria, configure `TOMTOM_KEY` nos secrets.")


# ----------------------------------------------------------------------------- Chuva e alagamentos
def alagamentos():
    style.titulo("🌊 Chuva por estação e pontos de alagamento — Rio de Janeiro")
    try:
        est = data.estacoes_alertario()
        chuva = data.chuva_estimada(tuple((e["lat"], e["lon"]) for e in est))
    except Exception as e:  # noqa: BLE001
        st.warning("Não foi possível carregar as estações agora.")
        st.caption(str(e))
        return
    for e, c in zip(est, chuva):
        e.update(c)
    a, b = st.columns([3, 1])
    with b:
        mais = max(est, key=lambda x: x["h6"])
        classe, _ = data.intensidade_chuva(max(x["pico"] for x in est))
        style.kpi("🌧️", "Pico previsto (6 h)", f"{max(x['pico'] for x in est):.1f}", "mm/h", f"Intensidade: {classe}")
        st.write("")
        style.kpi("📍", "Mais chuva em 6 h", f"{mais['h6']:.1f}", "mm", mais["nome"])
        st.write("")
        mostrar_desl = st.toggle("⛰️ Suscetibilidade a deslizamentos", value=False)
        mostrar_pts = st.toggle("🌊 Pontos críticos de alagamento", value=True)
    with a:
        m = mapa_base(-22.93, -43.35, 10)
        if mostrar_desl:
            ArcGISExport(data.DESLIZAMENTO_URL).add_to(m)
        for e in est:
            classe, cor = data.intensidade_chuva(max(e["agora"], e["pico"] if e["agora"] < 0.1 else e["agora"]))
            folium.CircleMarker(
                [e["lat"], e["lon"]], radius=7 + min(e["h6"], 25) * .5, color=cor, weight=2, fill=True, fill_opacity=.55,
                tooltip=(f'<b>{e["nome"]}</b><br>{e["endereco"]}<br>Agora: {e["agora"]:.1f} mm/h<br>'
                         f'Próx. 3 h: {e["h3"]:.1f} mm · 6 h: {e["h6"]:.1f} mm<br>{classe}')).add_to(m)
        if mostrar_pts:
            for n, (la, lo) in data.PONTOS_ALAGAMENTO.items():
                html = ('<div style="font-size:20px;filter:drop-shadow(0 2px 4px #000)">🌊</div>')
                folium.Marker([la, lo], icon=folium.DivIcon(html=html, icon_anchor=(10, 10)),
                              tooltip=f"{n} — área historicamente sujeita a alagamento").add_to(m)
        st_folium(m, height=520, width="stretch", returned_objects=[], key="mapa-alag")
    st.caption("⚠️ A chuva por estação é **estimada por modelo** (Open-Meteo) nas coordenadas das estações do Alerta Rio — "
               "não é a leitura dos pluviômetros. Os pontos de alagamento são **referência histórica**, não alerta em tempo real. "
               "Para dados oficiais: alertario.rio.rj.gov.br. Deslizamentos (GeoRio): 🟢 baixa · 🟡 média · 🔴 alta suscetibilidade.")


# ----------------------------------------------------------------------------- Segurança
def seguranca(lat: float, lon: float, uf: str):
    style.titulo("🛡️ Tiroteios registrados — Fogo Cruzado")
    try:
        email = st.secrets["FOGOCRUZADO_EMAIL"]
        senha = st.secrets["FOGOCRUZADO_PASSWORD"] if "FOGOCRUZADO_PASSWORD" in st.secrets else st.secrets["FOGOCRUZADO_SENHA"]
    except Exception:  # noqa: BLE001
        st.markdown(
            '<div class="glass"><b>Camada desativada</b><br><span style="opacity:.75">Ela usa a API pública do '
            '<a href="https://fogocruzado.org.br" target="_blank">Fogo Cruzado</a> (tiroteios na Região Metropolitana do Rio), '
            'que exige cadastro gratuito. Adicione <code>FOGOCRUZADO_EMAIL</code> e <code>FOGOCRUZADO_PASSWORD</code> '
            'em <i>Settings → Secrets</i> do app para ativar.</span></div>', unsafe_allow_html=True)
        st.caption("Não exibimos “mapa de facções” nem rótulos de “zonas perigosas”: não há fonte oficial confiável e isso estigmatiza moradores.")
        return
    try:
        dias = st.select_slider("Período", [1, 3, 7, 15, 30], value=7, format_func=lambda d: f"{d} dia(s)")
        ocs = data.tiroteios(email, senha, dias)
    except Exception as e:  # noqa: BLE001
        st.warning("Não foi possível consultar o Fogo Cruzado agora.")
        st.caption(f"{type(e).__name__}: {e}")
        return
    com_mortos = [o for o in ocs if o["mortos"]]
    k = st.columns(4)
    with k[0]:
        style.kpi("💥", "Tiroteios", str(len(ocs)), "", f"Últimos {dias} dia(s)")
    with k[1]:
        style.kpi("🩸", "Com feridos", str(sum(1 for o in ocs if o["feridos"])), "", f"{sum(o['feridos'] for o in ocs)} pessoa(s)")
    with k[2]:
        style.kpi("⚠️", "Com mortes", str(len(com_mortos)), "", f"{sum(o['mortos'] for o in com_mortos)} pessoa(s)")
    with k[3]:
        style.kpi("🚓", "Ação policial", str(sum(o["policia"] for o in ocs)), "", "Operações / presença de agentes")
    st.write("")

    filtro = st.segmented_control("Mostrar", ["Todos", "Com mortes", "Com feridos", "Sem vítimas", "Ação policial"],
                                  default="Todos", key="filtro_tiro") or "Todos"
    teste = {"Todos": lambda o: True, "Com mortes": lambda o: o["mortos"], "Com feridos": lambda o: o["feridos"],
             "Sem vítimas": lambda o: not o["vitimas"], "Ação policial": lambda o: o["policia"]}[filtro]
    vis = [o for o in ocs if teste(o)]

    def classe(o):
        if o["chacina"]:
            return "Chacina", "#a855f7"
        if o["mortos"]:
            return "Com morte(s)", "#ef4444"
        if o["feridos"]:
            return "Com ferido(s)", "#fb923c"
        return "Sem vítimas", "#facc15"

    def fmt_data(s):
        try:
            return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(ZoneInfo(data.TZ)).strftime("%d/%m/%Y %H:%M")
        except ValueError:
            return s[:16].replace("T", " ")

    m = mapa_base(lat, lon, 10)
    for o in vis:
        tipo, cor = classe(o)
        linhas = [f'<div style="font-weight:700;font-size:14px;color:{cor}">{tipo}{" · 🚓 ação policial" if o["policia"] else ""}</div>',
                  f'<div style="opacity:.8">{fmt_data(o["data"])}</div>',
                  f'<div>📍 {o["endereco"] or "—"}<br>{o["bairro"]}{" · " if o["bairro"] and o["cidade"] else ""}{o["cidade"]}</div>']
        if o["motivo"]:
            linhas.append(f'<div><b>Motivo:</b> {o["motivo"]}{" (" + o["motivos_compl"] + ")" if o["motivos_compl"] else ""}</div>')
        if o["unidade"]:
            linhas.append(f'<div><b>Unidade:</b> {o["unidade"]}</div>')
        if o["detalhes"]:
            linhas.append("<div><b>Vítimas:</b><br>" + "<br>".join("• " + x for x in o["detalhes"][:8]) + "</div>")
        else:
            linhas.append("<div><b>Vítimas:</b> nenhuma registrada</div>")
        html = '<div style="font:12px Inter,sans-serif;line-height:1.5;min-width:210px;max-width:290px">' + "".join(linhas) + "</div>"
        folium.CircleMarker([o["lat"], o["lon"]], radius=6 + 3 * min(o["mortos"] + o["feridos"], 4),
                            color="#ffffff" if o["policia"] else cor, weight=2 if o["policia"] else 1, fill=True, fill_color=cor,
                            fill_opacity=.75, popup=folium.Popup(html, max_width=300),
                            tooltip=f'{tipo} · {o["bairro"] or o["cidade"]}').add_to(m)
    st_folium(m, height=520, width="stretch", returned_objects=[], key=f"mapa-seg-{filtro}-{dias}")
    st.markdown('<span style="font-size:.82rem;opacity:.75">🟡 sem vítimas · 🟠 com ferido(s) · 🔴 com morte(s) · 🟣 chacina · '
                'contorno branco = ação policial · clique no ponto para ver os detalhes</span>', unsafe_allow_html=True)

    if vis:
        import pandas as pd
        tabela = pd.DataFrame([{"Data": fmt_data(o["data"]), "Tipo": classe(o)[0], "Bairro": o["bairro"], "Cidade": o["cidade"],
                                "Motivo": o["motivo"], "Mortos": o["mortos"], "Feridos": o["feridos"],
                                "Ação policial": "Sim" if o["policia"] else "Não"} for o in vis])
        with st.expander(f"📋 Lista das ocorrências ({len(vis)})"):
            st.dataframe(tabela, hide_index=True, width="stretch")
        with st.expander("🧪 Dados brutos (primeira ocorrência) — para diagnóstico"):
            st.json(vis[0]["bruto"])
    st.caption("O Fogo Cruzado registra **tiroteios** e suas vítimas; assaltos e outros crimes não fazem parte dessa base. Fonte: Fogo Cruzado (fogocruzado.org.br). Dados registrados e verificados pela organização; podem ter atraso.")


# ----------------------------------------------------------------------------- Ônibus
def onibus(lat: float, lon: float):
    from folium.plugins import HeatMap
    style.titulo("🚌 Ônibus em tempo real — lentidão estimada")
    try:
        df = data.onibus()
    except Exception as e:  # noqa: BLE001
        st.warning("Não foi possível carregar o GPS dos ônibus agora.")
        st.caption(str(e))
        return
    if df.empty:
        st.info("Sem posições recentes de ônibus neste momento.")
        return
    em_mov = df[df["velocidade"] > 0]
    lentos = df[(df["velocidade"] <= 5)]
    k = st.columns(3)
    with k[0]:
        style.kpi("🚌", "Ônibus rodando", f"{len(df):,}".replace(",", "."), "", f"{df['servico'].nunique()} linhas")
    with k[1]:
        style.kpi("⏱️", "Velocidade média", f"{em_mov['velocidade'].mean():.0f}", "km/h", "Só veículos em movimento")
    with k[2]:
        style.kpi("🐢", "Lentos ou parados", f"{len(lentos) / len(df) * 100:.0f}", "%", "≤ 5 km/h (inclui pontos e garagens)")
    st.write("")
    texto = st.text_input("Acompanhar linhas (opcional)", placeholder="Digite o número, ex.: 485 ou 485, 2336 — e tecle Enter",
                          key="linhas_onibus")
    pedidas = [t.strip().upper() for t in texto.replace(";", ",").split(",") if t.strip()][:5]
    disponiveis = set(df["servico"].dropna().astype(str).str.upper())
    escolha = [p for p in pedidas if p in disponiveis]
    nao_achadas = [p for p in pedidas if p not in disponiveis]
    if nao_achadas:
        st.caption(f"⚠️ Linha(s) sem ônibus rodando agora: {', '.join(nao_achadas)}")
    m = mapa_base(lat if -23.2 < lat < -22.6 else -22.92, lon if -43.9 < lon < -43.0 else -43.3, 11)
    if escolha:
        for _, r in df[df["servico"].astype(str).str.upper().isin(escolha)].iterrows():
            folium.CircleMarker([r["lat"], r["lon"]], radius=6, color="#38bdf8", fill=True, fill_opacity=.9,
                                tooltip=f'Linha {r["servico"]} · {r["velocidade"]:.0f} km/h').add_to(m)
    else:
        HeatMap(lentos[["lat", "lon"]].values.tolist(), radius=14, blur=18, min_opacity=.25,
                gradient={0.3: "#facc15", 0.6: "#fb923c", 1.0: "#ef4444"}).add_to(m)
    st_folium(m, height=520, width="stretch", returned_objects=[], key="mapa-bus")
    idade = (data.datetime.now(data.timezone.utc) - df["datetime"].max()).total_seconds()
    st.caption(f"Fonte: GPS dos ônibus (SPPO) — dados.mobilidade.rio · posição mais recente há ~{idade:.0f} s. "
               "O mapa de calor mostra onde há ônibus lentos/parados, um **indicador indireto** de congestionamento: "
               "também aparecem terminais, pontos e garagens.")
