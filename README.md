# Dashboard « Risques naturels et climat » · Bordeaux Métropole

Tableau de bord interactif et accessible (Python · Dash · Plotly) qui croise les **arrêtés de catastrophe naturelle (CatNat)** et les **données climatiques de Météo-France** pour répondre à une question simple : quel est le risque, comment évolue-t-il, et quelle est la part du climat ?

---

## Sommaire

1. [La problématique](#1-la-problématique)
2. [Trois questions, trois réponses](#2-trois-questions-trois-réponses)
3. [Les données](#3-les-données)
4. [Le dashboard](#4-le-dashboard)
5. [Installer et lancer](#5-installer-et-lancer)
6. [Organisation du projet](#6-organisation-du-projet)
7. [Annexes](#7-annexes)

---

## 1. La problématique

> **« Quel est le risque de catastrophe naturelle en métropole de Bordeaux, comment évolue-t-il, et dans quelle mesure le climat (chaleur, sécheresse, pluies extrêmes) l'aggrave-t-il ? »**

| | |
|---|---|
| **Public visé** | Un décideur public : Bordeaux Métropole (direction des risques), élus, préfecture |
| **Son besoin** | Comprendre le risque pour prioriser les investissements de prévention |
| **Périmètre** | Les 28 communes de Bordeaux Métropole, comparées à la Gironde, à la France et aux autres métropoles |

*Idée de départ : aider un particulier ou une entreprise à choisir où s'installer en Gironde selon les risques et les contraintes (chaleur, pluie, terrain). Le sujet a ensuite été recentré sur le décideur public.*

---

## 2. Trois questions, trois réponses

La problématique se découpe en trois questions. Tout le projet (données, tables, dashboard) est organisé pour y répondre.

| Question | Données | Tables | Dans le dashboard |
|---|---|---|---|
| **① Quel est le risque ?** | Arrêtés CatNat | `heatmap_communes`, `episodes_par_annee`, `benchmark` | KPI arrêtés, risque dominant, commune la plus touchée · graphique **Communes les plus exposées** |
| **② Comment évolue-t-il ?** | Arrêtés CatNat | `episodes_par_annee` | KPI nombre de catastrophes · graphique **Fréquence des catastrophes** |
| **③ Le climat l'aggrave-t-il ?** | Météo-France + CatNat | `climat_annuel`, `lien_climat_catastrophes` | KPI jours ≥ 30 °C · graphiques **Évolution du climat** et **Lien climat × catastrophes** |

### ① Quel est le risque ?

On mesure le risque par le **nombre d'arrêtés CatNat** (reconnaissance officielle d'une catastrophe naturelle dans une commune). On regarde **où** il se concentre (par commune), **lequel** domine (par type) et **à quel niveau** par rapport aux autres territoires.

### ② Comment évolue-t-il ?

On suit le nombre d'**épisodes par an et par type** depuis 1982, regroupés **par décennie** pour lisser les variations d'une année à l'autre.

### ③ Le climat l'aggrave-t-il ?

On suit d'abord l'**évolution du climat** (chaleur, pluie, sécheresse) depuis 1950, puis on **croise** climat et catastrophes année par année. Ce croisement est une **corrélation exploratoire**, pas une preuve de cause.

---

## 3. Les données

### Sources

| Source | Contenu | Période | Sert à | Lien |
|---|---|---|---|---|
| **Arrêtés CatNat** (data.gouv.fr) | Arrêtés de catastrophe naturelle par commune, France entière | 1982 → 2024 (utilisé : 1982-2022) | Questions ① ② ③ | [data.gouv.fr](https://www.data.gouv.fr/datasets/arretes-de-catastrophe-naturelle-par-commune) |
| **Météo-France** (data.gouv.fr) | Données climatologiques mensuelles des stations de Gironde | 1950 → 2024 | Question ③ | [defis.data.gouv.fr](https://defis.data.gouv.fr/datasets/6569b3d7d193b4daf2b43edc) |

*Source explorée mais non retenue : feux de forêt 2015-2025 de la [BDIFF](https://bdiff.agriculture.gouv.fr/incendies).*

### Prétraitements

**Arrêtés CatNat** (communs à toutes les tables CatNat) :
- Code INSEE converti en texte sur 5 caractères (garde le 0 initial, ex. `06088`).
- Année de l'événement = année de `date_debut`.
- Période limitée à **1982-2022** : 2023 et 2024 sont incomplets.
- **8 types regroupés en 5** : Sécheresse / argiles, Inondations, Tempêtes, Mouvements de terrain, Autres.

**Climat (Météo-France)** :
- Seules les **années complètes** (12 mois) sont gardées.
- Seules les stations ayant **au moins 40 années complètes** sont retenues, soit **19 stations**.
- Agrégation annuelle : **somme** pour les jours et la pluie, **moyenne** pour la température, puis **moyenne des stations**.
- Variables calculées : **bilan hydrique** (pluie − évapotranspiration), **moyennes mobiles sur 10 ans**, **nombre de stations** par année.

### Tables préparées

Produites par `notebook/cration_base.ipynb`, rangées ici par question.

| Question | Table | Niveau · période | Ce qu'elle montre |
|---|---|---|---|
| ① | `arretes_par_commune` | France entière (≈ 35 000 communes) · 1 ligne / commune | Classement national des communes (base des tables ci-dessous) |
| ① | `heatmap_communes` | Les 28 communes de la métropole | Quelle commune est touchée par quel risque |
| ① | `benchmark` | France, départements, métropoles · 1 ligne / territoire | Position de Bordeaux face aux autres territoires |
| ① ② | `episodes_par_annee` | Métropole · 1982-2022 · 1 ligne / année | Épisodes par année et par type |
| ③ | `climat_annuel` | Gironde · 1950-2024 · 1 ligne / année | Réchauffement, sécheresse, pluies extrêmes |
| ③ | `lien_climat_catastrophes` | Climat + épisodes · 1982-2022 · 1 ligne / année | Relation climat ↔ catastrophes |

<details>
<summary><b>Détail des traitements propres à chaque table</b></summary>

- **`arretes_par_commune`** : liste complète des communes, y compris celles sans arrêté (0) ; total et détail par type ; tri décroissant. Filtrer `departement == "33"` pour la Gironde.
- **`heatmap_communes`** : simple filtre de `arretes_par_commune` sur les 28 communes de la métropole.
- **`benchmark`** : total d'arrêtés par territoire, nombre de communes (référentiel toutes années), moyenne d'arrêtés par commune.
- **`episodes_par_annee`** : filtre sur la métropole ; un épisode touchant plusieurs communes est compté **une seule fois** ; comptage par année et par type ; années sans épisode mises à 0.
- **`climat_annuel`** : traitements « Climat » ci-dessus ; colonnes `TX`, `NBJTX30`, `NBJTX35`, `NBJTNS20`, `RR`, `ETP`, `NBJRR30`, `NBJRR50`, `bilan_hydrique`, `nb_stations`, moyennes mobiles `*_mm10`. Fiabilité plus faible avant 1954 (5 à 7 stations).
- **`lien_climat_catastrophes`** : jointure de `climat_annuel` et `episodes_par_annee` sur l'année (années communes uniquement).

</details>

---

## 4. Le dashboard

Une seule page, sans défilement sur un écran d'ordinateur, lisible en trois temps : **le chiffre (KPI) → la tendance (graphique) → le détail (fenêtre)**.

### Les 5 KPI : la réponse en un coup d'œil

| Question | KPI | Valeur 1950-2022 |
|---|---|---|
| ① | Arrêtés CatNat · Bordeaux Métropole | 840 (28 communes) |
| ① | Risque dominant | Sécheresse / argiles (46 % des épisodes) |
| ① | Commune la plus touchée | Le Bouscat · inondations |
| ② | Nombre de catastrophes 1982-2022 | 135 (≈ 33 par décennie) |
| ③ | Jours ≥ 30 °C par an, en moyenne sur la période | 20,6 j |

### Les 4 graphiques : une question chacun

| Position | Graphique | Question | Type | Table |
|---|---|---|---|---|
| Haut gauche | Communes les plus exposées | ① Où se concentre le risque ? | Barres horizontales empilées (top 10 ; les 28 dans le détail) | `heatmap_communes` |
| Bas gauche | Fréquence des catastrophes | ② Quels risques progressent ? | Courbes par décennie + indicateur climatique en dessous (axe séparé) | `episodes_par_annee` + `climat_annuel` |
| Haut droite | Évolution du climat | ③ Le climat change-t-il ? | Barres annuelles + moyenne mobile sur 10 ans | `climat_annuel` |
| Bas droite | Lien climat × catastrophes | ③ Le climat aggrave-t-il ? | Nuage de points + tendance + coefficient r | `lien_climat_catastrophes` |

**Code couleur des cartes :** liseré orange = catastrophes (colonne de gauche), turquoise = climat (haut droite), moitié-moitié = le lien (bas droite).

### Les filtres

| Filtre | Emplacement | Effet |
|---|---|---|
| **Indicateur climatique** | En haut à gauche | Met à jour les graphiques climat, fréquence et lien (jours ≥ 30 °C, pluie, bilan hydrique…) |
| **Types de catastrophes** | À côté | Met à jour les graphiques communes, fréquence et lien |
| **Période** | En haut à droite | 1950-2022 ; s'applique au climat, aux épisodes et aux KPI |

Les titres des graphiques changent avec les filtres (ex. « Fréquence des inondations vs pluie annuelle »).

### La fenêtre de détail (clic sur un graphique)

- Filtres propres au graphique (regroupement, mode d'affichage, tri, communes…).
- Graphique complet et interactif, avec un résumé en texte.
- **Explorer année par année** (graphiques climat et lien) : un curseur au clavier annonce la valeur, l'écart à la moyenne et le rang.
- **Tableau des données** et bouton **« Télécharger les données (Excel) »** (2 feuilles : données et description).

### L'accessibilité

Le bouton **Accessibilité** (en haut à droite) ouvre les réglages ; ils sont mémorisés dans le navigateur.

| Besoin | Ce qui est prévu |
|---|---|
| Daltonisme, impression N&B | Motifs sur les barres, pointillés et formes de points distincts, couleur jamais seule |
| Malvoyance | Thèmes clair / sombre / contraste élevé / automatique ; texte 125 % ou 150 % (grille 2 × 2 conservée) ; police Atkinson Hyperlegible |
| Dyslexie | Espacement du texte augmenté (WCAG 1.4.12) |
| Sensibilité au mouvement | Animations réduites |
| Clavier seul | Tab entre les graphiques, Entrée ouvre, Échap ferme et rend le focus ; focus visible ; lien d'évitement |
| Lecteur d'écran | Page en français, titres hiérarchisés, résumé texte lu automatiquement, tableaux avec en-têtes, fenêtres `<dialog>` natives |

Référentiels suivis : WCAG 2.1 et RGAA (pas encore d'audit avec des utilisateurs).

---

## 5. Installer et lancer

**Prérequis :** Python 3 (le projet est développé et testé avec Python 3.13).

Tous les paquets nécessaires sont listés, avec leurs versions testées, dans [`requirements.txt`](requirements.txt) :

| Paquet | Version | Rôle |
|---|---|---|
| `dash` | 4.4.1 | Application web |
| `plotly` | 7.1.0 | Graphiques |
| `pandas` | 3.0.6 | Lecture et calcul des données |
| `numpy` | 2.5.3 | Tendances et corrélations |
| `openpyxl` | 3.1.5 | Export Excel des données |
| `ipykernel` | 7.4.0 | Exécuter le notebook de préparation |

**1. Créer l'environnement virtuel** (une seule fois, depuis la racine du projet) :

```bash
python -m venv .venv
```

**2. Installer les paquets :**

```bash
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

**3. Lancer le dashboard :**

```bash
.venv\Scripts\python.exe dashboard\app.py
```

Puis ouvrir **http://127.0.0.1:8050**.

> Sous macOS / Linux, remplacer `.venv\Scripts\python.exe` par `.venv/bin/python`.

> Le serveur démarre en mode `debug` (barre « Errors / Callbacks » en bas à droite). Pour une démonstration, passer `app.run(debug=False)` à la fin de `dashboard/app.py`.

---

## 6. Organisation du projet

```
DATAVIZ Dashboard/
├── data/                              Données brutes
│   ├── catnat.csv                       Arrêtés CatNat par commune
│   └── MENSQ_33_previous-1950-2024.csv  Météo-France, données mensuelles de Gironde
├── notebook/
│   ├── cration_base.ipynb               Préparation : données brutes → tables
│   ├── dash.ipynb                       Essais
│   └── *.csv                            Les 6 tables préparées (section 3)
├── dashboard/
│   ├── app.py                           Application Dash (données, mise en page, graphiques)
│   └── assets/
│       ├── style.css                    Styles, thèmes et accessibilité
│       └── dialogs.js                   Ouverture / fermeture des fenêtres de détail
├── captures/                          Captures d'écran du dashboard (présentation)
├── requirements.txt                   Paquets Python à installer
└── README.md
```

---

## 7. Annexes

### Trame de la présentation

- [ ] **La problématique** et les trois questions qui en découlent (sections 1 et 2).
- [ ] **Les données** : quelles bases, quels prétraitements et pourquoi (section 3).
- [ ] **Les méthodes et la technologie** : pourquoi Python, Dash et Plotly.
- [ ] **Les choix d'affichage** : une page, KPI en haut, catastrophes à gauche, climat à droite, analyses par décennie (section 4).
- [ ] **Le lien météo × catastrophes** : corrélation exploratoire (nuage de points + coefficient r), pas une preuve de cause.
- [ ] **L'accessibilité** : options, clavier, lecteur d'écran.

### Idées de visuels non retenues

Pistes envisagées au départ ; certaines restent faisables avec les tables existantes.

| Visuel | Question | Table | Statut |
|---|---|---|---|
| Arrêtés par département (top 15) | ① | `benchmark` | Retiré du dashboard |
| Arrêtés par département et par type | ① | `arretes_par_commune` | Retiré du dashboard |
| Arrêtés par commune de Gironde (top 20) | ① | `arretes_par_commune` (`departement == "33"`) | Non réalisé |
| Bordeaux Métropole vs Gironde, France, autres métropoles | ① | `benchmark` | Retiré du dashboard (repris dans la présentation) |
| Heatmap des 28 communes × types | ① | `heatmap_communes` | Remplacée par des barres empilées (plus lisibles) |
| Risque dominant en barre à 100 % | ① | `episodes_par_annee` | Remplacé par un KPI |
| Sécheresse : bilan hydrique, pluie, ETP avec ligne à zéro | ③ | `climat_annuel` | Intégré au sélecteur d'indicateur |
| Pluies extrêmes (jours ≥ 30 / 50 mm) | ③ | `climat_annuel` | Intégré au sélecteur d'indicateur |
