"""Abas 'Cidade ao vivo': trânsito, chuva/alagamentos e segurança."""
from __future__ import annotations

import folium
import streamlit as st
import streamlit.components.v1 as components
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
def transito(lat: float, lon: float, nome: str):
    style.titulo("🚦 Trânsito ao vivo")
    zoom = st.slider("Zoom", 9, 16, 12, key="zoom_waze")
    url = f"https://embed.waze.com/iframe?zoom={zoom}&lat={lat}&lon={lon}&ct=livemap"
    components.html(f'<iframe src="{url}" width="100%" height="560" style="border:0;border-radius:20px" '
                    f'allowfullscreen loading="lazy"></iframe>', height=570)
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
        email, senha = st.secrets["FOGOCRUZADO_EMAIL"], st.secrets["FOGOCRUZADO_SENHA"]
    except Exception:  # noqa: BLE001
        st.markdown(
            '<div class="glass"><b>Camada desativada</b><br><span style="opacity:.75">Ela usa a API pública do '
            '<a href="https://fogocruzado.org.br" target="_blank">Fogo Cruzado</a> (tiroteios na Região Metropolitana do Rio), '
            'que exige cadastro gratuito. Adicione <code>FOGOCRUZADO_EMAIL</code> e <code>FOGOCRUZADO_SENHA</code> '
            'em <i>Settings → Secrets</i> do app para ativar.</span></div>', unsafe_allow_html=True)
        st.caption("Não exibimos “mapa de facções” nem rótulos de “zonas perigosas”: não há fonte oficial confiável e isso estigmatiza moradores.")
        return
    try:
        dias = st.select_slider("Período", [1, 3, 7, 15, 30], value=7, format_func=lambda d: f"{d} dia(s)")
        ocs = data.tiroteios(email, senha, "RJ", dias)
    except Exception as e:  # noqa: BLE001
        st.warning("Não foi possível consultar o Fogo Cruzado agora (verifique as credenciais nos secrets).")
        st.caption(str(e))
        return
    k = st.columns(3)
    with k[0]:
        style.kpi("💥", "Ocorrências", str(len(ocs)), "", f"Últimos {dias} dia(s)")
    with k[1]:
        style.kpi("🚓", "Com ação policial", str(sum(o["policia"] for o in ocs)))
    with k[2]:
        style.kpi("⚠️", "Com mortes", str(sum(1 for o in ocs if o["mortos"])))
    st.write("")
    m = mapa_base(lat, lon, 10)
    for o in ocs:
        folium.CircleMarker([o["lat"], o["lon"]], radius=6, color="#f87171", fill=True, fill_opacity=.6,
                            tooltip=f'{o["data"][:16].replace("T", " ")} · {o["bairro"] or o["cidade"]}<br>{o["endereco"]}').add_to(m)
    st_folium(m, height=520, width="stretch", returned_objects=[], key="mapa-seg")
    st.caption("Fonte: Fogo Cruzado (fogocruzado.org.br). Dados registrados e verificados pela organização; podem ter atraso.")
