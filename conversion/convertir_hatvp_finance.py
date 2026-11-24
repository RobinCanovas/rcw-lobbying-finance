#!/usr/bin/env python3
"""Convertit le JSON HATVP (organisations du secteur finance) en RDF/Turtle.

Entrée : JSON du répertoire des représentants d'intérêts (racine "publications").
Sortie : triplets à importer dans GraphDB. Sirene et Wikidata viennent après.

Choix de périmètre (voir la fiche projet) :
  - "finance" = organisations qui ont déclaré le secteur FINANCE
    (« Banques, assurances, secteur financier et extra financier ») ;
    on garde toutes leurs activités, quel que soit le domaine de chaque fiche.
  - les organisations vers lesquelles elles sont affiliées (fédérations,
    confédérations) sont ajoutées avec leur identité, sans leurs activités.

Exemples :
    python convertir_hatvp_finance.py agora_repertoire_opendata.json
    python convertir_hatvp_finance.py agora_repertoire_opendata.json --annees 2024 2025
"""
import argparse
from collections import deque
from hashlib import sha1
import json
from pathlib import Path
from urllib.parse import quote

from rdflib import Graph, Literal, Namespace, RDF, RDFS, XSD

EX = Namespace("https://example.org/rcw/lobbying/")

# --- Noms de l'ontologie : identiques à ceux de la fiche projet. ------------
# Pour renommer une propriété, il suffit de changer la ligne ici.
P_AFFILIE = EX["estAffiliéÀ"]
P_GOUVERNEMENT = EX["viseGouvernement"]
P_PARLEMENTAIRE = EX["viseParlementaire"]
P_COLLECTIVITE = EX["viseCollectivité"]

# --- Liste fermée des ministères (19 intitulés relevés dans le JSON). --------
# Le JSON donne les ministères dans un seul texte séparé par des virgules,
# et certains intitulés contiennent eux-mêmes une virgule : on ne peut donc
# pas faire un simple split(", "), on s'appuie sur cette liste.
MINISTERES = [
    "Premier ministre",
    "Economie et finances",
    "Environnement, énergie et mer",
    "Affaires sociales et santé",
    "Agriculture, agroalimentaire et forêt",
    "Travail, emploi, formation professionnelle et dialogue social",
    "Affaires étrangères et développement international",
    "Aménagement du territoire, ruralité et collectivités territoriales",
    "Culture et communication",
    "Education nationale, enseignement supérieur et recherche",
    "Logement",
    "Intérieur",
    "Justice",
    "Ville, jeunesse et sport",
    "Famille, enfance et droits des femmes",
    "Outre-mer",
    "Fonction publique",
    "Défense",
    "Autres : à préciser",
]
# Les plus longs d'abord, pour que « Environnement, énergie et mer »
# soit reconnu en entier.
MINISTERES_TRIES = sorted(MINISTERES, key=len, reverse=True)
# « Autres : à préciser » n'est pas un ministère : on n'en fait pas un nœud.
MINISTERE_AUTRE = "Autres : à préciser"

PREFIXE_GOUVERNEMENT = "Membre du Gouvernement ou membre de cabinet ministériel"
PREFIXE_PARLEMENT = "Député, sénateur"
PREFIXES_COLLECTIVITE = (
    "Élu ou membre de cabinet d'une collectivité territoriale",
    "Agent d'une collectivité territoriale",
)


def normaliser(texte):
    """Le JSON mélange l'apostrophe droite ' et l'apostrophe typographique ’."""
    return texte.replace("’", "'").strip()


def identite(organisation):
    """Clé stable HATVP : type d'identifiant + identifiant national."""
    t = str(organisation.get("typeIdentifiantNational") or "").strip().upper()
    n = str(organisation.get("identifiantNational") or "").strip()
    if t and n:
        return t, n
    nom = str(organisation.get("denomination") or "sans-nom").strip()
    return "NOM_HASH", sha1(nom.encode("utf-8")).hexdigest()[:16]


def uri_organisation(cle):
    t, n = cle
    return EX[f"organisation/{quote(t.lower(), safe='')}/{quote(n, safe='')}"]


def uri_valeur(categorie, libelle):
    empreinte = sha1(libelle.encode("utf-8")).hexdigest()[:16]
    return EX[f"{categorie}/{empreinte}"]


def chaine(valeur):
    return isinstance(valeur, str) and bool(valeur.strip())


def ajouter_libelle(g, ressource, libelle):
    if chaine(libelle):
        g.add((ressource, RDFS.label, Literal(libelle.strip(), lang="fr")))


def decouper_categorie(libelle):
    """Sépare « Catégorie - détail, détail » en (catégorie, détail ou None)."""
    libelle = normaliser(libelle)
    if " - " in libelle:
        categorie, detail = libelle.split(" - ", 1)
        return categorie.strip(), detail.strip()
    return libelle, None


def decouper_ministeres(texte):
    """Découpe « A, B, C » avec la liste fermée. Renvoie None si un morceau
    n'est pas reconnu (on le signale au lieu de le perdre en silence)."""
    restant = texte
    trouves = []
    while restant:
        for m in MINISTERES_TRIES:
            if restant == m or restant.startswith(m + ", "):
                trouves.append(m)
                restant = restant[len(m) + 2:]
                break
        else:
            return None
    return trouves


def propriete_niveau(categorie):
    """Sous-propriété utilisée pour Q5 ; None si la catégorie n'est pas
    classée national/local dans la fiche."""
    if categorie == PREFIXE_GOUVERNEMENT:
        return P_GOUVERNEMENT
    if categorie.startswith(PREFIXE_PARLEMENT):
        return P_PARLEMENTAIRE
    if categorie in PREFIXES_COLLECTIVITE:
        return P_COLLECTIVITE
    return None


def est_financiere(org):
    """FINANCE != FINANCES (qui désigne les finances publiques)."""
    secteurs = (org.get("activites") or {}).get("listSecteursActivites") or []
    return any(s.get("code") == "FINANCE" for s in secteurs)


def ajouter_profil(g, org, financiere=False):
    sujet = uri_organisation(identite(org))
    g.add((sujet, RDF.type, EX.Organisation))
    ajouter_libelle(g, sujet, org.get("denomination"))
    typ, numero = identite(org)
    if typ == "SIREN":
        g.add((sujet, EX.siren, Literal(numero)))
    elif typ == "RNA":
        g.add((sujet, EX.rna, Literal(numero)))
    elif typ == "HATVP":
        g.add((sujet, EX.identifiantHatvp, Literal(numero)))
    if financiere:
        secteur = EX["secteur/FINANCE"]
        g.add((secteur, RDF.type, EX.SecteurDeclare))
        ajouter_libelle(g, secteur, "Banques, assurances, secteur financier et extra financier")
        g.add((sujet, EX.secteurDeclare, secteur))
    return sujet


def ajouter_activites(g, org, annees, stats):
    sujet = uri_organisation(identite(org))
    id_org = "/".join(quote(s, safe="") for s in identite(org))
    for exercice in org.get("exercices") or []:
        publication = exercice.get("publicationCourante") or {}
        # Format vérifié : JJ-MM-AAAA. L'année de l'exercice = année de début.
        annee = str(publication.get("dateDebut") or "")[-4:]
        if annees and annee not in annees:
            continue
        for i, fiche_brute in enumerate(publication.get("activites") or []):
            fiche = fiche_brute.get("publicationCourante") or {}
            numero_fiche = quote(str(fiche.get("identifiantFiche") or f"sans-id-{i}"), safe="")
            uri_fiche = EX[f"activite/{id_org}/{annee}/{numero_fiche}"]
            g.add((uri_fiche, RDF.type, EX.ActiviteLobbying))
            g.add((sujet, EX.aDeclare, uri_fiche))
            # Entier et non xsd:gYear : HermiT (le raisonneur de Protégé) ne gère pas gYear.
            if annee.isdigit():
                g.add((uri_fiche, EX.annee, Literal(int(annee), datatype=XSD.integer)))
            if chaine(fiche.get("objet")):
                g.add((uri_fiche, RDFS.label, Literal(fiche["objet"].strip(), lang="fr")))
            stats["fiches"] += 1
            for domaine in fiche.get("domainesIntervention") or []:
                if chaine(domaine):
                    uri_domaine = uri_valeur("domaine", domaine)
                    g.add((uri_domaine, RDF.type, EX.DomaineIntervention))
                    ajouter_libelle(g, uri_domaine, domaine)
                    g.add((uri_fiche, EX.aPourDomaine, uri_domaine))
            for j, action in enumerate(fiche.get("actionsRepresentationInteret") or []):
                uri_action = EX[f"action/{id_org}/{annee}/{numero_fiche}/{j}"]
                g.add((uri_action, RDF.type, EX.ActionRepresentation))
                g.add((uri_fiche, EX.comporteAction, uri_action))
                stats["actions"] += 1
                # La clé s'écrit bien "reponsablesPublics" dans le JSON HATVP.
                for brut in set(action.get("reponsablesPublics") or []):
                    if not chaine(brut):
                        continue
                    categorie, detail = decouper_categorie(brut)
                    uri_cat = uri_valeur("categorie-responsable", categorie)
                    g.add((uri_cat, RDF.type, EX.CategorieResponsable))
                    ajouter_libelle(g, uri_cat, categorie)
                    g.add((uri_action, EX.viseCategorieResponsable, uri_cat))
                    sous_propriete = propriete_niveau(categorie)
                    if sous_propriete is not None:
                        g.add((uri_action, sous_propriete, uri_cat))
                    # Q1 : les ministères ne concernent que les membres du Gouvernement.
                    if categorie == PREFIXE_GOUVERNEMENT and detail:
                        ministeres = decouper_ministeres(detail)
                        if ministeres is None:
                            stats["ministeres_non_reconnus"].add(detail)
                            continue
                        for m in ministeres:
                            if m == MINISTERE_AUTRE:
                                continue
                            uri_min = uri_valeur("ministere", m)
                            g.add((uri_min, RDF.type, EX.Ministere))
                            ajouter_libelle(g, uri_min, m)
                            g.add((uri_action, EX.viseMinistere, uri_min))
                            stats["liens_ministeres"] += 1
                for decision in set(action.get("decisionsConcernees") or []):
                    if chaine(decision):
                        uri_decision = uri_valeur("type-decision", decision.strip())
                        g.add((uri_decision, RDF.type, EX.TypeDecision))
                        ajouter_libelle(g, uri_decision, decision)
                        g.add((uri_action, EX.concerneTypeDecision, uri_decision))
                for moyen in set(action.get("actionsMenees") or []):
                    if chaine(moyen):
                        g.add((uri_action, EX.moyenDeclare, Literal(moyen.strip(), lang="fr")))


def ajouter_affiliations(g, financieres, index, profondeur):
    """Remonte les affiliations (organisation -> fédération -> confédération)
    en suivant les identifiants, jamais les noms (risque d'homonymie).
    profondeur=None : on remonte toute la chaîne ; sinon on s'arrête à ce niveau.
    On n'importe que l'identité des organisations atteintes, pas leurs activités."""
    file = deque((identite(org), 0) for org in financieres)
    vus = set()
    nombre = 0
    while file:
        cle, distance = file.popleft()
        if cle in vus:
            continue
        vus.add(cle)
        if profondeur is not None and distance >= profondeur:
            continue
        org = index.get(cle)
        if org is None:
            continue
        sujet = uri_organisation(cle)
        for cible in org.get("affiliations") or []:
            if not cible.get("typeIdentifiantNational") or not cible.get("identifiantNational"):
                continue
            cle_cible = identite(cible)
            if cle_cible == cle:  # auto-affiliation déclarée par erreur
                continue
            org_cible = index.get(cle_cible)
            ajouter_profil(g, org_cible if org_cible else cible, est_financiere(org_cible) if org_cible else False)
            g.add((sujet, P_AFFILIE, uri_organisation(cle_cible)))
            nombre += 1
            if org_cible:
                file.append((cle_cible, distance + 1))
    return nombre


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("json_hatvp", type=Path, help="Fichier JSON source HATVP")
    parser.add_argument("--sortie", type=Path, default=Path("graphe-hatvp-finance.ttl"))
    parser.add_argument("--annees", nargs="+", default=None,
                        help="Années d'exercice à garder (défaut : toutes)")
    parser.add_argument("--max-organisations", type=int, default=None,
                        help="Limiter le nombre d'organisations pour un premier test")
    parser.add_argument("--profondeur-affiliations", type=int, default=None,
                        help="Niveaux d'affiliation à remonter (défaut : toute la chaîne)")
    args = parser.parse_args()

    with args.json_hatvp.open("r", encoding="utf-8") as fh:
        donnees = json.load(fh)
    publications = donnees.get("publications")
    if not isinstance(publications, list):
        raise ValueError("JSON non reconnu : tableau 'publications' absent")

    financieres = [o for o in publications if est_financiere(o)]
    financieres.sort(key=lambda o: (str(o.get("denomination") or ""), identite(o)))
    if args.max_organisations is not None:
        financieres = financieres[:args.max_organisations]
    index = {identite(org): org for org in publications}

    graphe = Graph()
    for prefixe, ns in (("ex", EX), ("rdf", RDF), ("rdfs", RDFS), ("xsd", XSD)):
        graphe.bind(prefixe, ns)

    stats = {"fiches": 0, "actions": 0, "liens_ministeres": 0, "ministeres_non_reconnus": set()}
    annees = set(args.annees) if args.annees else None
    for org in financieres:
        ajouter_profil(graphe, org, True)
        ajouter_activites(graphe, org, annees, stats)
    relations = ajouter_affiliations(graphe, financieres, index, args.profondeur_affiliations)

    args.sortie.parent.mkdir(parents=True, exist_ok=True)
    graphe.serialize(destination=str(args.sortie), format="turtle")
    print(f"Organisations financières sélectionnées : {len(financieres)}")
    print(f"Fiches d'activité retenues : {stats['fiches']}")
    print(f"Actions détaillées retenues : {stats['actions']}")
    print(f"Liens action -> ministère : {stats['liens_ministeres']}")
    print(f"Relations d'affiliation : {relations}")
    print(f"Triplets RDF produits : {len(graphe)}")
    print(f"Fichier créé : {args.sortie}")
    if stats["ministeres_non_reconnus"]:
        print(f"ATTENTION : {len(stats['ministeres_non_reconnus'])} liste(s) de ministères non reconnue(s) :")
        for texte in sorted(stats["ministeres_non_reconnus"])[:10]:
            print("   ", texte)
    print("IMPORTANT : ce fichier ne contient pas Sirene ni l'enrichissement Wikidata.")


if __name__ == "__main__":
    main()
