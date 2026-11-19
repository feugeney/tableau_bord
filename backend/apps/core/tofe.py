"""TOFE d'illustration autonome : montants inventés, structure documentée pour la Guinée.

Le scénario annuel est figé dans le journal du chargement. Aucun montant des
connecteurs métier n'est réutilisé ni présenté comme une consolidation réelle.
"""

import calendar
from datetime import date
from decimal import Decimal

from .domaines import chargements_actifs
from .models import Chargement
from .regles import taux

MD = Decimal(10**9)
D0 = Decimal(0)
POIDS_MENSUELS = (6, 6, 7, 7, 8, 8, 9, 9, 9, 9, 10, 12)
REFERENCES = [
    {
        "titre": "Ministère du Budget — publications TOFE",
        "url": "https://mbudget.gov.gn/tableau-des-operations-financieres-de-letat/",
        "usage": "Nomenclature et présentation nationale du tableau.",
    },
    {
        "titre": "DNPEC — Tableau de bord de l'économie, février 2025",
        "url": "https://www.mef.gov.gn/wp-content/uploads/2025/05/Tableau-de-Bord-Economie-fevrier-2025-.pdf",
        "usage": "Recettes, charges, actifs non financiers et suivi infra-annuel.",
    },
    {
        "titre": "BCRG — Politique monétaire, troisième trimestre 2025",
        "url": "https://www.bcrg-guinee.org/wp-content/uploads/2026/03/Rapport-CPM-du-2025T3.pdf",
        "usage": "Articulation des recettes, dépenses, soldes et financement.",
    },
    {
        "titre": "FMI — Guinée, rapport pays 24/130, tableau 3a",
        "url": "https://www.imf.org/-/media/files/publications/cr/2024/english/1ginea2024001.pdf",
        "usage": "Recettes minières/non minières, intérêts et financement net.",
    },
    {
        "titre": "DGI — adoption de la LFI 2026, 31 mars 2026",
        "url": "https://dgi.gov.gn/2026/03/31/adoption-de-la-loi-de-finance-initiales-lfi-2026/",
        "usage": "Contexte budgétaire 2026 ; aucun montant officiel repris dans le scénario.",
    },
]

# Montants annuels inventés en milliards GNF : LFI, LFR, exécution de scénario.
POSTES = [
    ("fiscal_minier", "Recettes fiscales minières", 2, (7200, 8000, 7600)),
    ("fiscal_non_minier", "Recettes fiscales non minières", 2, (30200, 31800, 30000)),
    ("autres_recettes", "Autres recettes non fiscales", 1, (3500, 3700, 3500)),
    ("dons_projets", "Dons-projets", 2, (2100, 2300, 2000)),
    ("dons_budget", "Dons budgétaires", 2, (500, 600, 500)),
    ("personnel", "Rémunération des salariés", 1, (11000, 11500, 11200)),
    ("biens_services", "Utilisation de biens et services", 1, (6500, 6700, 6100)),
    ("transferts", "Subventions et transferts courants", 1, (7800, 8000, 7500)),
    ("interets_interieurs", "Intérêts sur dette intérieure", 2, (2600, 2800, 2700)),
    ("interets_exterieurs", "Intérêts sur dette extérieure", 2, (900, 1000, 950)),
    ("investissement_interieur", "Actifs non financiers · financement intérieur", 1, (12500, 13500, 12500)),
    ("investissement_exterieur", "Actifs non financiers · financement extérieur", 1, (8500, 9500, 8400)),
    ("variation_arrieres", "Variation des arriérés · + accumulation / − apurement", 1, (-400, -500, -350)),
    ("bcrg", "Financement net BCRG", 2, (-500, -600, -500)),
    ("banques", "Financement net des banques commerciales", 2, (1400, 1700, 1200)),
    ("non_bancaire", "Financement intérieur non bancaire net", 2, (-900, -1600, -1300)),
    ("tirages_projets", "Tirages extérieurs sur prêts-projets", 2, (7000, 7800, 7000)),
    ("tirages_programmes", "Tirages extérieurs sur prêts-programmes", 2, (1300, 1600, 1400)),
    ("amortissement", "Amortissement du principal extérieur · à déduire", 2, (1600, 1800, 1700)),
]


def creer_scenario(exercice):
    # Facteur d'échelle purement fictif. Les montants conservent une précision exacte.
    facteur = Decimal("1.08") ** (exercice - 2026)
    return {
        "version": 1,
        "pib": str(Decimal(360000) * MD * facteur),
        "postes": {
            code: {k: str(Decimal(v) * MD * facteur) for k, v in zip(("lfi", "lfr", "annuel"), montants)}
            for code, _, _, montants in POSTES
        },
    }


def _fraction(jour, exercice):
    if jour < date(exercice, 1, 1):
        return D0
    if jour >= date(exercice, 12, 31):
        return Decimal(1)
    jours = calendar.monthrange(exercice, jour.month)[1]
    return (
        Decimal(sum(POIDS_MENSUELS[: jour.month - 1])) + Decimal(POIDS_MENSUELS[jour.month - 1]) * jour.day / jours
    ) / 100


def _calculer(v):
    """Identités explicites : les lignes parentes ne sont jamais additionnées aux enfants."""
    r = dict(v)
    r["recettes_fiscales"] = v["fiscal_minier"] + v["fiscal_non_minier"]
    r["recettes_hors_dons"] = r["recettes_fiscales"] + v["autres_recettes"]
    r["dons"] = v["dons_projets"] + v["dons_budget"]
    r["recettes_dons"] = r["recettes_hors_dons"] + r["dons"]
    r["interets"] = v["interets_interieurs"] + v["interets_exterieurs"]
    r["charges"] = sum((v[k] for k in ("personnel", "biens_services", "transferts")), D0) + r["interets"]
    r["actifs_non_financiers"] = v["investissement_interieur"] + v["investissement_exterieur"]
    r["depenses"] = r["charges"] + r["actifs_non_financiers"]
    r["solde_gestion"] = r["recettes_dons"] - r["charges"]
    r["solde_global"] = r["recettes_dons"] - r["depenses"]
    r["solde_primaire"] = r["solde_global"] + r["interets"]
    r["solde_caisse"] = r["solde_global"] + v["variation_arrieres"]
    r["besoin_financement"] = -r["solde_caisse"]
    r["financement_interieur"] = v["bcrg"] + v["banques"] + v["non_bancaire"]
    r["financement_exterieur"] = v["tirages_projets"] + v["tirages_programmes"] - v["amortissement"]
    r["financement"] = r["financement_interieur"] + r["financement_exterieur"]
    r["ecart_financement"] = r["besoin_financement"] - r["financement"]
    return r


AGREGATS = {
    "recettes_dons": ("A. Recettes et dons", 0),
    "recettes_hors_dons": ("Recettes hors dons", 1),
    "recettes_fiscales": ("Recettes fiscales", 1),
    "dons": ("Dons", 1),
    "charges": ("B. Charges courantes", 0),
    "interets": ("Intérêts de la dette", 1),
    "actifs_non_financiers": ("C. Acquisition nette d'actifs non financiers", 0),
    "depenses": ("D. Dépenses totales (B + C)", 0),
    "solde_gestion": ("Solde net de gestion (A − B)", 0),
    "solde_global": ("Solde global, dons compris (A − D)", 0),
    "solde_primaire": ("Solde primaire (solde global + intérêts)", 0),
    "solde_caisse": ("Solde base caisse simplifié", 0),
    "besoin_financement": ("E. Besoin (+) / capacité (−) de financement", 0),
    "financement_interieur": ("Financement intérieur net", 1),
    "financement_exterieur": ("Financement extérieur net", 1),
    "financement": ("F. Financement net total", 0),
    "ecart_financement": ("Besoin résiduel non financé (E − F)", 0),
}
ORDRE = (
    "recettes_dons recettes_hors_dons recettes_fiscales fiscal_minier fiscal_non_minier autres_recettes "
    "dons dons_projets dons_budget charges personnel biens_services transferts interets interets_interieurs "
    "interets_exterieurs actifs_non_financiers investissement_interieur investissement_exterieur depenses "
    "solde_gestion solde_global solde_primaire variation_arrieres solde_caisse besoin_financement financement "
    "financement_interieur bcrg banques non_bancaire financement_exterieur tirages_projets tirages_programmes "
    "amortissement ecart_financement"
).split()


def page(f):
    ch = Chargement.objects.filter(pk__in=chargements_actifs("tofe", f)).order_by("-fin", "-id").first()
    if not ch or ch.detail.get("profil") != "tofe_illustration_v1":
        return None
    scenario = ch.detail["scenario"]
    fraction = _fraction(f.date_situation, f.exercice)
    feuilles = scenario["postes"]
    colonnes = {
        "lfi": _calculer({k: Decimal(v["lfi"]) for k, v in feuilles.items()}),
        "lfr": _calculer({k: Decimal(v["lfr"]) for k, v in feuilles.items()}),
        "objectif_cumule": _calculer({k: Decimal(v["lfr"]) * fraction for k, v in feuilles.items()}),
        "realise": _calculer({k: Decimal(v["annuel"]) * fraction for k, v in feuilles.items()}),
        "realise_n1": _calculer({k: Decimal(v["annuel"]) * Decimal("0.90") * fraction for k, v in feuilles.items()}),
    }
    definitions = {k: (lib, niveau) for k, lib, niveau, _ in POSTES} | AGREGATS
    lignes = []
    for code in ORDRE:
        libelle, niveau = definitions[code]
        valeurs = {nom: colonne[code] for nom, colonne in colonnes.items()}
        signe = code in AGREGATS and (code.startswith("solde") or code in {"besoin_financement", "ecart_financement"})
        signe = (
            signe or code in {"variation_arrieres", "bcrg", "banques", "non_bancaire"} or code.startswith("financement")
        )
        lignes.append(
            {
                "code": code,
                "libelle": libelle,
                "niveau": niveau,
                "agregat": code in AGREGATS,
                **valeurs,
                "ecart": valeurs["realise"] - valeurs["objectif_cumule"],
                "taux": None if signe else taux(valeurs["realise"], valeurs["objectif_cumule"]),
            }
        )
    r = colonnes["realise"]
    mensuel = []
    dernier_mois = min(f.date_situation, date(f.exercice, 12, 31)).month
    for mois in range(1, dernier_mois + 1):
        fin = min(f.date_situation, date(f.exercice, mois, calendar.monthrange(f.exercice, mois)[1]))
        avant = date(f.exercice, mois, 1)
        cumul_avant = Decimal(sum(POIDS_MENSUELS[: mois - 1])) / 100
        part = _fraction(fin, f.exercice) - cumul_avant
        valeurs = _calculer({k: Decimal(v["annuel"]) * part for k, v in feuilles.items()})
        mensuel.append(
            {"mois": avant.isoformat(), **{k: valeurs[k] for k in ("recettes_dons", "depenses", "solde_global")}}
        )
    verifications = [
        {
            "libelle": "Recettes et dons − dépenses = solde global",
            "ecart": r["recettes_dons"] - r["depenses"] - r["solde_global"],
        },
        {
            "libelle": "Solde global + variation des arriérés = solde caisse",
            "ecart": r["solde_global"] + r["variation_arrieres"] - r["solde_caisse"],
        },
        {"libelle": "Besoin de financement − financement net", "ecart": r["ecart_financement"]},
        {
            "libelle": "Somme des recettes mensuelles = cumul présenté",
            "ecart": sum((m["recettes_dons"] for m in mensuel), D0) - r["recettes_dons"],
        },
    ]
    for controle in verifications:
        # Decimal : tolérance d'un centime uniquement pour les divisions infra-mensuelles.
        controle["reussi"] = abs(controle["ecart"]) < Decimal("0.01")
    return {
        "indicateurs": {
            **{
                k: r[k]
                for k in (
                    "recettes_dons",
                    "depenses",
                    "solde_global",
                    "solde_primaire",
                    "solde_caisse",
                    "besoin_financement",
                    "financement",
                    "ecart_financement",
                )
            },
            "pib": Decimal(scenario["pib"]),
            "ratio_solde_pib": taux(r["solde_global"], Decimal(scenario["pib"])),
            "pression_fiscale": taux(r["recettes_fiscales"], Decimal(scenario["pib"])),
            "taux_recettes": taux(r["recettes_dons"], colonnes["objectif_cumule"]["recettes_dons"]),
            "taux_depenses": taux(r["depenses"], colonnes["objectif_cumule"]["depenses"]),
        },
        "lignes": lignes,
        "mensuel": mensuel,
        "verifications": verifications,
        "references": REFERENCES,
        "perimetre": "Administration centrale budgétaire · scénario autonome entièrement fictif · GNF.",
        "methode": (
            "Les LFI, LFR, réalisations et le PIB sont simulés ; aucun chiffre officiel n'est reproduit. "
            "L'objectif cumulé suit un profil mensuel pédagogique commun, proratisé au jour de la situation. "
            "N−1 compare une période équivalente simulée. Un solde négatif désigne un déficit ; "
            "un financement positif apporte une ressource nette. L'amortissement est déduit des tirages. "
            "La variation des arriérés est positive en accumulation et négative en apurement. "
            "Le solde caisse est simplifié : les autres ajustements et les acquisitions nettes d'actifs "
            "financiers sont supposés nuls. Les ratios au PIB utilisent un PIB annuel fictif. "
            "Aucun lien automatique avec les données réelles SYSOP ou de dépenses."
        ),
    }
