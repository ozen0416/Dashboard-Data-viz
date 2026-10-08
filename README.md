Projet Dashboard



Agent immo / personne / entreprise dans la réigion de gironde / bordeau, objectif = trouver le meilleur endroit pour s'installer en prenant en compte les risques possible et les différentes contraintes (chaleur, pluvio, terrain équipement) 



- Incendies lien données période 20-25 ici = "https://bdiff.agriculture.gouv.fr/incendies?if%5BidIncendie%5D=&if%5BdateAlerteDeb%5D%5Bdate%5D=01%2F01%2F2015&if%5BdateAlerteDeb%5D%5Btime%5D%5Bhour%5D=0&if%5BdateAlerteDeb%5D%5Btime%5D%5Bminute%5D=0&if%5BdateAlerteFin%5D%5Bdate%5D=31%2F12%2F2025&if%5BdateAlerteFin%5D%5Btime%5D%5Bhour%5D=23&if%5BdateAlerteFin%5D%5Btime%5D%5Bminute%5D=59&if%5BperiodeDeb%5D%5Bjour%5D=&if%5BperiodeDeb%5D%5Bmois%5D=&if%5BperiodeFin%5D%5Bjour%5D=&if%5BperiodeFin%5D%5Bmois%5D=&if%5BperiodeAnnees%5D%5BanneeDeb%5D=&if%5BperiodeAnnees%5D%5BanneeFin%5D=&if%5BheureDeb%5D=&if%5BheureFin%5D=&if%5BsurfaceDeInc%5D=1&if%5BsurfaceDe%5D=&if%5BsurfaceA%5D=&if%5BsurfaceAInc%5D=1&if%5Bfr%5D=1&if%5Bzone%5D=&if%5Bra%5D=&if%5Bdeprts%5D%5Bvalue%5D=&if%5Bcommune%5D=&if%5Bbbox%5D%5Bvalue%5D=&if%5Bsubmit%5D=#tab"
- Météo lien données période 1950-2024 = "https://defis.data.gouv.fr/datasets/6569b3d7d193b4daf2b43edc"

-CATNAT : https://www.data.gouv.fr/datasets/arretes-de-catastrophe-naturelle-par-commune

-DVF : https://www.data.gouv.fr/datasets/demandes-de-valeurs-foncieres-geolocalisees


Le public et la question

ON s'adresses à un décideur public : Bordeaux Métropole (la direction qui s'occupe des risques), les élus, ou la préfecture. La question devient :

« Quels risques climatiques progressent à Bordeaux Métropole, et où faut-il investir en priorité pour protéger les habitants ? »
Du risque à la mesure

Problématique

« Quels risques naturels pèsent le plus sur Bordeaux Métropole, comment évoluent-ils avec le changement climatique, et dans quelles communes une collectivité doit-elle agir en priorité ? »

Le public visé est un décideur public (la métropole, la préfecture) qui doit prioriser ses investissements de prévention.

Ton intuition d’écarter les incendies est bonne : les feux ne figurent pas dans CatNat, et la métropole en a très peu. Ta problématique tient avec deux bases seulement, ce qui rendra le dashboard plus lisible.

Niveaux d’analyse
Niveau	Rôle	Base
28 communes de Bordeaux Métropole	Sujet principal : comparer les communes, trouver les priorités	CatNat (filtre libelle_epci)
Bordeaux Métropole entière	Évolution dans le temps	CatNat (épisodes comptés une seule fois)
Gironde, autres métropoles, France	Point de repère : Bordeaux est-elle plus ou moins touchée ?	CatNat (la base est nationale)
Gironde (département 33)	Climat de fond	Météo (stations, pas de commune)

Ta base CatNat est nationale (260 601 lignes). Elle te permet donc de répondre à ta question de départ, « Bordeaux comparée au reste de la France », sans autre base : tu compares le nombre moyen d’arrêtés par commune de Bordeaux Métropole avec celui des autres métropoles. Il faut ramener à la commune, car les métropoles n’ont pas le même nombre de communes.

Pourquoi ces deux bases
CatNat (le noyau) : source officielle, au niveau commune, depuis 1982, et elle parle directement de risques naturels. Elle donne l’exposition passée.
Météo (l’explication) : elle montre l’évolution du climat de 1954 à 2024. Elle relie les catastrophes à une cause.
Écartées : incendies (hors sujet pour la métropole, sauf éventuel graphique bonus sur la Gironde en 2022) et DVF (période incompatible).
Colonnes à garder
CatNat : code_geographique, libelle_geographique, libelle_epci, departement, type_catastrophe, date_debut, date_fin, date_arrete.
Météo : NUM_POSTE, NOM_USUEL, AAAAMM, puis un petit noyau selon le risque. Ignore toutes les colonnes Q... et ...DAT.
Chaleur : TX, NBJTX30, NBJTX35, NBJTNS20 (nuits chaudes).
Sécheresse : RR (pluie), ETP (évapotranspiration).
Pluies extrêmes : NBJRR30, NBJRR50 (jours de forte pluie).
Vent : une colonne de jours de vent fort (seuils à lire dans la doc Météo-France).
Trois précautions méthodologiques
Une ligne CatNat est un couple (commune, arrêté). Une inondation qui touche 20 communes fait 20 lignes. Pour compter les événements au niveau métropole, compte les épisodes distincts (type_catastrophe, date_debut, date_fin). Pour comparer les communes, compte les lignes.
CatNat mesure des événements reconnus administrativement, pas l’intensité physique. C’est un bon indicateur de l’exposition, mais pas une mesure exacte du danger. Précise-le sur le dashboard.
Les arrêtés récents sont publiés avec retard. 2024 et 2025 seront sous-estimés : arrête ta série CatNat à 2023 ou signale-le clairement.

À vérifier aussi : Sécheresse et Retrait-gonflement des argiles sont probablement deux libellés d’un même phénomène à des époques différentes. Trace leur nombre par année pour confirmer, puis fusionne-les en « Sécheresse / argiles » si c’est le cas. Garde les autres catégories rares (Avalanche, Grêle / neige, Divers) dans un groupe « Autres ».

Les graphiques, dans l’ordre de l’histoire
#	Graphique	Réponse apportée
1	Courbe des jours ≥ 30 °C par an (1954-2024), avec moyenne mobile sur 10 ans	Le climat se réchauffe
2	Pluie annuelle vs évapotranspiration, et jours de forte pluie	Sécheresses et pluies extrêmes évoluent-elles ?
3	Barres empilées : épisodes CatNat de la métropole par année et par type (1982-2023)	Quels risques reviennent, et se multiplient-ils ?
4	Barres : nombre moyen d’arrêtés par commune, Bordeaux Métropole vs Gironde vs autres métropoles vs France	Bordeaux est-elle plus exposée qu’ailleurs ?
5	Heatmap commune × type de catastrophe (28 communes)	Quelles communes sont touchées par quoi
6	Tableau final : pour chaque commune, risque dominant et mesure suggérée	Où agir en premier

Le graphique 5 est le cœur du dashboard : c’est lui qui répond à « où agir en priorité ». Une carte des 28 communes serait un bonus (il faut les contours communaux). Si tu veux relier le climat aux catastrophes, ajoute un nuage de points « jours de forte chaleur ou sécheresse vs nombre d’arrêtés sécheresse par année », en le présentant comme une corrélation exploratoire, pas une preuve de cause.

Ce que tu dois faire maintenant
Charger CatNat, filtrer la métropole, vérifier qu’il y a bien 28 communes.
Regrouper les types de catastrophe (sécheresse/argiles, inondations, tempêtes, mouvements de terrain, autres).
Préparer la météo annuelle (jours chauds, pluie, ETP) à partir de ta table mensuelle.