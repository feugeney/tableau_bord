"""Vue « Toute la chaîne, titre par titre », fiche d'un titre et dossiers en attente de visa.

Repris de la note à Madame la Ministre (vues 1 et 2) :
- vue 1 : les cinq titres, crédits, engagé, payé (chaîne) et un voyant qui rapporte l'engagé au
  temps écoulé de l'exercice ;
- vue 2 : pour un titre, la chaîne complète, les ministères aux plus gros crédits, les acteurs
  (DGCMP, contrôle financier, Trésor, DGIP) et les alertes du titre.

Le payé est celui de la Chaîne Dépense (montant brut enregistré). Pour les titres dont le paiement
n'est pas suivi dans la chaîne (dette, débit d'office), aucun taux de paiement n'est affiché.
"""

from __future__ import annotations

import hashlib
import re
import statistics
from dataclasses import replace
from datetime import date
from decimal import Decimal
from typing import Optional

from apps.core import regles
from apps.core.domaines import chargements_actifs
from apps.core.filtres import Filtres
from apps.referentiels.models import NATURE_VERS_TITRE, TITRES

from . import services

D0 = Decimal(0)
TITRE_VERS_NATURE = {t: n for n, t in NATURE_VERS_TITRE.items()}
# Procédures passées par marché public : libellés du référentiel se terminant par « MP ».
MARCHE_PUBLIC = re.compile(r"\bMP\b")
# États d'un engagement qui n'attend plus de visa (abandonné, rejeté).
ETATS_CLOS = ("abandon", "rejet")
NB_MINISTERES = 6


def libelle_titre(code: str) -> str:
    return f"T{code} · {TITRES.get(code, code)}"


def _filtres_titre(f: Filtres, titre: str) -> Filtres:
    return replace(f, nature=TITRE_VERS_NATURE[titre])


# ------------------------------------------------------------------ vue 1


def titres(f: Filtres) -> dict:
    temps = regles.temps_ecoule_exercice(f.exercice, f.date_situation)
    non_suivis = regles.titres_paiement_non_suivi()
    lignes = []
    for n in services.natures(f):
        suivi = n["titre"] not in non_suivis
        lignes.append(
            {
                **n,
                "libelle_titre": libelle_titre(n["titre"]),
                "paiement_suivi": suivi,
                "taux_paiement": regles.taux(n["montant_paye"], n["credit_actuel"]) if suivi else None,
                "voyant": regles.voyant_titre(n["taux_engagement"], temps) if suivi else None,
            }
        )
    return {"temps_ecoule": temps, "titres": lignes}


# ------------------------------------------------------------------ vue 2


def _engagements(f: Filtres):
    from .models import FaitEngagement
    from .pilotage import perimetre

    return perimetre(FaitEngagement, f, chargements_actifs("chaine_depense", f))


def delais_visa(f: Filtres, seuil_jours: int) -> dict:
    """Création → visa du contrôle financier, sur les engagements visés à la date de situation."""
    jours = sorted(
        (r["date_visa_cf"] - r["date_creation"]).days
        for r in _engagements(f)
        .exclude(date_creation=None)
        .exclude(date_visa_cf=None)
        .values("date_creation", "date_visa_cf")
        if r["date_visa_cf"] <= f.date_situation and r["date_visa_cf"] >= r["date_creation"]
    )
    if not jours:
        return {"nb_vises": 0, "mediane_jours": None, "part_au_dela": None, "seuil_jours": seuil_jours}
    return {
        "nb_vises": len(jours),
        "mediane_jours": statistics.median(jours),
        "p90_jours": jours[max(0, (9 * len(jours) + 9) // 10 - 1)],
        "part_au_dela": regles.taux(sum(j > seuil_jours for j in jours), len(jours)),
        "seuil_jours": seuil_jours,
    }


def dossiers_en_attente_visa(
    f: Filtres, delai_jours: int, montant_min: Decimal | int = 0, etats_exclus=ETATS_CLOS
) -> list[dict]:
    """Engagements sans visa du contrôle financier depuis plus de `delai_jours` (hors procédures payées
    hors chaîne et états clos), du plus ancien au plus récent."""
    if not f.date_situation:
        return []
    qs = _engagements(f).filter(date_visa_cf=None).exclude(type_procedure__paiement_hors_chaine=True)
    for motif in etats_exclus:
        qs = qs.exclude(etat_dossier__libelle__icontains=motif)
    if montant_min:
        qs = qs.filter(montant_engage__gte=montant_min)
    noms = services._libelles_sections(f)
    sortie = []
    for r in qs.values(
        "numero",
        "section_id",
        "titre",
        "cle_imputation",
        "beneficiaire_brut",
        "beneficiaire__nom_affiche",
        "objet",
        "montant_engage",
        "date_creation",
        "date_etat",
        "etat_dossier__libelle",
        "type_procedure__libelle",
        "sous_section_id",
        "sous_section__libelle",
        "chapitre",
        "article",
        "paragraphe",
        "attributs",
    ):
        depuis: Optional[date] = r["date_creation"] or r["date_etat"]
        if not depuis or depuis > f.date_situation:
            continue
        jours = (f.date_situation - depuis).days
        if jours <= delai_jours:
            continue
        cle = f"{r['section_id']}|{r['titre']}|{r['numero'].strip()}|{r['cle_imputation']}"
        sortie.append(
            {
                "cle": hashlib.sha1(cle.encode()).hexdigest(),
                "numero": r["numero"].strip(),
                "section": r["section_id"],
                "ministere": noms.get(r["section_id"], {}).get("libelle_court", r["section_id"]),
                "titre": r["titre"],
                "libelle_titre": libelle_titre(r["titre"]),
                "beneficiaire": (r["beneficiaire__nom_affiche"] or r["beneficiaire_brut"] or "").strip(),
                "objet": (r["objet"] or "").strip(),
                "montant": r["montant_engage"],
                "depuis": depuis,
                "jours": jours,
                "etat": (r["etat_dossier__libelle"] or "").strip(),
                "etape": "Visa du contrôle financier",
                "acteur": "Contrôle financier",
                "procedure": (r["type_procedure__libelle"] or "").strip(),
                "service": (
                    (r["attributs"] or {}).get("libelle_sous_section") or r["sous_section__libelle"] or ""
                ).strip(),
                "sous_section": r["sous_section_id"] or "",
                "imputation": ".".join(p for p in (r["titre"], r["chapitre"], r["article"], r["paragraphe"]) if p),
                "date_creation": r["date_creation"],
                "date_etat": r["date_etat"],
            }
        )
    sortie.sort(key=lambda d: (-d["jours"], -d["montant"]))
    return sortie


def _sgpip() -> dict:
    from apps.core.models import Chargement, Source

    source = Source.objects.filter(code="sgpip").first()
    raccorde = bool(source) and Chargement.objects.filter(source=source, statut="succes").exists()
    return {"raccorde": raccorde, "application": source.application if source else "SGPIP"}


def titre_detail(f: Filtres, titre: str) -> dict:
    fs = _filtres_titre(f, titre)
    suivi = titre not in regles.titres_paiement_non_suivi()
    t = services._totaux(fs)[0]
    credits = t["credit_actuel"]
    chaine = [
        {"code": code, "libelle": libelle, "montant": montant, "taux": regles.taux(montant, credits)}
        for code, libelle, montant in (
            ("credits", "Crédits", credits),
            ("engage", "Engagé", t["credit_engage"]),
            ("liquide", "Liquidé", t["montant_liquide"]),
            ("ordonnance", "Ordonnancé", t["montant_ordonnance"]),
            ("paye", "Payé", t["montant_paye"] if suivi else None),
        )
    ]

    noms = services._libelles_sections(f)
    par_section = sorted(services._totaux(fs, group_by="section_code"), key=lambda r: r["credit_actuel"], reverse=True)
    ministeres = [
        {
            "code": r["section_code"],
            "libelle": noms.get(r["section_code"], {}).get("libelle_court", r["section_code"]),
            "credit_actuel": r["credit_actuel"],
            "credit_engage": r["credit_engage"],
            "montant_paye": r["montant_paye"],
            "taux_engagement": regles.taux(r["credit_engage"], r["credit_actuel"]),
            "taux_paiement": regles.taux(r["montant_paye"], r["credit_actuel"]) if suivi else None,
        }
        for r in par_section[:NB_MINISTERES]
    ]

    acteurs = []
    procedures = services.procedures(fs)
    engage_total = sum((p["montant_engage"] for p in procedures), D0)
    engage_mp = sum((p["montant_engage"] for p in procedures if MARCHE_PUBLIC.search(p["procedure"])), D0)
    acteurs.append(
        {
            "code": "dgcmp",
            "acteur": "DGCMP · Télémo",
            "voyant": None,
            "texte": (
                f"{_pct(regles.taux(engage_mp, engage_total))} des engagements avec marché public"
                if engage_total
                else "Aucun engagement sur ce titre"
            ),
            "valeur": regles.taux(engage_mp, engage_total),
        }
    )
    seuil = int(regles.parametre("visa_cf_delai_max_jours"))
    visa = delais_visa(fs, seuil)
    voyant_cf = None
    if visa["mediane_jours"] is not None:
        voyant_cf = (
            "critique" if visa["mediane_jours"] > seuil else ("vigilance" if visa["p90_jours"] > seuil else "bon")
        )
    acteurs.append(
        {
            "code": "controle_financier",
            "acteur": "Contrôle financier",
            "voyant": voyant_cf,
            "texte": (
                f"Visa : {_jours(visa['mediane_jours'])} médians, {_pct(visa['part_au_dela'])} au-delà de {seuil} jours"
                if visa["nb_vises"]
                else "Aucun visa daté sur ce titre"
            ),
            "valeur": visa,
        }
    )
    if suivi:
        paye_ordo = regles.taux(t["montant_paye"], t["montant_ordonnance"])
        acteurs.append(
            {
                "code": "tresor",
                "acteur": "Trésor",
                "voyant": regles.voyant_paiement(paye_ordo),
                "texte": f"{_mds(t['montant_paye'])} payés sur {_mds(t['montant_ordonnance'])} ordonnancés",
                "valeur": paye_ordo,
            }
        )
    else:
        acteurs.append(
            {
                "code": "tresor",
                "acteur": "Trésor",
                "voyant": None,
                "texte": "Paiement hors chaîne (débit d'office) : non suivi ici",
                "valeur": None,
            }
        )
    if titre == str(regles.parametre("titre_investissement")):
        sgpip = _sgpip()
        acteurs.append(
            {
                "code": "dgip",
                "acteur": "DGIP · SGPIP",
                "voyant": None,
                "texte": (
                    "Décaissements et entrée en vigueur des projets : données reçues"
                    if sgpip["raccorde"]
                    else "Non raccordé : décaissements, entrée en vigueur et clôture des projets à venir"
                ),
                "raccorde": sgpip["raccorde"],
                "valeur": None,
            }
        )

    alertes = []
    credits_min = regles.parametre("sous_execution_credits_min")
    for r in par_section:
        if r["credit_actuel"] >= Decimal(str(credits_min)) and not r["credit_engage"]:
            nom = noms.get(r["section_code"], {}).get("libelle_court", r["section_code"])
            alertes.append(
                {"severite": "critique", "texte": f"Crédits de {nom} non engagés ({_mds(r['credit_actuel'])})"}
            )
    attente = dossiers_en_attente_visa(fs, seuil)
    if attente:
        alertes.append(
            {
                "severite": "serieux",
                "texte": (
                    f"{len(attente)} dossier(s) en attente de visa au-delà de {seuil} jours, pour "
                    f"{_mds(sum((d['montant'] for d in attente), D0))}"
                ),
            }
        )
    return {
        "titre": titre,
        "libelle_titre": libelle_titre(titre),
        "paiement_suivi": suivi,
        "chaine": chaine,
        "ministeres": ministeres,
        "nb_ministeres": len(par_section),
        "acteurs": acteurs,
        "alertes": alertes,
    }


# ------------------------------------------------------------------ formats des textes


def _pct(t) -> str:
    return "—" if t is None else f"{round(Decimal(t) * 100):.0f} %"


def _mds(montant) -> str:
    from apps.core.alertes import mds

    return mds(montant)


def _jours(j) -> str:
    if j is None:
        return "—"
    j = Decimal(str(j))
    texte = f"{j:.0f}" if j == j.to_integral_value() else f"{j:.1f}".replace(".", ",")
    return f"{texte} jour" if j <= 1 else f"{texte} jours"
