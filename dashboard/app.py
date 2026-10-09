"""
Dashboard de test - Risques naturels et climat à Bordeaux Métropole.

Lancement (depuis la racine du projet) :
    .venv\\Scripts\\python.exe dashboard\\app.py
puis ouvrir http://127.0.0.1:8050
"""

from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dash import Dash, html, dcc, callback, clientside_callback, Input, Output, State, no_update

# ---------------------------------------------------------------------------
# Données
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).resolve().parent.parent / "notebook"
CODES = {"code_commune": str, "departement": str, "epci": str}


def load(name, **kwargs):
    return pd.read_csv(DATA_DIR / f"{name}.csv", encoding="utf-8-sig", **kwargs)


climat = load("climat_annuel")
episodes = load("episodes_par_annee")
benchmark = load("benchmark")
heatmap = load("heatmap_communes", dtype=CODES)

TYPES = ["Inondations", "Sécheresse / argiles", "Tempêtes", "Mouvements de terrain", "Autres"]
PATTERNS = {"Inondations": "/", "Sécheresse / argiles": ".", "Tempêtes": "\\",
            "Mouvements de terrain": "x", "Autres": "+"}

INDICATEURS = {
    "TX": ("Température maximale moyenne", "°C"),
    "NBJTX30": ("Jours de forte chaleur (≥ 30 °C)", "jours"),
    "NBJTX35": ("Jours de canicule (≥ 35 °C)", "jours"),
    "NBJTNS20": ("Nuits tropicales (min. ≥ 20 °C)", "nuits"),
    "RR": ("Pluviométrie annuelle", "mm"),
    "ETP": ("Évapotranspiration potentielle", "mm"),
    "bilan_hydrique": ("Bilan hydrique (pluie − ETP)", "mm"),
    "NBJRR30": ("Jours de forte pluie (≥ 30 mm)", "jours"),
    "NBJRR50": ("Jours de très forte pluie (≥ 50 mm)", "jours"),
}

_bm = benchmark.query("territoire == 'Bordeaux Métropole'").iloc[0]
_fr = benchmark.query("niveau == 'France'").iloc[0]

YEAR_MIN, YEAR_MAX = int(climat.annee.min()), int(climat.annee.max())
EP_MIN, EP_MAX = int(episodes.annee.min()), int(episodes.annee.max())

# ---------------------------------------------------------------------------
# Thèmes (palette catégorielle validée : bleu, orange, aqua, jaune + gris "Autres")
# ---------------------------------------------------------------------------
THEMES = {
    "clair": dict(
        surface="#ffffff", text="#111827", muted="#6b7280", grid="#e5e7eb",
        accent="#2a78d6", ref="#6f6e69", neutral="#c9c8c2",
        series=dict(zip(TYPES, ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#8a8984"])),
        ramp=["#f0f5fc", "#9ec5f4", "#3987e5", "#1c5cab", "#0d366b"],
    ),
    "sombre": dict(
        surface="#1e293b", text="#f1f5f9", muted="#94a3b8", grid="#334155",
        accent="#3987e5", ref="#a3a29b", neutral="#5c5b57",
        series=dict(zip(TYPES, ["#3987e5", "#d95926", "#199e70", "#c98500", "#8f8e88"])),
        ramp=["#24272c", "#184f95", "#3987e5", "#86b6ef", "#cde2fb"],
    ),
    "contraste": dict(
        surface="#ffffff", text="#000000", muted="#000000", grid="#595959",
        accent="#0d366b", ref="#000000", neutral="#8a8a8a",
        series=dict(zip(TYPES, ["#1c5cab", "#c24a1c", "#0f7a54", "#a36f00", "#5c5b57"])),
        ramp=["#ffffff", "#9ec5f4", "#2a78d6", "#104281", "#000000"],
    ),
}
DEFAULT_PREFS = {"theme": "clair", "scale": 1.0, "patterns": False, "labels": False, "font": False}


def get_prefs(prefs):
    p = {**DEFAULT_PREFS, **(prefs or {})}
    if p["theme"] == "contraste":
        p["patterns"] = True
    p["t"] = THEMES.get(p["theme"], THEMES["clair"])
    return p


# ---------------------------------------------------------------------------
# Utilitaires
# ---------------------------------------------------------------------------
def fr(x, dec=0):
    """Format nombre à la française (espace fine insécable, virgule décimale)."""
    s = f"{x:,.{dec}f}"
    return s.replace(",", " ").replace(".", ",")


def style_fig(fig, p, height=420, legend=True):
    t, size = p["t"], 14 * p["scale"]
    fig.update_layout(
        height=int(height * min(p["scale"], 1.3)),
        paper_bgcolor=t["surface"], plot_bgcolor=t["surface"],
        font=dict(family="Atkinson Hyperlegible, Verdana, sans-serif" if p["font"]
                  else "Inter, Segoe UI, Arial, sans-serif", size=size, color=t["text"]),
        separators=", ",
        margin=dict(l=10, r=20, t=50 if legend else 20, b=10),
        hoverlabel=dict(font_size=size + 1, bgcolor=t["surface"], font_color=t["text"],
                        bordercolor=t["muted"]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0.5, xanchor="center", title_text="",
                    font_color=t["text"], traceorder="normal", itemsizing="constant"),
        showlegend=legend,
        barcornerradius=4,
    )
    axis = dict(gridcolor=t["grid"], zerolinecolor=t["grid"], showline=False, ticks="",
                tickfont_color=t["muted"], title_font_color=t["muted"], automargin=True)
    fig.update_xaxes(**axis, showgrid=False)
    fig.update_yaxes(**axis, griddash="dot")
    return fig


# Encodage secondaire des types de risque (forme du point, style de trait) : jamais la couleur seule.
SYMBOLS = {"Inondations": "circle", "Sécheresse / argiles": "square", "Tempêtes": "diamond",
           "Mouvements de terrain": "triangle-up", "Autres": "x"}
DASHES = {"Inondations": "solid", "Sécheresse / argiles": "dash", "Tempêtes": "dot",
          "Mouvements de terrain": "dashdot", "Autres": "longdash"}


def line_style(risk, p, width=2.5, size=7):
    t = p["t"]
    return dict(line=dict(color=t["series"][risk], width=width, dash=DASHES[risk] if p["patterns"] else "solid",
                          shape="linear"),
                marker=dict(symbol=SYMBOLS[risk], size=size, color=t["series"][risk],
                            line=dict(color=t["surface"], width=1.5)))


def bar_marker(risk, p):
    t = p["t"]
    m = dict(color=t["series"][risk], line=dict(color=t["surface"], width=1))
    if p["patterns"]:
        m["pattern"] = dict(shape=PATTERNS[risk], fgcolor=t["text"] if p["theme"] == "contraste" else t["surface"],
                            solidity=0.35, size=8)
    return m


def html_table(df, caption):
    """Tableau HTML accessible (caption + en-têtes avec scope)."""
    def cell(v):
        return fr(v, 2 if v % 1 else 0) if isinstance(v, (int, float, np.number)) else v

    head = html.Tr([html.Th(c, scope="col") for c in df.columns])
    rows = [html.Tr([html.Th(cell(r[0]), scope="row")] + [html.Td(cell(v)) for v in r[1:]])
            for r in df.itertuples(index=False)]
    return html.Div(html.Table([html.Caption(caption), html.Thead(head), html.Tbody(rows)],
                               className="data-table"), className="table-wrap", tabIndex=0,
                    role="region", **{"aria-label": caption})


def empty_fig(p, msg):
    fig = go.Figure()
    fig.add_annotation(text=msg, showarrow=False, font_size=16 * p["scale"])
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return style_fig(fig, p, height=250, legend=False)


def fieldset(legend, component):
    return html.Fieldset([html.Legend(legend), component], className="control")


def labelled(label, cid, component):
    return html.Div([html.Label(label, htmlFor=cid), component], className="control")


def types_checklist(cid):
    return fieldset("Types de risque", dcc.Checklist(
        id=cid, options=TYPES, value=TYPES, inline=True, className="choices"))


def detail_body(cid, title, question, controls, note=None):
    """Contenu complet d'une fenêtre de détail : filtres, graphe, résumé, données."""
    return [
        html.P(question, className="question"),
        html.Div(controls, className="controls", role="group", **{"aria-label": f"Filtres : {title}"}),
        html.Div(dcc.Graph(id=f"{cid}-graph", config=GRAPH_CONFIG),
                 **{"aria-describedby": f"{cid}-summary"}),
        html.P(id=f"{cid}-summary", className="summary", **{"aria-live": "polite"}),
        html.P(note, className="note") if note else None,
        html.Div([
            html.Button("Télécharger les données (Excel)", id=f"{cid}-xlsx", type="button", className="btn-export",
                        **{"aria-describedby": f"{cid}-xlsx-hint"}),
            html.Span("Fichier .xlsx avec les valeurs affichées et les filtres actuels.",
                      id=f"{cid}-xlsx-hint", className="note"),
            dcc.Download(id=f"{cid}-download"),
            dcc.Store(id=f"{cid}-store"),
        ], className="data-actions"),
        html.Details([html.Summary("Afficher les données sous forme de tableau"),
                      html.Div(id=f"{cid}-table")]),
    ]


def dialog(cid, title, children):
    """Fenêtre modale native (<dialog>) : focus piégé, Échap pour fermer, retour du focus."""
    return html.Dialog([
        html.Div([
            html.H2(title, id=f"dlg-{cid}-title"),
            html.Button("Fermer ✕", type="button", className="dialog-close", **{"data-dialog-close": ""}),
        ], className="dialog-head"),
        html.Div(children, className="dialog-body"),
    ], id=f"dlg-{cid}", className="dialog", **{"aria-labelledby": f"dlg-{cid}-title"})


def tile(cid, title):
    """Visuel du rapport : titre-bouton (ouvre le détail), mini-graphique décoratif, résumé pour lecteurs d'écran."""
    return html.Article([
        html.Div([
            html.H3(html.Button([title, html.Span(" - ouvrir le détail", className="sr-only")],
                                type="button", className="tile-open",
                                **{"data-dialog-open": f"dlg-{cid}", "aria-haspopup": "dialog",
                                   "aria-controls": f"dlg-{cid}"})),
            html.Span("⤢", className="focus-icon", title="Mode focus", **{"aria-hidden": "true"}),
        ], className="tile-head"),
        html.P(id=f"{cid}-sub", className="tile-sub"),
        html.P(id=f"{cid}-short", className="sr-only"),
        html.Div(dcc.Graph(id=f"{cid}-mini", config=MINI_CONFIG, responsive=True, style={"height": "100%"}),
                 className="tile-viz", **{"aria-hidden": "true"}),
    ], className="tile")


GRAPH_CONFIG = {
    "displaylogo": False,
    "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"],
    "toImageButtonOptions": {"format": "png", "scale": 2},
}
MINI_CONFIG = {"staticPlot": True, "displayModeBar": False}

# ---------------------------------------------------------------------------
# Application et mise en page
# ---------------------------------------------------------------------------
app = Dash(__name__, title="Risques naturels - Bordeaux Métropole", external_stylesheets=[
    "https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:wght@300;500"
    "&family=Inter:wght@400;500;600;700&display=swap"])

app.index_string = app.index_string.replace("<html>", '<html lang="fr">')

a11y_dialog = dialog("a11y", "Options d'accessibilité", html.Div([
    fieldset("Thème", dcc.RadioItems(
        id="a11y-theme", value="clair", className="choices", persistence=True,
        persistence_type="local", options=[
            {"label": "Automatique (suit le système)", "value": "auto"},
            {"label": "Clair", "value": "clair"},
            {"label": "Sombre", "value": "sombre"},
            {"label": "Contraste élevé", "value": "contraste"}])),
    fieldset("Taille du texte", dcc.RadioItems(
        id="a11y-size", value=1.0, className="choices", persistence=True,
        persistence_type="local", options=[
            {"label": "Normale", "value": 1.0}, {"label": "Grande (125 %)", "value": 1.25},
            {"label": "Très grande (150 %)", "value": 1.5}])),
    fieldset("Lecture", dcc.Checklist(
        id="a11y-options", value=[], className="choices", persistence=True,
        persistence_type="local", options=[
            {"label": "Motifs sur les couleurs (daltonisme, impression N&B)", "value": "patterns"},
            {"label": "Afficher les valeurs sur les graphiques", "value": "labels"},
            {"label": "Police très lisible (Atkinson Hyperlegible)", "value": "font"},
            {"label": "Espacement du texte augmenté (dyslexie)", "value": "spacing"},
            {"label": "Réduire les animations", "value": "motion"}])),
    html.P("Astuce : chaque vignette s'ouvre avec Entrée ou Espace et se ferme avec Échap. "
           "Chaque graphique propose ses données sous forme de tableau.", className="note"),
], className="controls a11y-controls"))

CLIMAT_OPTIONS = [{"label": f"{v[0]} ({v[1]})", "value": k} for k, v in INDICATEURS.items()]

dialogs = [
    dialog("evol", "Fréquence des catastrophes naturelles dans la métropole", detail_body(
        "evol", "Évolution des catastrophes",
        "Quels risques reviennent, et se multiplient-ils ? (épisodes CatNat, 28 communes, 1982-2022)",
        [types_checklist("evol-types"),
         fieldset("Regroupement", dcc.RadioItems(
             id="evol-grain", value="decennie", inline=True, className="choices",
             options=[{"label": "Par décennie (moyenne par an)", "value": "decennie"},
                      {"label": "Par année", "value": "annee"}])),
         labelled("Indicateur climatique à comparer (graphique dessous)", "evol-climat", dcc.Dropdown(
             id="evol-climat", value="none", clearable=False,
             options=[{"label": "Aucun", "value": "none"}] + CLIMAT_OPTIONS))])),
    dialog("heat", "Exposition des 28 communes de la métropole par type de risque", detail_body(
        "heat", "Communes par type de risque",
        "Quelle commune est touchée par quel risque ? (nombre d'arrêtés CatNat 1982-2022)",
        [types_checklist("heat-types"),
         fieldset("Valeur affichée", dcc.RadioItems(
             id="heat-mode", value="count", inline=True, className="choices",
             options=[{"label": "Nombre d'arrêtés", "value": "count"},
                      {"label": "Part dans la commune (%)", "value": "share"}])),
         labelled("Trier les communes par", "heat-sort", dcc.Dropdown(
             id="heat-sort", value="total", clearable=False,
             options=[{"label": "Total des types sélectionnés", "value": "total"},
                      {"label": "Ordre alphabétique", "value": "alpha"}]
             + [{"label": t, "value": t} for t in TYPES])),
         labelled("Limiter à certaines communes (vide = toutes)", "heat-communes", dcc.Dropdown(
             id="heat-communes", multi=True, placeholder="Toutes les communes",
             options=sorted(heatmap.libelle_geographique)))])),
    dialog("clim", "Évolution du climat en Gironde", detail_body(
        "clim", "Indicateur climatique",
        "Le climat se réchauffe-t-il ? Les sécheresses et les pluies extrêmes évoluent-elles ?",
        [labelled("Indicateur (température, pluviométrie...)", "clim-ind", dcc.Dropdown(
            id="clim-ind", value="NBJTX30", clearable=False, options=CLIMAT_OPTIONS)),
         fieldset("Affichage", dcc.Checklist(
             id="clim-opts", value=["mm10"], inline=True, className="choices",
             options=[{"label": "Moyenne mobile 10 ans", "value": "mm10"},
                      {"label": "Tendance linéaire", "value": "trend"}])),
         fieldset("Regroupement", dcc.RadioItems(
             id="clim-grain", value="annee", inline=True, className="choices",
             options=[{"label": "Par année", "value": "annee"},
                      {"label": "Moyenne par décennie", "value": "decennie"}]))])),
    dialog("scat", "Lien entre climat et catastrophes naturelles", detail_body(
        "scat", "Climat et catastrophes",
        "Relation exploratoire entre un indicateur climatique et les épisodes CatNat d'un type (une année = un point).",
        [labelled("Indicateur climatique (axe horizontal)", "scat-x", dcc.Dropdown(
            id="scat-x", value="NBJTX30", clearable=False, options=CLIMAT_OPTIONS)),
         labelled("Type de catastrophe (axe vertical)", "scat-y", dcc.Dropdown(
             id="scat-y", value="Sécheresse / argiles", clearable=False, options=TYPES))],
        note="Corrélation exploratoire sur environ 40 années : elle ne prouve pas un lien de cause à effet.")),
]

app.layout = html.Div([
    html.A("Aller aux graphiques", href="#graphiques", className="skip-link"),
    dcc.Store(id="prefs"),
    html.Header([
        html.Div(className="topbar-side", **{"aria-hidden": "true"}),
        html.H1("Risques naturels et climat à Bordeaux Métropole"),
        html.Div([html.Div([
            html.Span("Période", id="periode-label", className="slicer-label"),
            html.Div(dcc.RangeSlider(
                id="periode", min=YEAR_MIN, max=YEAR_MAX, step=1, value=[YEAR_MIN, YEAR_MAX], marks={},
                tooltip={"placement": "bottom"}, allowCross=False, className="slicer-range",
            ), className="slicer"),
        ], className="periode", role="group", **{"aria-labelledby": "periode-label"}),
        html.Button("Accessibilité", type="button", className="btn",
                    **{"data-dialog-open": "dlg-a11y", "aria-haspopup": "dialog", "aria-controls": "dlg-a11y"}),
        ], className="topbar-side topbar-right"),
    ], className="topbar"),
    html.Section([
        html.H2("Indicateurs clés", className="sr-only"),
        html.Div(id="kpis", className="kpi-grid"),
    ], className="kpi-band", **{"aria-label": "Indicateurs clés"}),
    html.Main([
        html.H2("Graphiques - sélectionner un visuel pour afficher le détail", className="sr-only"),
        html.Div([
            tile("heat", "Communes les plus exposées par type de risque"),
            tile("clim", "Évolution du climat en Gironde"),
            tile("evol", "Fréquence des catastrophes naturelles"),
            tile("scat", "Lien entre climat et catastrophes naturelles"),
        ], className="tile-grid"),
    ], id="graphiques", tabIndex=-1),
    html.Footer([
        html.Span(id="periode-text", **{"aria-live": "polite"}),
        html.Span(" Sources : arrêtés CatNat (data.gouv.fr, 1982-2022), Météo-France Gironde 1950-2024."),
    ]),
    *dialogs,
    a11y_dialog,
], className="app")

# ---------------------------------------------------------------------------
# Préférences d'accessibilité (côté navigateur)
# ---------------------------------------------------------------------------
clientside_callback(
    """
    function(theme, size, options) {
        options = options || [];
        let eff = theme;
        if (theme === 'auto') {
            const mq = q => window.matchMedia && window.matchMedia(q).matches;
            eff = mq('(prefers-contrast: more)') || mq('(forced-colors: active)') ? 'contraste'
                : mq('(prefers-color-scheme: dark)') ? 'sombre' : 'clair';
        }
        const root = document.documentElement;
        root.dataset.theme = eff;
        root.style.fontSize = (100 * size) + '%';
        root.classList.toggle('scaled', size > 1);
        root.classList.toggle('readable-font', options.includes('font'));
        root.classList.toggle('wide-spacing', options.includes('spacing'));
        const motion = options.includes('motion') ||
            (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
        root.classList.toggle('reduce-motion', motion);
        return {theme: eff, scale: size, patterns: options.includes('patterns'),
                labels: options.includes('labels'), font: options.includes('font')};
    }
    """,
    Output("prefs", "data"),
    Input("a11y-theme", "value"), Input("a11y-size", "value"), Input("a11y-options", "value"),
)


def clip_years(df, periode):
    return df[(df.annee >= periode[0]) & (df.annee <= periode[1])]


def mini_fig(fig):
    """Version vignette d'une figure : compacte, sans titres d'axes ni barre d'échelle."""
    m = go.Figure(fig)
    legend = m.layout.showlegend is not False
    m.update_layout(height=None, autosize=True, hovermode=False, font_size=10,
                    margin=dict(l=4, r=8, t=22 if legend else 4, b=4),
                    legend=dict(font_size=10, y=1, yanchor="bottom"))
    m.update_xaxes(title_text=None)
    m.update_yaxes(title_text=None)
    m.update_traces(showscale=False, texttemplate=None, selector=dict(type="heatmap"))
    m.update_traces(marker_showscale=False, selector=dict(type="scatter"))
    m.update_traces(mode="markers", selector=dict(mode="markers+text"))
    m.update_traces(textposition="none", selector=dict(type="bar"))
    if any(t.type == "heatmap" for t in m.data):
        m.update_yaxes(tickfont_size=8)
    return m


def tile_layout(fig, p, legend=False):
    """Mise en forme d'une vue « lecture rapide » de vignette : grands caractères, marges serrées."""
    style_fig(fig, p, legend=legend)
    fig.update_layout(height=None, autosize=True, hovermode=False, font_size=12 * p["scale"],
                      margin=dict(l=4, r=16, t=26 if legend else 6, b=4),
                      legend=dict(font_size=11 * p["scale"], y=1, yanchor="bottom", x=0.5, xanchor="center"))
    return fig


def detail_callback(cid, *inputs):
    """Un callback de graphique alimente la fenêtre de détail ET la vignette.

    La fonction renvoie (figure, résumé, tableau, figure_vignette, sous_titre) ; sans figure de
    vignette, une version compacte de la figure de détail est utilisée.
    """
    def deco(fn):
        @callback(Output(f"{cid}-graph", "figure"), Output(f"{cid}-mini", "figure"),
                  Output(f"{cid}-summary", "children"), Output(f"{cid}-short", "children"),
                  Output(f"{cid}-table", "children"), Output(f"{cid}-sub", "children"),
                  Output(f"{cid}-store", "data"), *inputs)
        def wrapper(*args):
            fig, summary, table, mini, sub = (list(fn(*args)) + [None, ""])[:5]
            store = None
            if isinstance(table, tuple):
                df, caption = table
                store = {"caption": caption, "columns": list(df.columns),
                         "rows": df.astype(object).where(df.notna(), None).values.tolist()}
                table = html_table(df, caption)
            return fig, mini if mini is not None else mini_fig(fig), summary, summary, table, sub, store

        @callback(Output(f"{cid}-download", "data"), Input(f"{cid}-xlsx", "n_clicks"),
                  State(f"{cid}-store", "data"), prevent_initial_call=True)
        def download(_, store):
            return excel_download(store, EXPORT_NAMES[cid]) if store else no_update
        return fn
    return deco


EXPORT_NAMES = {
    "heat": "communes_par_type_de_risque",
    "clim": "evolution_climat_gironde",
    "evol": "frequence_catastrophes_metropole",
    "scat": "lien_climat_catastrophes",
}
SOURCES = "Arrêtés CatNat (data.gouv.fr, 1982-2022) ; Météo-France, données mensuelles Gironde 1950-2024"


def excel_download(store, name):
    """Fichier Excel : feuille « Données » (colonnes ajustées) + feuille « Description »."""
    df = pd.DataFrame(store["rows"], columns=store["columns"])
    info = pd.DataFrame({"Information": ["Contenu", "Sources", "Exporté le"],
                         "Valeur": [store["caption"], SOURCES, date.today().strftime("%d/%m/%Y")]})

    def write(buffer):
        with pd.ExcelWriter(buffer, engine="openpyxl") as xw:
            for sheet, data in (("Données", df), ("Description", info)):
                data.to_excel(xw, sheet_name=sheet, index=False)
                ws = xw.sheets[sheet]
                ws.freeze_panes = "A2"
                for col in ws.columns:
                    width = max(len(str(c.value)) if c.value is not None else 0 for c in col)
                    ws.column_dimensions[col[0].column_letter].width = min(width + 2, 80)

    return dcc.send_bytes(write, f"{name}_{date.today():%Y%m%d}.xlsx")


# ---------------------------------------------------------------------------
# KPI
# ---------------------------------------------------------------------------
def kpi(label, value, sub=None):
    """Carte KPI : libellé lu en premier par les lecteurs d'écran, valeur affichée au-dessus (CSS)."""
    return html.Div([html.P(label, className="kpi-label"), html.P(value, className="kpi-value"),
                     html.P(sub, className="kpi-sub") if sub else None], className="kpi")


def signed(x, dec=0):
    return f"{'+' if x >= 0 else '−'}{fr(abs(x), dec)}"


@callback(Output("kpis", "children"), Output("periode-text", "children"), Input("periode", "value"))
def update_kpis(periode):
    y0, y1 = periode
    cards = []

    clim = clip_years(climat, periode)
    if y1 - y0 + 1 >= 20:
        first = clim[clim.annee < y0 + 10].NBJTX30.mean()
        last = clim[clim.annee > y1 - 10].NBJTX30.mean()
        diff = last - first
        cards.append(kpi(f"Jours ≥ 30 °C / an : {y1 - 9}-{y1} vs {y0}-{y0 + 9}",
                         f"{signed(diff, 1)} j"))
    else:
        cards.append(kpi("Jours ≥ 30 °C / an (période ≥ 20 ans requise)", "-"))

    ep = clip_years(episodes, periode)
    if len(ep):
        totaux = ep[TYPES].sum()
        y_a, y_b = int(ep.annee.min()), int(ep.annee.max())
        par_decennie = totaux.sum() / ((y_b - y_a + 1) / 10)
        cards.append(kpi(f"Épisodes CatNat {y_a}-{y_b} (≈ {fr(par_decennie)} / décennie)", fr(totaux.sum())))
        top = totaux.idxmax()
        cards.append(kpi(f"Risque dominant ({fr(totaux[top] / totaux.sum() * 100)} % des épisodes)", top))
    else:
        cards.append(kpi("Épisodes CatNat (données 1982-2022)", "-"))
        cards.append(kpi("Risque dominant", "-"))

    ratio = _bm.arretes_par_commune / _fr.arretes_par_commune
    cards.append(kpi("Arrêtés par commune : métropole vs France", f"× {fr(ratio, 1)}",
                     f"{fr(_bm.arretes_par_commune, 1)} contre {fr(_fr.arretes_par_commune, 1)}"))

    c = heatmap.loc[heatmap.nb_arretes.idxmax()]
    risk = c[TYPES].astype(float).idxmax()
    cards.append(kpi(f"Commune la plus touchée · {risk.lower()}", c.libelle_geographique))

    note = f"Période {y0}-{y1} appliquée au climat et aux épisodes CatNat ; communes et benchmark : 1982-2022."
    return cards, note


# ---------------------------------------------------------------------------
# Graphique : évolution des épisodes dans la métropole
# ---------------------------------------------------------------------------
def by_decade(df, cols, how="sum"):
    g = df.assign(periode=(df.annee // 10 * 10)).groupby("periode")
    out = (g[cols].sum() if how == "sum" else g[cols].mean()).reset_index()
    out["x"] = [f"{a}-{b}" for a, b in zip(g.annee.min(), g.annee.max())]
    return out


@detail_callback("evol",
          Input("evol-types", "value"), Input("evol-grain", "value"), Input("evol-climat", "value"),
          Input("periode", "value"), Input("prefs", "data"))
def update_evol(types, grain, clim_ind, periode, prefs):
    p = get_prefs(prefs)
    types = [t for t in TYPES if t in (types or [])]
    ep = clip_years(episodes, periode)
    if not types or ep.empty:
        return empty_fig(p, "Aucune donnée : sélectionner au moins un type et une période entre 1982 et 2022."), "", ""

    if grain == "decennie":
        data = by_decade(ep, types, "mean")
    else:
        data = ep[["annee"] + types].assign(x=ep.annee)
    fmt = ".1f" if grain == "decennie" else ""

    with_clim = clim_ind != "none"
    fig = make_subplots(rows=2 if with_clim else 1, cols=1, shared_xaxes=True,
                        row_heights=[0.65, 0.35] if with_clim else [1], vertical_spacing=0.08)
    for t in types:
        fig.add_scatter(x=data.x, y=data[t], name=t, mode="lines+markers+text" if p["labels"] else "lines+markers",
                        **line_style(t, p), row=1, col=1, text=data[t].where(data[t] > 0) if p["labels"] else None,
                        textposition="top center",
                        hovertemplate=f"{t} : %{{y:{fmt}}}<extra></extra>")
    fig.update_layout(hovermode="x unified")
    fig.update_yaxes(title_text="Épisodes par an (moyenne)" if grain == "decennie" else "Épisodes",
                     rangemode="tozero", row=1, col=1)
    if grain == "decennie":
        fig.update_xaxes(type="category")

    if with_clim:
        label, unit = INDICATEURS[clim_ind]
        cl = clip_years(climat, [max(periode[0], EP_MIN), min(periode[1], EP_MAX)])
        cl = by_decade(cl, [clim_ind], "mean") if grain == "decennie" else cl.assign(x=cl.annee)
        fig.add_scatter(x=cl.x, y=cl[clim_ind], name=label, mode="lines+markers", row=2, col=1,
                        line=dict(color=p["t"]["text"], width=2), marker=dict(size=8),
                        hovertemplate=f"<b>{label}</b><br>%{{x}} : %{{y:.1f}} {unit}<extra></extra>")
        fig.update_yaxes(title_text=unit, row=2, col=1)
        if clim_ind == "bilan_hydrique":
            fig.add_hline(y=0, line_color=p["t"]["muted"], line_dash="dash", row=2, col=1)
    style_fig(fig, p, height=560 if with_clim else 440)

    totals = data[types].sum(axis=1)
    rec = data.loc[totals.idxmax()]
    sums = ep[types].sum()
    pic = (f"{fr(totals.max(), 1)} épisodes par an en moyenne" if grain == "decennie"
           else f"{fr(totals.max())} épisodes")
    summary = (f"{fr(sums.sum())} épisodes sur la période. Type le plus fréquent : {sums.idxmax()} "
               f"({fr(sums.max())}). Pic : {rec.x} avec {pic}.")
    table = data[["x"] + types].round(2).rename(columns={"x": "Décennie" if grain == "decennie" else "Année"})

    # Vignette : une courbe par type, moyenne d'épisodes par an sur chaque décennie
    # (comparable même pour les décennies incomplètes 1982-89 et 2020-22).
    g = ep.groupby(ep.annee // 10 * 10)
    dec = g[types].mean()
    labels = [f"{a}-{str(b)[2:]}" for a, b in zip(g.annee.min(), g.annee.max())]
    mini = go.Figure()
    for t in types:
        mini.add_scatter(x=labels, y=dec[t], name=t, mode="lines+markers", **line_style(t, p, width=3, size=9))
    mini.update_xaxes(type="category")
    mini.update_yaxes(rangemode="tozero")
    tile_layout(mini, p, legend=True)
    sub = "Épisodes par an (moyenne de chaque décennie), par type de risque"
    return fig, summary, (table, "Épisodes CatNat par période et par type"), mini, sub


# ---------------------------------------------------------------------------
# Graphique : heatmap des communes
# ---------------------------------------------------------------------------
@detail_callback("heat",
          Input("heat-types", "value"), Input("heat-mode", "value"), Input("heat-sort", "value"),
          Input("heat-communes", "value"), Input("prefs", "data"))
def update_heat(types, mode, sort, selection, prefs):
    p = get_prefs(prefs)
    types = [t for t in TYPES if t in (types or [])]
    df = heatmap if not selection else heatmap[heatmap.libelle_geographique.isin(selection)]
    if not types or df.empty:
        return empty_fig(p, "Sélectionner au moins un type de risque."), "", ""

    df = df.set_index("libelle_geographique")[types].copy()
    df["Total"] = df.sum(axis=1)
    top10 = df.nlargest(10, "Total").iloc[::-1]
    if sort == "alpha":
        df = df.sort_index(ascending=False)
    else:
        df = df.sort_values("Total" if sort == "total" or sort not in types else sort)
    values = df[types].div(df.Total.replace(0, np.nan), axis=0) * 100 if mode == "share" else df[types]
    unit = "%" if mode == "share" else "arrêtés"

    t = p["t"]
    fig = go.Figure(go.Heatmap(
        z=values.values, x=types, y=values.index, xgap=2, ygap=2,
        colorscale=[[i / (len(t["ramp"]) - 1), c] for i, c in enumerate(t["ramp"])],
        texttemplate="%{z:.0f}", textfont_size=12 * p["scale"],
        colorbar=dict(title=dict(text=unit, font_color=t["text"]), tickfont_color=t["text"]),
        hovertemplate="<b>%{y}</b><br>%{x} : %{z:.0f} " + unit + "<extra></extra>"))
    fig.update_xaxes(side="top", showgrid=False)
    fig.update_yaxes(showgrid=False)
    style_fig(fig, p, height=max(320, 26 * len(df) + 80), legend=False)

    top = df.Total.idxmax()
    best = df[types].stack().idxmax()
    summary = (f"{len(df)} communes affichées. Commune la plus touchée (types sélectionnés) : {top} "
               f"({fr(df.Total.max())} arrêtés). Combinaison la plus forte : {best[0]}, {best[1].lower()} "
               f"({fr(df[types].stack().max())} arrêtés).")
    table = values.round(1).reset_index().rename(columns={"libelle_geographique": "Commune"}).iloc[::-1]

    # Vignette : les 10 communes les plus touchées, barres empilées par type et total écrit.
    mini = go.Figure()
    for r in types:
        mini.add_bar(y=top10.index, x=top10[r], name=r, orientation="h", marker=bar_marker(r, p))
    mini.add_scatter(y=top10.index, x=top10.Total, mode="text", text=[fr(v) for v in top10.Total],
                     textposition="middle right", showlegend=False, cliponaxis=False,
                     textfont=dict(size=12 * p["scale"], color=t["text"], weight="bold"))
    mini.update_layout(barmode="stack", barcornerradius=0, bargap=0.25)
    mini.update_xaxes(range=[0, top10.Total.max() * 1.12])
    tile_layout(mini, p, legend=True)
    mini.update_layout(legend=dict(orientation="v", x=1.02, xanchor="left", y=0.5, yanchor="middle"),
                       margin=dict(t=6))
    mini.update_yaxes(tickmode="array", tickvals=list(top10.index), tickfont_size=11 * p["scale"])
    sub = f"Arrêtés CatNat 1982-2022 · les {len(top10)} communes les plus touchées sur {len(df)}"
    return fig, summary, (table, f"Arrêtés par commune et par type ({unit})"), mini, sub


# ---------------------------------------------------------------------------
# Graphique : indicateur climatique
# ---------------------------------------------------------------------------
@detail_callback("clim",
          Input("clim-ind", "value"), Input("clim-opts", "value"), Input("clim-grain", "value"),
          Input("periode", "value"), Input("prefs", "data"))
def update_clim(ind, opts, grain, periode, prefs):
    p = get_prefs(prefs)
    t = p["t"]
    label, unit = INDICATEURS[ind]
    full = climat.assign(mm10=climat[ind].rolling(10).mean())
    df = clip_years(full, periode)
    opts = opts or []

    fig = go.Figure()
    if grain == "decennie":
        d = by_decade(df, [ind], "mean")
        fig.add_bar(x=d.x, y=d[ind], name=label, marker_color=t["accent"],
                    text=d[ind] if p["labels"] else None, texttemplate="%{y:.1f}", textposition="outside",
                    hovertemplate=f"%{{x}} : %{{y:.1f}} {unit}<extra></extra>")
        table = d[["x", ind]].rename(columns={"x": "Décennie", ind: f"{label} ({unit})"}).round(1)
    else:
        fig.add_scatter(x=df.annee, y=df[ind], name="Valeur annuelle", mode="lines+markers",
                        line=dict(color=t["accent"], width=2), marker=dict(size=7),
                        text=df[ind].round(1) if p["labels"] else None,
                        hovertemplate=f"%{{x}} : %{{y:.1f}} {unit}<extra></extra>")
        if "mm10" in opts:
            fig.add_scatter(x=df.annee, y=df.mm10, name="Moyenne mobile 10 ans", mode="lines",
                            line=dict(color=t["text"], width=3, dash="dash" if p["patterns"] else "solid"),
                            hovertemplate=f"%{{x}} : %{{y:.1f}} {unit} (moy. 10 ans)<extra></extra>")
        table = df[["annee", ind, "mm10", "nb_stations"]].round(1)
        table.columns = ["Année", f"{label} ({unit})", "Moyenne mobile 10 ans", "Nombre de stations"]
    slope = None
    if "trend" in opts and len(df) > 2:
        a, b = np.polyfit(df.annee, df[ind], 1)
        slope = a * 10
        xs = df.annee if grain == "annee" else None
        if xs is not None:
            fig.add_scatter(x=xs, y=a * xs + b, name="Tendance linéaire", mode="lines",
                            line=dict(color=t["ref"], width=2, dash="dot"), hoverinfo="skip")
    if ind == "bilan_hydrique":
        fig.add_hline(y=0, line_color=t["muted"], line_dash="dash",
                      annotation_text="0 : pluie = évapotranspiration", annotation_font_color=t["text"])
    fig.update_yaxes(title_text=f"{label} ({unit})")
    style_fig(fig, p, height=420)

    if df.empty:
        return fig, "Aucune donnée sur la période.", ""
    i_max = df[ind].idxmax()
    summary = (f"{label} : moyenne {fr(df[ind].mean(), 1)} {unit} entre {periode[0]} et {periode[1]}. "
               f"Maximum en {int(df.loc[i_max, 'annee'])} ({fr(df.loc[i_max, ind], 1)} {unit}).")
    if slope is not None:
        summary += f" Tendance : {'+' if slope >= 0 else '−'}{fr(abs(slope), 2)} {unit} par décennie."
    stations = f"Fiabilité : moyenne de {int(df.nb_stations.min())} à {int(df.nb_stations.max())} stations selon l'année."

    # Vignette : chaque année en barre pâle, moyenne sur 10 ans en trait fort avec valeurs de début et de fin.
    dec_fmt = 1 if unit == "°C" else 0
    mini = go.Figure()
    if grain == "decennie":
        mini.add_bar(x=d.x, y=d[ind], marker_color=t["accent"], text=[fr(v, dec_fmt) for v in d[ind]],
                     textposition="outside", cliponaxis=False)
        sub = f"{label} ({unit}) · moyenne par décennie"
    else:
        mini.add_bar(x=df.annee, y=df[ind], marker_color=t["accent"], opacity=0.35, name="Chaque année")
        ma = df.dropna(subset=["mm10"])
        mini.add_scatter(x=ma.annee, y=ma.mm10, mode="lines", name="Moyenne sur 10 ans",
                         line=dict(color=t["ramp"][3], width=4))
        for _, row in (ma.iloc[[0, -1]] if len(ma) else ma).iterrows():
            mini.add_annotation(x=row.annee, y=row.mm10, text=f"<b>{fr(row.mm10, dec_fmt)}</b>",
                                showarrow=False, yshift=14, font=dict(size=13 * p["scale"], color=t["text"]),
                                bgcolor=t["surface"])
        sub = f"{label} ({unit}) · barres : chaque année · trait : moyenne sur 10 ans"
    if ind == "bilan_hydrique":
        mini.add_hline(y=0, line_color=t["muted"])
    mini.update_layout(barcornerradius=1, bargap=0.15)
    tile_layout(mini, p)
    return fig, [summary, html.Br(), stations], (table, f"{label} par période"), mini, sub


# ---------------------------------------------------------------------------
# Graphique : nuage climat x catastrophes
# ---------------------------------------------------------------------------
lien = load("lien_climat_catastrophes")


@detail_callback("scat",
          Input("scat-x", "value"), Input("scat-y", "value"), Input("periode", "value"), Input("prefs", "data"))
def update_scat(x, y, periode, prefs):
    p = get_prefs(prefs)
    t = p["t"]
    df = clip_years(lien, periode)
    if len(df) < 3:
        return empty_fig(p, "Période trop courte (données communes 1982-2022)."), "", ""
    label, unit = INDICATEURS[x]
    fig = go.Figure(go.Scatter(
        x=df[x], y=df[y], mode="markers+text" if p["labels"] else "markers",
        text=df.annee, textposition="top center", textfont_size=10 * p["scale"],
        marker=dict(size=11, color=df.annee, colorscale=[[0, t["ramp"][1]], [1, t["ramp"][4]]],
                    line=dict(color=t["surface"], width=2),
                    colorbar=dict(title=dict(text="Année", font_color=t["text"]), tickfont_color=t["text"])),
        hovertemplate=f"<b>%{{text}}</b><br>{label} : %{{x:.1f}} {unit}<br>{y} : %{{y}} épisode(s)<extra></extra>"))
    r = df[x].corr(df[y])
    if df[x].nunique() > 1:
        a, b = np.polyfit(df[x], df[y], 1)
        xs = np.linspace(df[x].min(), df[x].max(), 50)
        fig.add_scatter(x=xs, y=a * xs + b, mode="lines", line=dict(color=t["ref"], dash="dot", width=2),
                        hoverinfo="skip", showlegend=False)
    fig.update_xaxes(title_text=f"{label} ({unit})")
    fig.update_yaxes(title_text=f"Épisodes : {y}")
    style_fig(fig, p, height=420, legend=False)

    force = "forte" if abs(r) >= 0.5 else "modérée" if abs(r) >= 0.3 else "faible"
    summary = (f"{len(df)} années. Corrélation {force} {'positive' if r >= 0 else 'négative'} "
               f"(r = {fr(r, 2)}) entre {label[0].lower() + label[1:]} et les épisodes « {y} ». "
               "Relation exploratoire, pas une preuve de cause.")
    table = df[["annee", x, y]].round(1)
    table.columns = ["Année", f"{label} ({unit})", f"Épisodes {y}"]

    # Vignette : nuage de points, droite de tendance et force du lien écrite en clair.
    mini = go.Figure(go.Scatter(
        x=df[x], y=df[y], mode="markers",
        marker=dict(size=11, color=t["accent"], opacity=0.8, line=dict(color=t["surface"], width=1.5))))
    if df[x].nunique() > 1:
        mini.add_scatter(x=xs, y=a * xs + b, mode="lines", line=dict(color=t["text"], dash="dash", width=2))
    mini.add_annotation(xref="paper", yref="paper", x=0.01, y=0.99, xanchor="left", yanchor="top",
                        showarrow=False, bgcolor=t["surface"], bordercolor=t["grid"], borderpad=4,
                        text=f"<b>r = {fr(r, 2)}</b> · lien {force}", font=dict(size=12 * p["scale"], color=t["text"]))
    tile_layout(mini, p)
    mini.update_layout(margin=dict(l=4, r=12, t=6, b=4))
    mini.update_xaxes(title_text=f"{label} ({unit})", title_font_size=11 * p["scale"], showgrid=True, griddash="dot")
    mini.update_yaxes(title_text="Épisodes / an", title_font_size=11 * p["scale"], rangemode="tozero")
    sub = f"Une année = un point · épisodes « {y} » selon {label[0].lower() + label[1:]}"
    return fig, summary, (table, "Climat et catastrophes par année"), mini, sub


if __name__ == "__main__":
    app.run(debug=True)
