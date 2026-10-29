# 🌊 Rio ao Vivo

Painel meteorológico em tempo real feito com **Streamlit** — visual glassmorphism escuro, gráficos interativos Plotly e mapa Folium com radar de chuva ao vivo.

**Recursos:** temperatura e condição atual · previsão 48 h / 7 dias · umidade · vento (direção, rajadas, rosa dos ventos) · precipitação · pressão · UV · qualidade do ar · nascer/pôr do sol e trajetória solar · fase da lua · maré e ondas · avisos INMET/Defesa Civil · mapa com radar, satélite e temperaturas por cidade.

## Abas extras
🚦 Trânsito (Waze) · ⛈️ Alagamentos (estações Alerta Rio + deslizamentos GeoRio) · 🛡️ Segurança (Fogo Cruzado, opcional).
Segredos opcionais: veja `.streamlit/secrets.toml.example`.

## Rodar localmente
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy no Streamlit Community Cloud
1. Faça push deste repositório para o GitHub.
2. Em [share.streamlit.io](https://share.streamlit.io) → **New app** → escolha o repositório, branch e `app.py` como *Main file*.
3. Não há chaves/segredos: todas as fontes são APIs públicas e gratuitas.

## Fontes de dados
Open-Meteo (previsão, marinho, qualidade do ar) · RainViewer (radar) · INMET via RadarMeteorológico (avisos — radarmeteorologico.com.br/api-publica) · Esri/OpenStreetMap (mapas).
A maré é uma estimativa do modelo global; para navegação use a Tábua de Marés da Marinha (DHN).
