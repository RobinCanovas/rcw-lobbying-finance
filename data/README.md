# Données d'origine

Les fichiers bruts ne sont pas versionnés (le JSON HATVP fait environ 136 Mo, au-delà de la limite de 100 Mo de GitHub). Pour les reproduire, placer les fichiers dans `data/raw/`.

## Répertoire des représentants d'intérêts (HATVP)

- Page du jeu de données : https://www.data.gouv.fr/datasets/repertoire-des-representants-dinterets
- Téléchargement direct du JSON : https://www.data.gouv.fr/api/1/datasets/r/46cd8d72-dd5e-4198-88b5-ab95702ba6dd
- Fichier à enregistrer sous le nom `data/raw/agora_repertoire_opendata.json`
- Licence : Licence Ouverte (Etalab)
- Fichier utilisé pour le développement : récupéré le 22/11/2026, 4 123 organisations, environ 113 500 activités (exercices 2018 à 2026)
- SHA-256 de ce fichier : `0545f8b58d52f5ab62b3c2411e7ed1a59909054419caea2b55f474b1d00448d0`
- Le fichier évolue (mise à jour quotidienne) : les chiffres peuvent différer sur une version plus récente.
- Les dirigeants, collaborateurs, mails et téléphones du JSON sont des données de personnes physiques : ils ne sont pas convertis en RDF.

## Base Sirene (INSEE) — à venir

- Page du jeu de données : https://www.data.gouv.fr/datasets/base-sirene-des-entreprises-et-de-leurs-etablissements-siren-siret
- Fichier utile : le stock des unités légales (Parquet)
- Licence : Licence Ouverte 2.0 (Etalab)

## Nomenclature d'activités française, NAF rév. 2 (INSEE) — à venir

- Page : https://insee.fr/fr/information/2120875
- Fichier : https://www.insee.fr/fr/statistiques/fichier/2120875/naf2008_5_niveaux.xls
- Licence : Licence Ouverte 2.0 (Etalab), source Insee, publication du 08/03/2021
