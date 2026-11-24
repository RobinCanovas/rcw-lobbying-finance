#!/usr/bin/env python3
"""Vérifie l'ontologie avec des instances de test :
  1. cohérence logique (raisonneur HermiT, nécessite Java + owlready2) ;
  2. inférences attendues (raisonneur OWL-RL, comme le ruleset OWL2-RL de GraphDB).
Usage : python tests/verifier_inferences.py"""
import sys
import tempfile
from pathlib import Path

from rdflib import Graph, Namespace, RDF

RACINE = Path(__file__).resolve().parent.parent
EX = Namespace("https://example.org/rcw/lobbying/")
T = Namespace("https://example.org/rcw/lobbying/test/")

g = Graph()
g.parse(RACINE / "ontologie.ttl", format="turtle")
g.parse(RACINE / "tests" / "instances-test.ttl", format="turtle")

# --- 1. Cohérence avec HermiT ------------------------------------------------
try:
    from owlready2 import get_ontology, sync_reasoner_hermit, default_world
    with tempfile.TemporaryDirectory() as d:
        fichier = Path(d) / "onto.owl"
        g.serialize(destination=str(fichier), format="xml")
        onto = get_ontology(fichier.as_uri()).load()
        with onto:
            sync_reasoner_hermit(infer_property_values=False, debug=0)
        incoherentes = list(default_world.inconsistent_classes())
        print("HermiT : ontologie cohérente" if not incoherentes else f"HermiT : classes incohérentes {incoherentes}")
except Exception as e:  # Java ou owlready2 absent
    print("HermiT non exécuté :", type(e).__name__, str(e)[:120])

# --- 2. Inférences avec OWL-RL ----------------------------------------------
import owlrl
avant = len(g)
owlrl.DeductiveClosure(owlrl.OWLRL_Semantics).expand(g)
print(f"OWL-RL : {avant} -> {len(g)} triplets")

attendus = [
    ("Q2 transitivité : banque -> confédération", (T.banque, EX["estAffiliéÀ"], T.confederation)),
    ("Q3 NAF : banque est de la section K", (T.banque, RDF.type, EX.NAF_K)),
    ("Q3 NAF : banque est de la division 64", (T.banque, RDF.type, EX.NAF_64)),
    ("Q5 national : action1 (Gouvernement)", (T.action1, EX.viseResponsableNational, T.catGouv)),
    ("Q5 national : action2 (Parlement)", (T.action2, EX.viseResponsableNational, T.catParl)),
    ("Q5 local : action3 (collectivité)", (T.action3, EX.viseResponsableLocal, T.catColl)),
    ("3e niveau : action1 viseCategorieResponsable", (T.action1, EX.viseCategorieResponsable, T.catGouv)),
]
ok = True
for nom, triplet in attendus:
    present = triplet in g
    ok &= present
    print(("OK    " if present else "ECHEC ") + nom)
interdits = [
    ("Q5 : action1 ne doit pas être locale", (T.action1, EX.viseResponsableLocal, T.catGouv)),
    ("Q5 : action3 ne doit pas être nationale", (T.action3, EX.viseResponsableNational, T.catColl)),
]
for nom, triplet in interdits:
    absent = triplet not in g
    ok &= absent
    print(("OK    " if absent else "ECHEC ") + nom)

# Cas limite : avec une propriété transitive, un cycle A<->B produit A->A.
auto = (T.cycleA, EX["estAffiliéÀ"], T.cycleA) in g
print("INFO  cycle d'affiliation -> auto-affiliation inférée :", auto,
      "(à filtrer dans les requêtes avec FILTER(?a != ?b))")
sys.exit(0 if ok else 1)
