#!/usr/bin/env python3
"""Exécute les requêtes Q1, Q2, Q3 et Q5 sur les instances de test, sans puis avec
raisonneur, pour vérifier que les requêtes (b) n'ont de réponse complète
qu'avec l'inférence. Usage : python tests/tester_requetes.py"""
import sys
from pathlib import Path
import owlrl
from rdflib import Graph

RACINE = Path(__file__).resolve().parent.parent

def charger():
    g = Graph()
    g.parse(RACINE / "ontologie.ttl", format="turtle")
    g.parse(RACINE / "tests" / "instances-test.ttl", format="turtle")
    return g

def lancer(g, fichier):
    texte = (RACINE / "requetes" / fichier).read_text(encoding="utf-8").replace("662042449", "000000000")
    return [tuple(str(v) for v in r) for r in g.query(texte)]

sans = charger()
avec = charger()
owlrl.DeductiveClosure(owlrl.OWLRL_Semantics).expand(avec)

ok = True
def verifier(nom, condition):
    global ok
    ok &= condition
    print(("OK    " if condition else "ECHEC ") + nom)

q1 = lancer(sans, "q1_ministeres_categories_decisions.rq")
verifier(f"Q1 sans inférence : {len(q1)} lignes (ministère, catégorie, décision)", len(q1) == 3)
for fichier, nom, attendu_sans, attendu_avec in [
    ("q2_federations_directes_indirectes.rq", "Q2", 1, 2),
    ("q3_organisations_finance.rq", "Q3", 0, 1),
]:
    a, b = lancer(sans, fichier), lancer(avec, fichier)
    verifier(f"{nom} : {len(a)} réponse(s) sans inférence, {len(b)} avec", (len(a), len(b)) == (attendu_sans, attendu_avec))
q5_sans, q5_avec = lancer(sans, "q5_nationaux_ou_locaux.rq"), lancer(avec, "q5_nationaux_ou_locaux.rq")
verifier(f"Q5 : {len(q5_sans)} ligne(s) sans inférence, {len(q5_avec)} avec", (len(q5_sans), len(q5_avec)) == (0, 1))
sys.exit(0 if ok else 1)
