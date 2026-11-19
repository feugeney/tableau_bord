"""KPI complémentaires, calculés sur un seul instantané actif et sans addition des grains."""

from collections import defaultdict
from decimal import Decimal
from statistics import median

from django.db.models import Count, Q, Sum

from apps.core.domaines import chargements_actifs
from apps.core.models import Chargement
from apps.core.regles import taux

from .criteres import extra_orm
from .models import FaitAPAD, FaitEngagement, FaitRegie, FaitSituationLigne
from .services import _libelles_sections

ZERO = Decimal(0)
IMPUTATION = (
    "type_budget",
    "section_id",
    "sous_section_id",
    "titre",
    "chapitre",
    "article",
    "paragraphe",
    "sous_paragraphe",
    "source_financement",
    "groupe_bailleur",
    "bailleur",
)
MESURES = (
    "credit_actuel",
    "credit_engage",
    "credit_disponible",
    "credit_reserve",
    "montant_bloque",
    "avance_demarrage",
    "montant_liquide",
    "montant_ordonnance",
    "montant_vbp",
    "montant_paye",
)
PHASES = (
    ("Engagé", "credit_engage", "montant_engage"),
    ("Liquidé", "montant_liquide", "montant_liquide"),
    ("Ordonnancé", "montant_ordonnance", "montant_ordonnance"),
    ("VBP", "montant_vbp", "montant_vbp"),
    ("Payé enregistré", "montant_paye", "montant_paye"),
)


def perimetre(modele, f, ids):
    qs = modele.objects.filter(chargement_id__in=ids, exercice=f.exercice, date_situation=f.date_situation)
    if f.section:
        qs = qs.filter(section_id=f.section)
    if f.titre:
        qs = qs.filter(titre=f.titre)
    # Critères multiples de la page (ministère, programme, zone…), mêmes règles que les autres blocs.
    # Hors lignes budgétaires (engagements, APAD, régies) : critères lus via la ligne de même imputation.
    extra = extra_orm(f, f'"{modele._meta.db_table.split(chr(34))[-1]}"', engagement=modele is not FaitSituationLigne)
    if extra:
        qs = qs.extra(where=extra[0], params=extra[1])
    return qs


def cle(row):
    # Programme et nature de flux sont présents dans les deux vues Oracle ; la régulation
    # absente de la liste des engagements ne peut pas être inventée pour le rapprochement.
    return tuple(row.get(c) or "" for c in IMPUTATION) + tuple(
        row["attributs"].get(c, "") for c in ("programme", "nature_flux")
    )


def page(f):
    ids = chargements_actifs("chaine_depense", f)
    charges = {c.pk: c for c in Chargement.objects.filter(pk__in=ids)}
    situation = list(perimetre(FaitSituationLigne, f, ids).values(*IMPUTATION, *MESURES, "attributs", "chargement_id"))
    engagements = list(
        perimetre(FaitEngagement, f, ids).values(
            *IMPUTATION,
            "attributs",
            "montant_engage",
            "montant_liquide",
            "montant_ordonnance",
            "montant_vbp",
            "montant_paye",
            "date_creation",
            "date_visa_cf",
            "date_visa_ministre",
            "chargement_id",
        )
    )

    def connue(ch, onglet, champ, rows):
        if champ in ch.detail.get("indicateurs_indisponibles", []):
            return False
        colonnes = ch.detail.get("colonnes_extraites", {}).get(onglet)
        if colonnes is not None:
            return champ in colonnes
        # Les anciens imports ne conservent pas tous leur manifeste. Une valeur non nulle
        # atteste la présence de la mesure ; un ensemble de zéros ne le prouve pas.
        return champ in {
            "credit_actuel",
            "credit_engage",
            "montant_ordonnance",
            "montant_paye",
            "montant_liquide",
        } or any(r.get(champ, ZERO) != ZERO for r in rows if r["chargement_id"] == ch.pk)

    def somme_sc(champ):
        if not charges or not all(connue(ch, "situation", champ, situation) for ch in charges.values()):
            return None
        if any(champ in r["attributs"].get("_mesures_absentes", []) for r in situation):
            return None
        return sum((r[champ] for r in situation), ZERO)

    disponibilite = {
        m: somme_sc(m)
        for m in ("credit_actuel", "credit_engage", "credit_disponible", "credit_reserve", "montant_bloque")
    }
    actuel, engage = disponibilite["credit_actuel"], disponibilite["credit_engage"]
    disponibilite["credits_non_engages"] = actuel - engage if actuel is not None and engage is not None else None
    composants = [disponibilite[m] for m in ("credit_actuel", "credit_engage", "credit_reserve", "montant_bloque")]
    disponibilite["disponible_reconstitue"] = (
        composants[0] - sum(composants[1:]) if all(v is not None for v in composants) else None
    )
    source, reconstitue = disponibilite["credit_disponible"], disponibilite["disponible_reconstitue"]
    disponibilite["ecart_disponibilite"] = (
        source - reconstitue if source is not None and reconstitue is not None else None
    )
    disponibilite["part_immobilisee"] = (
        taux(disponibilite["credit_reserve"] + disponibilite["montant_bloque"], actuel)
        if all(disponibilite[m] is not None for m in ("credit_reserve", "montant_bloque", "credit_actuel"))
        else None
    )
    disponibilite["methode"] = (
        "Disponible reconstitué = crédits actuels − engagé − réservé − bloqué. À rapprocher du disponible source."
    )

    delais = []
    for libelle, debut, fin in (
        ("Création → visa CF", "date_creation", "date_visa_cf"),
        ("Visa CF → visa ministre", "date_visa_cf", "date_visa_ministre"),
    ):
        paires = [
            (r[fin] - r[debut]).days
            for r in engagements
            if r[debut] and r[fin] and r[debut] <= f.date_situation and r[fin] <= f.date_situation
        ]
        valides = [j for j in paires if j >= 0]
        dates_invalides = sum(
            bool((r[debut] and r[debut] > f.date_situation) or (r[fin] and r[fin] > f.date_situation))
            for r in engagements
        )
        delais.append(
            {
                "libelle": libelle,
                "nb_engagements": len(engagements),
                "paires_valides": len(valides),
                "couverture": taux(len(valides), len(engagements)),
                "mediane_jours": median(valides) if valides else None,
                "p90_jours": sorted(valides)[max(0, (9 * len(valides) + 9) // 10 - 1)] if valides else None,
                "delais_negatifs": sum(j < 0 for j in paires),
                "dates_futures": dates_invalides,
                "sans_date_fin": sum(r[fin] is None for r in engagements),
            }
        )

    rapprochements = []
    for libelle, mesure_sc, mesure_eng in PHASES:
        budget, detail, brut = defaultdict(Decimal), defaultdict(Decimal), ZERO
        for r in situation:
            budget[cle(r)] += r[mesure_sc]
        for r in engagements:
            brut += r[mesure_eng]
            ctrl = charges[r["chargement_id"]].detail.get("rapprochement_engage", {})
            exclure = (
                mesure_sc == "credit_engage"
                and ctrl.get("cles_en_ecart") == 0
                and (
                    r["attributs"].get("code_etat_dossier") == "E9N"
                    or r["attributs"].get("code_type_procedure") == "52"
                )
            )
            if not exclure:
                detail[cle(r)] += r[mesure_eng]
        valeur_sc = somme_sc(mesure_sc)
        total = sum(detail.values(), ZERO)
        ecarts = [budget[k] - detail[k] for k in budget.keys() | detail.keys() if budget[k] != detail[k]]
        rapprochements.append(
            {
                "libelle": libelle,
                "reference": valeur_sc,
                "detail_brut": brut,
                "detail_comparable": total,
                "ecart": valeur_sc - total if valeur_sc is not None else None,
                "cles_en_ecart": len(ecarts) if valeur_sc is not None else None,
                "ecart_absolu": sum(map(abs, ecarts), ZERO) if valeur_sc is not None else None,
                "perimetre": (
                    "Hors E9N et procédure 52, règle validée à l'import"
                    if brut != total
                    else "Toutes les lignes reçues"
                ),
            }
        )

    apad_qs = perimetre(FaitAPAD, f, ids)
    apad_connue = bool(charges) and all(
        ch.detail.get("comptes", {}).get("apad", {}).get("chargees", 0) > 0 for ch in charges.values()
    )
    apad_total = apad_qs.aggregate(total=Sum("avance_demarrage"))["total"] or ZERO
    apad_absents = apad_qs.filter(montant_absent=True).count()
    apad_total = apad_total if apad_connue and not apad_absents else None
    avance_sc = somme_sc("avance_demarrage")
    noms = _libelles_sections(f)
    ministeres = (
        list(
            apad_qs.values("section_id")
            .annotate(montant=Sum("avance_demarrage"), absents=Count("id", filter=Q(montant_absent=True)))
            .order_by("-montant")
        )
        if apad_connue
        else []
    )
    for m in ministeres:
        m["libelle"] = noms.get(m["section_id"], {}).get("libelle_court", m["section_id"])
        if m.pop("absents"):
            m["montant"] = None
    dossiers = (
        list(
            apad_qs.order_by("section_id", "gestionnaire", "numero_apad", "ligne_source").values(
                "section_id",
                "gestionnaire",
                "numero_apad",
                "numero_marche",
                "sous_section_id",
                "libelle_projet",
                "avance_demarrage",
                "montant_absent",
                "date_creation",
            )
        )
        if apad_connue
        else []
    )
    for ligne in dossiers:
        ligne["ministere"] = noms.get(ligne["section_id"], {}).get("libelle", ligne["section_id"])
        if ligne.pop("montant_absent"):
            ligne["avance_demarrage"] = None
    apad = {
        "renseigne": apad_connue,
        "nb_lignes": apad_qs.count() if apad_connue else None,
        "nb_marches": (
            apad_qs.exclude(numero_marche="").values("gestionnaire", "numero_marche").distinct().count()
            if apad_connue
            else None
        ),
        "avance_demarrage": apad_total,
        "montants_absents": apad_absents,
        "reference": avance_sc,
        "ecart": apad_total - avance_sc if apad_total is not None and avance_sc is not None else None,
        "ministeres": ministeres,
        "dossiers": dossiers,
        "precision": "Avances enregistrées ; paiement et apurement non établis par cet export.",
    }
    regies = perimetre(FaitRegie, f, ids)
    regies_connues = bool(charges) and all(
        ch.detail.get("comptes", {}).get("regie", {}).get("chargees", 0) > 0 for ch in charges.values()
    )
    return {
        "disponibilite": disponibilite,
        "delais": delais,
        "rapprochements": rapprochements,
        "apad": apad,
        "regies": {
            "nb_lignes": regies.count() if regies_connues else None,
            "montant_regie": (
                (regies.aggregate(total=Sum("montant_regie"))["total"] or ZERO) if regies_connues else None
            ),
        },
    }
