"""
Dashboard de test - Risques naturels et climat à Bordeaux Métropole.

Lancement (depuis la racine du projet) :
    .venv\\Scripts\\python.exe dashboard\\app.py
puis ouvrir http://127.0.0.1:8050
"""

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dash import Dash, html, dcc, callback, clientside_callback, Input, Output

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
communes = load("arretes_par_commune", dtype=CODES)
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

MESURES = {
    "Inondations": "Gestion des eaux pluviales, zones d'expansion de crue, plan communal de sauvegarde",
    "Sécheresse / argiles": "Surveillance du bâti (fissures), étude de sol avant construction, végétalisation maîtrisée",
    "Tempêtes": "Élagage préventif, contrôle des toitures et des réseaux aériens",
    "Mouvements de terrain": "Cartographie des cavités, surveillance des coteaux",
    "Autres": "Analyse au cas par cas des arrêtés",
}

# Tables dérivées
dept_types = (communes.groupby("libelle_departement")[TYPES].sum()
              .assign(total=lambda d: d[TYPES].sum(axis=1)))

_bm = benchmark.query("territoire == 'Bordeaux Métropole'").iloc[0]
_gir = benchmark.query("niveau == 'Département' and territoire == 'Gironde'").iloc[0]
_fr = benchmark.query("niveau == 'France'").iloc[0]
RESTE_GIRONDE = {
    "niveau": "Département", "territoire": "Gironde hors métropole",
    "nb_arretes": _gir.nb_arretes - _bm.nb_arretes,
    "nb_communes": _gir.nb_communes - _bm.nb_communes,
}
RESTE_GIRONDE["arretes_par_commune"] = round(RESTE_GIRONDE["nb_arretes"] / RESTE_GIRONDE["nb_communes"], 2)

N_METRO = int((benchmark.niveau == "Métropole").sum())
YEAR_MIN, YEAR_MAX = int(climat.annee.min()), int(climat.annee.max())
EP_MIN, EP_MAX = int(episodes.annee.min()), int(episodes.annee.max())

# ---------------------------------------------------------------------------
# Thèmes (palette catégorielle validée : bleu, orange, aqua, jaune + gris "Autres")
# ---------------------------------------------------------------------------
THEMES = {
    "clair": dict(
        surface="#fcfcfb", text="#0b0b0b", muted="#52514e", grid="#e4e3df",
        accent="#2a78d6", ref="#6f6e69", neutral="#c9c8c2",
        series=dict(zip(TYPES, ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#8a8984"])),
        ramp=["#f0f5fc", "#9ec5f4", "#3987e5", "#1c5cab", "#0d366b"],
    ),
    "sombre": dict(
        surface="#1a1a19", text="#ffffff", muted="#c3c2b7", grid="#383835",
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
DEFAULT_PREFS = {"theme": "clair", "scale": 1.0, "patterns": False, "labels": False}


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
        font=dict(family="Atkinson Hyperlegible, Verdana, Arial, sans-serif", size=size, color=t["text"]),
        separators=", ",
        margin=dict(l=10, r=20, t=50 if legend else 20, b=10),
        hoverlabel=dict(font_size=size + 1, bgcolor=t["surface"], font_color=t["text"],
                        bordercolor=t["muted"]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title_text="",
                    font_color=t["text"], traceorder="normal"),
        showlegend=legend,
        barcornerradius=4,
    )
    axis = dict(gridcolor=t["grid"], zerolinecolor=t["muted"], linecolor=t["muted"],
                tickfont_color=t["text"], title_font_color=t["text"], automargin=True)
    fig.update_xaxes(**axis)
    fig.update_yaxes(**axis)
    return fig


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


def chart_card(cid, title, question, controls, note=None):
    """Bloc graphique : titre, question, filtres, graphe, résumé lu par lecteur d'écran, données."""
    return html.Section([
        html.H3(title, id=f"{cid}-title"),
        html.P(question, className="question"),
        html.Div(controls, className="controls", role="group", **{"aria-label": f"Filtres : {title}"}),
        html.Div(dcc.Graph(id=f"{cid}-graph", config=GRAPH_CONFIG),
                 **{"aria-describedby": f"{cid}-summary"}),
        html.P(id=f"{cid}-summary", className="summary", **{"aria-live": "polite"}),
        html.P(note, className="note") if note else None,
        html.Details([html.Summary("Afficher les données sous forme de tableau"),
                      html.Div(id=f"{cid}-table")]),
    ], className="card", **{"aria-labelledby": f"{cid}-title"})


GRAPH_CONFIG = {
    "displaylogo": False,
    "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"],
    "toImageButtonOptions": {"format": "png", "scale": 2},
}

# ---------------------------------------------------------------------------
# Application et mise en page
# ---------------------------------------------------------------------------
app = Dash(__name__, title="Risques naturels - Bordeaux Métropole", external_stylesheets=[
    "https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:wght@400;700&display=swap"])

app.index_string = app.index_string.replace("<html>", '<html lang="fr">')

a11y_bar = html.Details([
    html.Summary("Options d'accessibilité"),
    html.Div([
        fieldset("Thème", dcc.RadioItems(
            id="a11y-theme", value="auto", inline=True, className="choices", persistence=True,
            persistence_type="local", options=[
                {"label": "Automatique (système)", "value": "auto"},
                {"label": "Clair", "value": "clair"},
                {"label": "Sombre", "value": "sombre"},
                {"label": "Contraste élevé", "value": "contraste"}])),
        fieldset("Taille du texte", dcc.RadioItems(
            id="a11y-size", value=1.0, inline=True, className="choices", persistence=True,
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
    ], className="controls"),
], className="a11y-bar")

app.layout = html.Div([
    html.A("Aller au contenu principal", href="#main", className="skip-link"),
    dcc.Store(id="prefs"),
    html.Header([
        html.H1("Risques naturels et climat à Bordeaux Métropole"),
        html.P("Dashboard de test - quels risques progressent, et où agir en priorité ?"),
        a11y_bar,
        html.Nav(html.Ul([
            html.Li(html.A("Indicateurs clés", href="#kpi")),
            html.Li(html.A("Catastrophes dans la métropole", href="#catnat")),
            html.Li(html.A("Comparaisons territoriales", href="#territoires")),
            html.Li(html.A("Climat", href="#climat")),
        ]), **{"aria-label": "Sections du tableau de bord"}),
    ]),
    html.Main([
        html.Div([
            html.Span("Période analysée (années)", id="periode-label", className="label"),
            html.Div(dcc.RangeSlider(
                id="periode", min=YEAR_MIN, max=YEAR_MAX, step=1, value=[YEAR_MIN, YEAR_MAX],
                marks={y: str(y) for y in range(1950, YEAR_MAX + 1, 10)},
                tooltip={"placement": "bottom", "always_visible": False}, allowCross=False,
            ), className="slider"),
            html.P(id="periode-text", className="note", **{"aria-live": "polite"}),
        ], className="global-filter", role="group", **{"aria-labelledby": "periode-label"}),

        html.Section([
            html.H2("Indicateurs clés", id="kpi-title"),
            html.Div(id="kpis", className="kpi-grid"),
        ], id="kpi", **{"aria-labelledby": "kpi-title"}),

        html.Section([
            html.H2("Catastrophes naturelles dans la métropole", id="catnat-title"),
            chart_card(
                "evol", "Évolution des catastrophes dans la métropole",
                "Quels risques reviennent, et se multiplient-ils ? (épisodes CatNat, 28 communes, 1982-2022)",
                [types_checklist("evol-types"),
                 fieldset("Regroupement", dcc.RadioItems(
                     id="evol-grain", value="annee", inline=True, className="choices",
                     options=[{"label": "Par année", "value": "annee"},
                              {"label": "Par décennie", "value": "decennie"}])),
                 labelled("Indicateur climatique à comparer (graphique dessous)", "evol-climat", dcc.Dropdown(
                     id="evol-climat", value="none", clearable=False,
                     options=[{"label": "Aucun", "value": "none"}]
                     + [{"label": f"{v[0]} ({v[1]})", "value": k} for k, v in INDICATEURS.items()]))],
            ),
            chart_card(
                "heat", "Les 28 communes de la métropole par type de risque",
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
                     options=sorted(heatmap.libelle_geographique)))],
            ),
            html.Section([
                html.H3("Où agir en priorité ?", id="prio-title"),
                html.P("Risque dominant de chaque commune (type le plus fréquent) et mesure de prévention suggérée.",
                       className="question"),
                html.Div(id="prio-table"),
            ], className="card", **{"aria-labelledby": "prio-title"}),
        ], id="catnat", **{"aria-labelledby": "catnat-title"}),

        html.Section([
            html.H2("Comparaisons territoriales", id="territoires-title"),
            chart_card(
                "bench", "Bordeaux Métropole face à la Gironde, la France et les autres métropoles",
                "Bordeaux est-elle plus exposée qu'ailleurs ?",
                [fieldset("Indicateur", dcc.RadioItems(
                    id="bench-metric", value="arretes_par_commune", inline=True, className="choices",
                    options=[{"label": "Arrêtés par commune (moyenne)", "value": "arretes_par_commune"},
                             {"label": "Nombre total d'arrêtés", "value": "nb_arretes"}])),
                 fieldset("Territoires de référence", dcc.Checklist(
                     id="bench-refs", inline=True, className="choices",
                     value=["France", "Gironde", "Gironde hors métropole"],
                     options=["France", "Gironde", "Gironde hors métropole"])),
                 labelled("Nombre d'autres métropoles affichées", "bench-n", dcc.Slider(
                     id="bench-n", min=0, max=34, step=1, value=10,
                     marks={0: "0", 10: "10", 20: "20", 34: "34"},
                     tooltip={"placement": "bottom"}))],
                note="Le total d'arrêtés dépend de la taille du territoire : la moyenne par commune permet de comparer.",
            ),
            chart_card(
                "dept", "Nombre d'arrêtés par département",
                "Quels départements cumulent le plus d'arrêtés CatNat ?",
                [fieldset("Indicateur", dcc.RadioItems(
                    id="dept-metric", value="nb_arretes", inline=True, className="choices",
                    options=[{"label": "Nombre total d'arrêtés", "value": "nb_arretes"},
                             {"label": "Arrêtés par commune (moyenne)", "value": "arretes_par_commune"}])),
                 labelled("Nombre de départements affichés", "dept-n", dcc.Slider(
                     id="dept-n", min=5, max=40, step=1, value=15, marks={5: "5", 15: "15", 25: "25", 40: "40"},
                     tooltip={"placement": "bottom"}))],
            ),
            chart_card(
                "dtype", "Arrêtés par département et par type de risque",
                "Quels risques dominent dans chaque département ?",
                [types_checklist("dtype-types"),
                 fieldset("Échelle", dcc.RadioItems(
                     id="dtype-norm", value="", inline=True, className="choices",
                     options=[{"label": "Nombre d'arrêtés", "value": ""},
                              {"label": "Répartition en %", "value": "percent"}])),
                 labelled("Nombre de départements affichés", "dtype-n", dcc.Slider(
                     id="dtype-n", min=5, max=40, step=1, value=15, marks={5: "5", 15: "15", 25: "25", 40: "40"},
                     tooltip={"placement": "bottom"})),
                 fieldset("Option", dcc.Checklist(
                     id="dtype-gironde", value=["on"], className="choices",
                     options=[{"label": "Toujours inclure la Gironde", "value": "on"}]))],
            ),
        ], id="territoires", **{"aria-labelledby": "territoires-title"}),

        html.Section([
            html.H2("Climat de la Gironde", id="climat-title"),
            chart_card(
                "clim", "Évolution d'un indicateur climatique",
                "Le climat se réchauffe-t-il ? Les sécheresses et les pluies extrêmes évoluent-elles ?",
                [labelled("Indicateur (température, pluviométrie...)", "clim-ind", dcc.Dropdown(
                    id="clim-ind", value="NBJTX30", clearable=False,
                    options=[{"label": f"{v[0]} ({v[1]})", "value": k} for k, v in INDICATEURS.items()])),
                 fieldset("Affichage", dcc.Checklist(
                     id="clim-opts", value=["mm10"], inline=True, className="choices",
                     options=[{"label": "Moyenne mobile 10 ans", "value": "mm10"},
                              {"label": "Tendance linéaire", "value": "trend"}])),
                 fieldset("Regroupement", dcc.RadioItems(
                     id="clim-grain", value="annee", inline=True, className="choices",
                     options=[{"label": "Par année", "value": "annee"},
                              {"label": "Moyenne par décennie", "value": "decennie"}]))],
            ),
            chart_card(
                "scat", "Le climat évolue-t-il avec les catastrophes ?",
                "Relation exploratoire entre un indicateur climatique et les épisodes CatNat d'un type (une année = un point).",
                [labelled("Indicateur climatique (axe horizontal)", "scat-x", dcc.Dropdown(
                    id="scat-x", value="NBJTX30", clearable=False,
                    options=[{"label": f"{v[0]} ({v[1]})", "value": k} for k, v in INDICATEURS.items()])),
                 labelled("Type de catastrophe (axe vertical)", "scat-y", dcc.Dropdown(
                     id="scat-y", value="Sécheresse / argiles", clearable=False, options=TYPES))],
                note="Corrélation exploratoire sur environ 40 années : elle ne prouve pas un lien de cause à effet.",
            ),
        ], id="climat", **{"aria-labelledby": "climat-title"}),
    ], id="main", tabIndex=-1),
    html.Footer(html.P("Sources : arrêtés CatNat (data.gouv.fr), Météo-France données mensuelles Gironde 1950-2024. "
                       "CatNat limité à 1982-2022 (2023-2024 incomplets).")),
])

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
        root.classList.toggle('readable-font', options.includes('font'));
        root.classList.toggle('wide-spacing', options.includes('spacing'));
        const motion = options.includes('motion') ||
            (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
        root.classList.toggle('reduce-motion', motion);
        return {theme: eff, scale: size, patterns: options.includes('patterns'),
                labels: options.includes('labels')};
    }
    """,
    Output("prefs", "data"),
    Input("a11y-theme", "value"), Input("a11y-size", "value"), Input("a11y-options", "value"),
)


def clip_years(df, periode):
    return df[(df.annee >= periode[0]) & (df.annee <= periode[1])]


# ---------------------------------------------------------------------------
# KPI
# ---------------------------------------------------------------------------
def kpi(label, value, detail):
    return html.Div([html.P(label, className="kpi-label"), html.P(value, className="kpi-value"),
                     html.P(detail, className="kpi-detail")], className="kpi", role="group",
                    **{"aria-label": label})


@callback(Output("kpis", "children"), Output("periode-text", "children"), Input("periode", "value"))
def update_kpis(periode):
    y0, y1 = periode
    cards = []

    clim = clip_years(climat, periode)
    if y1 - y0 + 1 >= 20:
        first = clim[clim.annee < y0 + 10].NBJTX30.mean()
        last = clim[clim.annee > y1 - 10].NBJTX30.mean()
        diff = last - first
        cards.append(kpi("Jours ≥ 30 °C par an", f"{fr(last, 1)} j",
                         f"{y1 - 9}-{y1} contre {fr(first, 1)} j en {y0}-{y0 + 9} : "
                         f"{'+' if diff >= 0 else '−'}{fr(abs(diff), 1)} j ({'+' if diff >= 0 else '−'}"
                         f"{fr(abs(diff) / first * 100)} %)"))
    else:
        cards.append(kpi("Jours ≥ 30 °C par an", "-", "Choisir une période d'au moins 20 ans pour comparer deux décennies."))

    ep = clip_years(episodes, periode)
    if len(ep):
        totaux = ep[TYPES].sum()
        decades = ep.assign(dec=ep.annee // 10 * 10).groupby("dec")[TYPES].sum().sum(axis=1)
        cards.append(kpi(f"Épisodes CatNat dans la métropole ({int(ep.annee.min())}-{int(ep.annee.max())})",
                         fr(totaux.sum()),
                         " · ".join(f"années {d} : {fr(n)}" for d, n in decades.items())))
        top = totaux.idxmax()
        cards.append(kpi("Risque dominant", top,
                         f"{fr(totaux[top] / totaux.sum() * 100)} % des épisodes ({fr(totaux[top])} sur {fr(totaux.sum())})"))
    else:
        cards.append(kpi("Épisodes CatNat dans la métropole", "-", f"Données disponibles de {EP_MIN} à {EP_MAX}."))
        cards.append(kpi("Risque dominant", "-", f"Données disponibles de {EP_MIN} à {EP_MAX}."))

    ratio = _bm.arretes_par_commune / _fr.arretes_par_commune
    cards.append(kpi("Arrêtés par commune : métropole vs France", f"× {fr(ratio, 1)}",
                     f"{fr(_bm.arretes_par_commune, 1)} arrêtés par commune à Bordeaux Métropole contre "
                     f"{fr(_fr.arretes_par_commune, 1)} en France (1982-2022)"))

    c = heatmap.loc[heatmap.nb_arretes.idxmax()]
    risk = c[TYPES].astype(float).idxmax()
    cards.append(kpi("Commune la plus touchée", c.libelle_geographique,
                     f"{fr(c.nb_arretes)} arrêtés, surtout {risk.lower()} ({fr(c[risk])})"))

    note = (f"Période sélectionnée : {y0}-{y1}. Elle s'applique aux indicateurs climatiques et aux épisodes CatNat "
            f"(disponibles {EP_MIN}-{EP_MAX}). Les comparaisons territoriales et les communes couvrent toute la période 1982-2022.")
    return cards, note


# ---------------------------------------------------------------------------
# Graphique : évolution des épisodes dans la métropole
# ---------------------------------------------------------------------------
def by_decade(df, cols, how="sum"):
    g = df.assign(periode=(df.annee // 10 * 10)).groupby("periode")[cols]
    out = (g.sum() if how == "sum" else g.mean()).reset_index()
    out["x"] = out.periode.map(lambda d: f"{d}-{d + 9}")
    return out


@callback(Output("evol-graph", "figure"), Output("evol-summary", "children"), Output("evol-table", "children"),
          Input("evol-types", "value"), Input("evol-grain", "value"), Input("evol-climat", "value"),
          Input("periode", "value"), Input("prefs", "data"))
def update_evol(types, grain, clim_ind, periode, prefs):
    p = get_prefs(prefs)
    types = [t for t in TYPES if t in (types or [])]
    ep = clip_years(episodes, periode)
    if not types or ep.empty:
        return empty_fig(p, "Aucune donnée : sélectionner au moins un type et une période entre 1982 et 2022."), "", ""

    if grain == "decennie":
        data = by_decade(ep, types)
    else:
        data = ep[["annee"] + types].assign(x=ep.annee)

    with_clim = clim_ind != "none"
    fig = make_subplots(rows=2 if with_clim else 1, cols=1, shared_xaxes=True,
                        row_heights=[0.65, 0.35] if with_clim else [1], vertical_spacing=0.08)
    for t in types:
        fig.add_bar(x=data.x, y=data[t], name=t, marker=bar_marker(t, p), row=1, col=1,
                    text=data[t].where(data[t] > 0) if p["labels"] else None, textposition="inside",
                    hovertemplate=f"<b>{t}</b><br>%{{x}} : %{{y}} épisode(s)<extra></extra>")
    fig.update_layout(barmode="stack", barcornerradius=0)
    fig.update_yaxes(title_text="Épisodes", row=1, col=1)

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
    sums = data[types].sum()
    summary = (f"{fr(sums.sum())} épisodes sur la période. Type le plus fréquent : {sums.idxmax()} "
               f"({fr(sums.max())}). Pic : {rec.x} avec {fr(totals.max())} épisodes.")
    table = data[["x"] + types].rename(columns={"x": "Décennie" if grain == "decennie" else "Année"})
    return fig, summary, html_table(table, "Épisodes CatNat par période et par type")


# ---------------------------------------------------------------------------
# Graphique : heatmap des communes
# ---------------------------------------------------------------------------
@callback(Output("heat-graph", "figure"), Output("heat-summary", "children"), Output("heat-table", "children"),
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
    return fig, summary, html_table(table, f"Arrêtés par commune et par type ({unit})")


@callback(Output("prio-table", "children"), Input("heat-communes", "value"))
def update_prio(selection):
    df = heatmap if not selection else heatmap[heatmap.libelle_geographique.isin(selection)]
    df = df.sort_values("nb_arretes", ascending=False)
    dom = df[TYPES].astype(float).idxmax(axis=1)
    table = pd.DataFrame({
        "Commune": df.libelle_geographique,
        "Arrêtés (total)": df.nb_arretes,
        "Risque dominant": dom,
        "Part du risque dominant (%)": [round(df.loc[i, d] / df.loc[i, "nb_arretes"] * 100) for i, d in dom.items()],
        "Mesure suggérée": dom.map(MESURES),
    })
    return html_table(table, "Priorités d'action par commune, de la plus touchée à la moins touchée")


# ---------------------------------------------------------------------------
# Graphique : benchmark territoires
# ---------------------------------------------------------------------------
@callback(Output("bench-graph", "figure"), Output("bench-summary", "children"), Output("bench-table", "children"),
          Input("bench-metric", "value"), Input("bench-refs", "value"), Input("bench-n", "value"),
          Input("prefs", "data"))
def update_bench(metric, refs, n, prefs):
    p = get_prefs(prefs)
    t = p["t"]
    refs = refs or []
    rows = [benchmark.query("territoire == 'Bordeaux Métropole'").assign(groupe="Bordeaux Métropole")]
    if "France" in refs:
        rows.append(benchmark.query("niveau == 'France'").assign(groupe="Références"))
    if "Gironde" in refs:
        rows.append(benchmark.query("niveau == 'Département' and territoire == 'Gironde'").assign(groupe="Références"))
    if "Gironde hors métropole" in refs:
        rows.append(pd.DataFrame([RESTE_GIRONDE]).assign(groupe="Références"))
    autres = (benchmark.query("niveau == 'Métropole' and territoire != 'Bordeaux Métropole'")
              .nlargest(n or 0, metric).assign(groupe="Autres métropoles"))
    rows.append(autres)
    df = pd.concat(rows).sort_values(metric)

    colors = {"Bordeaux Métropole": t["accent"], "Références": t["ref"], "Autres métropoles": t["neutral"]}
    fmt = ".1f" if metric == "arretes_par_commune" else ",.0f"
    label = "Arrêtés par commune" if metric == "arretes_par_commune" else "Nombre d'arrêtés"
    fig = go.Figure()
    for g, c in colors.items():
        d = df[df.groupe == g]
        if d.empty:
            continue
        fig.add_bar(y=d.territoire, x=d[metric], orientation="h", name=g, marker_color=c,
                    marker_line=dict(color=t["text"] if p["theme"] == "contraste" else t["surface"], width=1),
                    marker_pattern_shape="/" if p["patterns"] and g == "Références" else "",
                    text=d[metric] if p["labels"] or g == "Bordeaux Métropole" else None,
                    texttemplate=f"%{{x:{fmt}}}", textposition="outside", cliponaxis=False,
                    customdata=d.nb_communes,
                    hovertemplate=f"<b>%{{y}}</b><br>{label} : %{{x:{fmt}}}<br>%{{customdata}} communes<extra></extra>")
    fig.update_layout(barmode="overlay", yaxis=dict(categoryorder="array", categoryarray=list(df.territoire)))
    fig.update_xaxes(title_text=label)
    style_fig(fig, p, height=max(300, 28 * len(df) + 100))

    rank = int((benchmark.query("niveau == 'Métropole'")[metric] > _bm[metric]).sum()) + 1
    summary = (f"Bordeaux Métropole : {fr(_bm[metric], 1 if metric == 'arretes_par_commune' else 0)} "
               f"({label.lower()}), rang {rank} sur {N_METRO} métropoles. "
               f"France : {fr(_fr[metric], 1 if metric == 'arretes_par_commune' else 0)}.")
    table = df.iloc[::-1][["territoire", "groupe", "nb_arretes", "nb_communes", "arretes_par_commune"]]
    table.columns = ["Territoire", "Groupe", "Arrêtés", "Communes", "Arrêtés par commune"]
    return fig, summary, html_table(table, "Comparaison des territoires")


# ---------------------------------------------------------------------------
# Graphique : départements (top N)
# ---------------------------------------------------------------------------
@callback(Output("dept-graph", "figure"), Output("dept-summary", "children"), Output("dept-table", "children"),
          Input("dept-metric", "value"), Input("dept-n", "value"), Input("prefs", "data"))
def update_dept(metric, n, prefs):
    p = get_prefs(prefs)
    t = p["t"]
    df = benchmark.query("niveau == 'Département'").nlargest(n, metric).sort_values(metric)
    is_gir = df.territoire == "Gironde"
    fmt = ".1f" if metric == "arretes_par_commune" else ",.0f"
    label = "Arrêtés par commune" if metric == "arretes_par_commune" else "Nombre d'arrêtés"
    fig = go.Figure(go.Bar(
        y=df.territoire, x=df[metric], orientation="h",
        marker=dict(color=np.where(is_gir, t["accent"], t["neutral"]),
                    line=dict(color=t["text"] if p["theme"] == "contraste" else t["surface"], width=1)),
        text=df[metric] if p["labels"] else None, texttemplate=f"%{{x:{fmt}}}", textposition="outside",
        cliponaxis=False, customdata=df.nb_communes,
        hovertemplate=f"<b>%{{y}}</b><br>{label} : %{{x:{fmt}}}<br>%{{customdata}} communes<extra></extra>"))
    fig.update_xaxes(title_text=label)
    style_fig(fig, p, height=max(320, 26 * len(df) + 80), legend=False)

    all_dep = benchmark.query("niveau == 'Département'")
    rank = int((all_dep[metric] > _gir[metric]).sum()) + 1
    first = df.iloc[-1]
    summary = (f"Premier département : {first.territoire} ({fr(first[metric], 1 if metric != 'nb_arretes' else 0)}). "
               f"La Gironde est {rank}ᵉ sur {len(all_dep)} départements"
               f"{' (mise en évidence en bleu)' if is_gir.any() else ' (hors du classement affiché)'}.")
    table = df.iloc[::-1][["territoire", "nb_arretes", "nb_communes", "arretes_par_commune"]]
    table.columns = ["Département", "Arrêtés", "Communes", "Arrêtés par commune"]
    return fig, summary, html_table(table, f"Top {n} des départements")


# ---------------------------------------------------------------------------
# Graphique : départements par type de risque
# ---------------------------------------------------------------------------
@callback(Output("dtype-graph", "figure"), Output("dtype-summary", "children"), Output("dtype-table", "children"),
          Input("dtype-types", "value"), Input("dtype-norm", "value"), Input("dtype-n", "value"),
          Input("dtype-gironde", "value"), Input("prefs", "data"))
def update_dtype(types, norm, n, gironde, prefs):
    p = get_prefs(prefs)
    types = [t for t in TYPES if t in (types or [])]
    if not types:
        return empty_fig(p, "Sélectionner au moins un type de risque."), "", ""
    df = dept_types[types].assign(sel=lambda d: d.sum(axis=1)).sort_values("sel", ascending=False)
    top = df.head(n)
    if gironde and "Gironde" not in top.index:
        top = pd.concat([top, df.loc[["Gironde"]]])
    top = top.sort_values("sel")

    fig = go.Figure()
    for t in types:
        fig.add_bar(y=top.index, x=top[t], name=t, orientation="h", marker=bar_marker(t, p),
                    text=top[t] if p["labels"] else None, textposition="inside",
                    hovertemplate=f"<b>%{{y}}</b><br>{t} : %{{x}}<extra></extra>")
    fig.update_layout(barmode="stack", barnorm=norm or None, barcornerradius=0)
    fig.update_xaxes(title_text="Part des arrêtés (%)" if norm else "Nombre d'arrêtés")
    style_fig(fig, p, height=max(340, 26 * len(top) + 110))

    lead = top.index[-1]
    summary = (f"{lead} cumule le plus d'arrêtés pour les types sélectionnés ({fr(top.sel.iloc[-1])}), "
               f"surtout {top.loc[lead, types].idxmax().lower()}. Gironde : {fr(df.loc['Gironde', 'sel'])} arrêtés, "
               f"surtout {df.loc['Gironde', types].idxmax().lower()}.")
    table = top.iloc[::-1][types + ["sel"]].reset_index().rename(
        columns={"libelle_departement": "Département", "sel": "Total"})
    return fig, summary, html_table(table, "Arrêtés par département et par type de risque")


# ---------------------------------------------------------------------------
# Graphique : indicateur climatique
# ---------------------------------------------------------------------------
@callback(Output("clim-graph", "figure"), Output("clim-summary", "children"), Output("clim-table", "children"),
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
    return fig, [summary, html.Br(), stations], html_table(table, f"{label} par période")


# ---------------------------------------------------------------------------
# Graphique : nuage climat x catastrophes
# ---------------------------------------------------------------------------
lien = load("lien_climat_catastrophes")


@callback(Output("scat-graph", "figure"), Output("scat-summary", "children"), Output("scat-table", "children"),
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
               f"(r = {fr(r, 2)}) entre {label.lower()} et les épisodes « {y} ». "
               "Relation exploratoire, pas une preuve de cause.")
    table = df[["annee", x, y]].round(1)
    table.columns = ["Année", f"{label} ({unit})", f"Épisodes {y}"]
    return fig, summary, html_table(table, "Climat et catastrophes par année")


if __name__ == "__main__":
    app.run(debug=True)
