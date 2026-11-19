"""Export Excel des pages : GET /api/v1/export/<page>.xlsx (mêmes filtres que la page).

Chaque classeur contient une feuille « Lisez-moi » (en-tête officiel, exercice, date de situation,
source et statut de chaque feuille, mention « diffusion restreinte ») puis une feuille par bloc.
Montants en milliards de GNF, taux en pourcentage. Droits : `peut_exporter` du domaine ; export journalisé.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from importlib import import_module
from io import BytesIO
from typing import Any

from django.http import HttpResponse
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.views import APIView

from .audit import journaliser
from .domaines import filtres_source
from .filtres import resoudre_filtres
from .models import Domaine, JournalAudit
from .permissions import DoubleAuthentification
from .reponses import PARAMETRES_COMMUNS, meta

# page : (domaine, source principale, titre)
PAGES = {
    "tofe": (Domaine.TOFE, "tofe", "TOFE — données d'illustration"),
    "synthese": (Domaine.SYNTHESE, "chaine_depense", "Synthèse"),
    "depenses": (Domaine.DEPENSE, "chaine_depense", "Dépenses"),
    "investissements": (Domaine.INVESTISSEMENT, "chaine_depense", "Investissements"),
    "recettes-fiscales": (Domaine.RECETTES_FISCALES, "safig", "Recettes fiscales"),
    "recettes-douanieres": (Domaine.DOUANES, "sydonia", "Recettes douanières"),
    "tresorerie": (Domaine.TRESOR, "scie", "Trésorerie"),
    "dette-publique": (Domaine.DETTE, "dette", "Dette publique"),
    "patrimoine": (Domaine.PATRIMOINE, "sicom", "Patrimoine de l'État"),
    "portefeuille": (Domaine.PORTEFEUILLE, "sysop", "Portefeuille de l'État"),
    "masse-salariale": (Domaine.PAIE, "fugas", "Masse salariale"),
    "marches-publics": (Domaine.MARCHES_PUBLICS, "telemo", "Marchés publics"),
}
MODULES = {
    "tofe": "apps.core.tofe",
    "recettes-fiscales": "apps.recettes_fiscales.services",
    "recettes-douanieres": "apps.douanes.services",
    "tresorerie": "apps.tresor.services",
    "dette-publique": "apps.dette.services",
    "patrimoine": "apps.patrimoine.services",
    "portefeuille": "apps.portefeuille.services",
    "marches-publics": "apps.marches_publics.services",
}

# Champs exprimés en GNF (convertis en milliards) et champs exprimés en ratio (format %).
MONTANTS = {
    "credit_reserve",
    "montant_bloque",
    "disponible_reconstitue",
    "ecart_disponibilite",
    "avance_demarrage",
    "montant_regie",
    "detail_brut",
    "detail_comparable",
    "ecart_absolu",
    "lfi",
    "lfr",
    "objectif_cumule",
    "realise_n1",
    "recettes_dons",
    "depenses",
    "solde_global",
    "solde_primaire",
    "solde_caisse",
    "besoin_financement",
    "financement",
    "ecart_financement",
    "credit_initial_lfi",
    "credit_lfr",
    "brut",
    "comparable",
    "ecart_perimetre",
    "ecart_reference",
    "credit_actuel",
    "credit_disponible",
    "credit_engage",
    "montant_liquide",
    "montant_ordonnance",
    "montant_vbp",
    "montant_paye",
    "credits_non_engages",
    "ordonnance",
    "paye",
    "reste_a_payer",
    "ordonnance_hors_chaine",
    "paye_hors_chaine",
    "montant_engage",
    "total_engage",
    "realise",
    "objectif",
    "recouvre",
    "restes_a_recouvrer",
    "contentieux",
    "montant",
    "exonerations",
    "encaissements",
    "decaissements",
    "solde",
    "encours",
    "exterieure",
    "interieure",
    "pib",
    "principal",
    "interets",
    "valeur_nette",
    "valeur_brute",
    "subventions_prevues",
    "subventions_payees",
    "dividendes_votes",
    "dividendes_encaisses",
    "prevu",
    "vote",
    "encaisse",
    "masse_brute",
    "masse_nette",
    "masse_mensuelle_moyenne",
    "credits_projets_sans_engagement",
    "reste_a_payer_risque_arriere",
    "montant_ttc",
    "montant_ht",
    "montant_taxes",
    "montant_reserve",
    "montant_paiement",
    "ecart",
    "montant_avenants",
    "engage_periode_complementaire",
    "reference",
    "valeur",
    "interets_engages",
}
TAUX = {
    "part_immobilisee",
    "couverture",
    "ratio_solde_pib",
    "pression_fiscale",
    "taux_recettes",
    "taux_depenses",
    "taux",
    "taux_engagement",
    "taux_ordonnancement",
    "taux_paiement",
    "taux_vbp",
    "taux_liquidation",
    "taux_liquidation_sur_credits",
    "taux_ordonnancement_sur_credits",
    "taux_paiement_sur_credits",
    "variation_lfi",
    "paye_sur_ordonnance",
    "part",
    "ratio",
    "seuil",
    "part_budget",
    "taux_teledeclaration",
    "part_exonerations",
    "taux_amortissement",
    "taux_immatriculation",
    "taux_en_service",
    "taux_dividendes",
    "taux_transmission",
    "seuil_retard",
    "part_entente_directe",
    "seuil_entente_directe",
    "part_avenants",
}
LIBELLES = {
    "credit_reserve": "Crédits réservés",
    "montant_bloque": "Crédits bloqués",
    "disponible_reconstitue": "Solde calculé après engagement, réservation et blocage",
    "ecart_disponibilite": "Disponible source moins solde calculé",
    "part_immobilisee": "Part réservée ou bloquée",
    "mediane_jours": "Délai médian (jours calendaires)",
    "p90_jours": "90e percentile (jours calendaires)",
    "paires_valides": "Paires de dates valides",
    "couverture": "Couverture des dates",
    "sans_date_fin": "Sans date de visa",
    "delais_negatifs": "Délais négatifs exclus",
    "dates_futures": "Dates futures exclues",
    "detail_brut": "Détail brut reçu",
    "detail_comparable": "Détail comparable",
    "cles_en_ecart": "Clés d'imputation en écart",
    "ecart_absolu": "Somme des écarts absolus par imputation",
    "avance_demarrage": "Avances APAD enregistrées",
    "montant_regie": "Régies enregistrées",
    "numero_apad": "Numéro APAD",
    "numero_marche": "Numéro de marché",
    "libelle_projet": "Projet ou service",
    "date_creation": "Date de création",
    "gestionnaire": "Gestionnaire",
    "lfi": "LFI simulée",
    "lfr": "LFR simulée",
    "objectif_cumule": "Prévision cumulée simulée",
    "realise_n1": "Réalisé N−1 simulé à période équivalente",
    "libelle": "Libellé",
    "libelle_court": "Libellé court",
    "code": "Code",
    "mois": "Mois",
    "credit_actuel": "Crédits actuels",
    "credit_initial_lfi": "Crédits LFI",
    "credit_engage": "Engagé",
    "montant_ordonnance": "Ordonnancé",
    "montant_paye": "Payé",
    "credit_disponible": "Disponible",
    "reste_a_payer": "Solde ordonnancé non payé (à rapprocher)",
    "taux_engagement": "Taux d'engagement",
    "taux_transmission": "Taux selon les critères de validation des états",
    "etats_non_transmis": "Organismes sans validation établie",
    "brut": "Engagements bruts",
    "comparable": "Engagements comparables",
    "ecart_perimetre": "Écart de périmètre",
    "ecart_reference": "Écart résiduel avec la situation budgétaire",
    "paye_sur_ordonnance": "Payé / ordonnancé",
    "recouvre": "Recouvré",
    "objectif": "Objectif",
    "taux": "Taux",
    "montant": "Montant",
    "nombre": "Nombre",
    "statut": "Statut",
    "procedure": "Procédure",
    "hors_chaine": "Hors chaîne",
    "beneficiaire": "Bénéficiaire",
    "part": "Part",
    "nb_engagements": "Engagements",
    "montant_engage": "Engagé",
    "projet": "Projet",
    "ministere": "Ministère",
    "section_code": "Section",
    "sous_section_code": "Sous-section",
    "sans_engagement": "Sans engagement",
    "encaissements": "Encaissements",
    "decaissements": "Décaissements",
    "solde": "Solde",
    "annee": "Année",
    "principal": "Principal",
    "interets": "Intérêts",
    "encours": "Encours",
    "prevu": "Prévu",
    "paye": "Payé",
    "vote": "Attendu renseigné",
    "dividendes_votes": "Dividendes attendus renseignés",
    "transferts": "Contexte budgétaire global du titre 4",
    "reste_a_payer_risque_arriere": "Solde associé aux engagements anciens (non certifié comme arriérés)",
    "encaisse": "Encaissé",
    "valeur_nette": "Valeur nette",
    "valeur_brute": "Valeur brute",
    "nombre_biens": "Nombre de biens",
    "nombre_agents": "Agents",
    "masse_brute": "Masse brute",
    "masse_nette": "Masse nette",
    "effectif": "Effectif",
    "titre": "Titre",
    "severite": "Sévérité",
    "domaine": "Domaine",
    "message": "Message",
    "action_recommandee": "Action recommandée",
    "valeur": "Valeur",
    "indicateur": "Indicateur",
    "realise": "Réalisé",
    "application": "Application",
    "structure": "Structure",
    "variation_lfi": "Variation par rapport à la LFI",
    "taux_liquidation": "Liquidé / engagé",
    "taux_ordonnancement": "Ordonnancé / liquidé",
    "taux_vbp": "VBP / ordonnancé",
    "taux_paiement": "Payé / ordonnancé",
    "taux_liquidation_sur_credits": "Liquidé / crédits actuels",
    "taux_ordonnancement_sur_credits": "Ordonnancé / crédits actuels",
    "taux_paiement_sur_credits": "Payé / crédits actuels",
    "credits_non_engages": "Crédits non engagés",
    "montant_liquide": "Liquidé",
    "montant_vbp": "Vu bon pour paiement",
    "nb_lignes": "Lignes budgétaires",
    "nb_lfi_absent": "Lignes sans LFI",
    "ordonnance_hors_chaine": "Ordonnancé hors chaîne",
    "paye_hors_chaine": "Payé hors chaîne",
    "restes_a_recouvrer": "Restes à recouvrer",
    "contribuables_actifs": "Contribuables actifs",
    "taux_teledeclaration": "Taux de télédéclaration",
    "delai_moyen_jours": "Délai moyen (jours)",
    "jours_de_decaissements": "Jours de décaissements",
    "sous_seuil": "Sous le seuil",
    "depasse": "Seuil dépassé",
    "nb_projets": "Projets",
    "nb_projets_sans_engagement": "Projets de plus de 1 Md sans engagement",
    "credits_projets_sans_engagement": "Crédits des projets sans engagement",
    "part_budget": "Part du budget",
    "anciennete_mois": "Ancienneté (mois)",
    "risque_arriere": "Engagement ancien — échéance non évaluée",
    "mois_creation": "Mois de création",
    "periode_complementaire": "Période complémentaire",
    "decembre": "Décembre",
    "seuil": "Seuil",
}
NATURES = {
    "personnel": "Personnel",
    "biens_services": "Biens et services",
    "transferts": "Transferts",
    "investissement": "Investissement",
    "dette": "Dette",
}

MARINE = "16314E"
ENTETE = PatternFill("solid", fgColor=MARINE)


def _lib(cle: str) -> str:
    base = cle.split(".")[-1]
    suffixe = " (Mds GNF)" if base in MONTANTS else ""
    return LIBELLES.get(base, base.replace("_", " ").capitalize()) + suffixe


def _valeur(cle: str, v: Any) -> Any:
    base = cle.split(".")[-1]
    if isinstance(v, bool):
        return "Oui" if v else "Non"
    if isinstance(v, (Decimal, float, int)) and base in MONTANTS:
        return round(float(v) / 1e9, 3)
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, (date, datetime)):
        return v.isoformat()[:10] if isinstance(v, date) and not isinstance(v, datetime) else v.isoformat()
    if isinstance(v, (dict, list)):
        return str(v)
    return v


def _aplatir(d: dict, prefixe: str = "") -> dict:
    out = {}
    for k, v in d.items():
        if k == "meta":
            continue
        cle = f"{prefixe}{k}"
        if isinstance(v, dict):
            out.update(_aplatir(v, f"{cle}."))
        else:
            out[cle] = v
    return out


class Classeur:
    def __init__(self, titre: str, meta_principale: dict, utilisateur: str, filtres: str = ""):
        self.wb = Workbook()
        self.lisez_moi = self.wb.active
        self.lisez_moi.title = "Lisez-moi"
        self.titre = titre
        self.meta = meta_principale
        self.sources: list[tuple[str, dict]] = []
        self.utilisateur = utilisateur
        self.filtres = filtres

    def feuille(self, nom: str, donnees: Any, meta_bloc: dict | None = None) -> None:
        """Ajoute une feuille : liste de dicts → tableau ; dict → paires indicateur / valeur."""
        if donnees in (None, [], {}):
            return
        ws = self.wb.create_sheet(nom[:31])
        self.sources.append((nom, meta_bloc or self.meta))
        if isinstance(donnees, dict):
            lignes = [{"indicateur": k, "valeur": v} for k, v in _aplatir(donnees).items()]
            ws.append(["Indicateur", "Valeur"])
            for ligne in lignes:
                ws.append([_lib(ligne["indicateur"]), _valeur(ligne["indicateur"], ligne["valeur"])])
                self._format(ws.cell(ws.max_row, 2), ligne["indicateur"])
        else:
            lignes = [_aplatir(x) if isinstance(x, dict) else {"valeur": x} for x in donnees]
            colonnes = list(dict.fromkeys(k for ligne in lignes for k in ligne))
            ws.append([_lib(c) for c in colonnes])
            for ligne in lignes:
                ws.append([_valeur(c, ligne.get(c)) for c in colonnes])
                for i, c in enumerate(colonnes, start=1):
                    self._format(ws.cell(ws.max_row, i), c)
        for cellule in ws[1]:
            cellule.font = Font(bold=True, color="FFFFFF")
            cellule.fill = ENTETE
            cellule.alignment = Alignment(wrap_text=True, vertical="center")
        ws.freeze_panes = "A2"
        for i, colonne in enumerate(ws.columns, start=1):
            largeur = max(len(str(c.value or "")) for c in colonne)
            ws.column_dimensions[get_column_letter(i)].width = min(60, max(10, largeur + 2))

    @staticmethod
    def _format(cellule, cle: str) -> None:
        base = cle.split(".")[-1]
        if base in TAUX and isinstance(cellule.value, (int, float)):
            cellule.number_format = "0%"
        elif base in MONTANTS and isinstance(cellule.value, (int, float)):
            cellule.number_format = "#,##0.0"

    def octets(self) -> bytes:
        ws = self.lisez_moi
        m = self.meta
        lignes = [
            ["République de Guinée · Ministère de l'Économie, des Finances et du Budget"],
            [f"Tableau de bord des finances publiques — {self.titre}"],
            ["Document de travail – diffusion restreinte"],
            [],
            ["Exercice", m.get("exercice")],
            ["Date de situation", m.get("date_situation")],
            ["Exporté le", timezone.localtime().strftime("%d/%m/%Y %H:%M")],
            ["Exporté par", self.utilisateur],
            ["Filtres appliqués", self.filtres or "Aucun (toutes natures, tous ministères)"],
            ["Unités", "Montants en milliards de GNF (Mds) ; taux en pourcentage."],
            [],
            ["Feuille", "Source", "Statut", "Date de situation"],
        ]
        statuts = {"reel": "réel", "demo": "illustration (chiffres fictifs)", "non_raccorde": "non raccordée"}
        for nom, mb in self.sources:
            lignes.append(
                [
                    nom[:31],
                    mb.get("application") or mb.get("source"),
                    statuts.get(mb.get("statut_source"), mb.get("statut_source")),
                    mb.get("date_situation"),
                ]
            )
        for ligne in lignes:
            ws.append(ligne)
        ws["A1"].font = Font(bold=True, color=MARINE)
        ws["A2"].font = Font(bold=True, size=14, color=MARINE)
        ws["A3"].font = Font(bold=True)
        for c in ws[12]:
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = ENTETE
        ws.column_dimensions["A"].width = 34
        ws.column_dimensions["B"].width = 46
        ws.column_dimensions["C"].width = 30
        ws.column_dimensions["D"].width = 18
        tampon = BytesIO()
        self.wb.save(tampon)
        return tampon.getvalue()


def _contenu(page: str, request, c: Classeur) -> None:
    params = request.query_params
    if page == "synthese":
        from .synthese import SyntheseView

        vue = SyntheseView()
        vue.request = request
        d = vue._get.__wrapped__(vue, request).get("data") or {}
        indicateurs = []
        for x in d.get("indicateurs", []):
            ligne = {k: v for k, v in x.items() if k != "meta"}
            if x["code"] == "dette" and "reference" in ligne:  # la référence de la dette est un ratio (seuil CEDEAO)
                ligne["seuil"] = ligne.pop("reference")
            indicateurs.append(
                ligne
                | {
                    "source": x["meta"]["application"],
                    "statut": x["meta"]["statut_source"],
                    "date_situation": x["meta"]["date_situation"],
                    "exercice": x["meta"].get("exercice"),
                }
            )
        c.feuille(
            "Mode de lecture",
            {
                "mode": d.get("mode_synthese"),
                "precaution": (
                    "Les montants absents ne sont pas des zéros confirmés. "
                    "Aucun solde budgétaire n'est déduit des graphiques."
                ),
            },
        )
        c.feuille("Indicateurs", indicateurs)
        execution = d.get("execution")
        if execution:
            i, n1 = execution["indicateurs"], execution.get("comparaison_n1") or {}
            c.feuille(
                "Exécution",
                {
                    "credits_actuels": i["credit_actuel"],
                    "engage": i["credit_engage"],
                    "liquide": i["montant_liquide"],
                    "ordonnance": i["montant_ordonnance"],
                    "paye": i["montant_paye"],
                    "reste_a_payer": i["paiement"]["reste_a_payer"],
                    "taux_engagement": i["taux_engagement"],
                    "taux_liquidation": i["taux_liquidation"],
                    "taux_ordonnancement": i["taux_ordonnancement"],
                    "taux_vbp": i["taux_vbp"],
                    "taux_paiement": i["taux_paiement"],
                    "taux_engagement_n1_meme_date": n1.get("taux_engagement"),
                    "date_n1": n1.get("date"),
                    "methode_n1": n1.get("methode") or n1.get("motif"),
                },
            )
        if d.get("plan_engagement"):
            c.feuille("Plan d'engagement", d["plan_engagement"])
        c.feuille("Rapprochement mensuel", d.get("rapprochement_mensuel"))
        c.feuille(
            "Alertes",
            [
                {k: a[k] for k in ("severite", "domaine", "titre", "message", "valeur", "action_recommandee", "statut")}
                for a in d.get("alertes", [])
            ],
        )
        c.feuille("Alertes par gravité", d.get("alertes_compte") or {})
        c.feuille("Cohortes et encaissements", d.get("serie_mensuelle"))
        return
    if page in ("depenses", "investissements"):
        from apps.depense import services as dep

        f = resoudre_filtres(params, "chaine_depense")
        if f.date_situation is None:
            return
        if page == "depenses":
            from apps.depense.pilotage import page as pilotage_depense

            c.feuille("Indicateurs", dep.indicateurs(f))
            pilotage = pilotage_depense(f)
            c.feuille("Délais de visa", pilotage["delais"])
            c.feuille("Rapprochement des phases", pilotage["rapprochements"])
            c.feuille(
                "APAD enregistrées", {k: v for k, v in pilotage["apad"].items() if k not in {"ministeres", "dossiers"}}
            )
            c.feuille("APAD par ministère", pilotage["apad"]["ministeres"])
            c.feuille("Régies enregistrées", pilotage["regies"])
            c.feuille("Natures", [{k: v for k, v in n.items() if k != "empile"} for n in dep.natures(f)])
            c.feuille(
                "Ministères",
                [
                    {**{k: v for k, v in s.items() if k != "statut"}, "statut": s["statut"]["libelle"]}
                    for s in dep.sections(f)
                ],
            )
            mensuel = dep.mensuel(f)
            c.feuille("Cohortes mensuelles", mensuel["mois"])
            c.feuille("Rapprochement mensuel", mensuel["rapprochement"])
            c.feuille(
                "Méthode des soldes",
                {
                    "precision": (
                        "Ordonnancé non payé à rapprocher avec le Trésor. "
                        "L'âge est mesuré depuis la création de l'engagement ; "
                        "il ne certifie ni l'exigibilité ni des arriérés."
                    )
                },
            )
            c.feuille("Restes à payer", dep.restes_a_payer_anciennete(f)["mois"])
        else:
            s = dep.synthese_investissement(f)
            c.feuille("Indicateurs", {k: v for k, v in s.items() if not isinstance(v, list)})
            c.feuille("Projets", sorted(dep.projets_investissement(f), key=lambda p: -p["credit_actuel"]))
            c.feuille("Ministères", s["top_ministeres"])
        return
    if page == "masse-salariale":
        from apps.paie.services import page as paie

        f = resoudre_filtres(params, "fugas")
        fc = filtres_source("chaine_depense")
        if f.date_situation is None:
            f = None
        if f is None and fc is None:
            return
        d = paie(f, exercice=f.exercice if f else fc.exercice)
        c.feuille("Crédits de personnel", d["credits"]["donnees"], d["credits"]["meta"])
        c.feuille("Par ministère", d["par_ministere"]["donnees"], d["par_ministere"]["meta"])
        if d["fugas"]["donnees"]:
            c.feuille("Paie mensuelle", d["fugas"]["donnees"]["mensuel"], d["fugas"]["meta"])
            c.feuille("Contrôles de paie", d["fugas"]["donnees"]["controles"], d["fugas"]["meta"])
        return
    source = PAGES[page][1]
    f = resoudre_filtres(params, source)
    if f.date_situation is None:
        return
    d = import_module(MODULES[page]).page(f)
    if page == "tofe":
        c.feuille("Tableau TOFE", d["lignes"])
        c.feuille("Indicateurs", d["indicateurs"])
        c.feuille("Série mensuelle", d["mensuel"])
        c.feuille("Contrôles", d["verifications"])
        c.feuille("Méthode", {"description": d["methode"], "perimetre": d["perimetre"]})
        c.feuille("Références", d["references"])
        return
    for cle, v in d.items():
        if isinstance(v, dict) and "meta" in v and "donnees" in v:  # bloc à source propre
            c.feuille(
                cle.replace("_", " ").capitalize(),
                v["donnees"] if isinstance(v["donnees"], (list, dict)) else {cle: v["donnees"]},
                v["meta"],
            )
        elif cle == "controles" and isinstance(v, dict):
            resume = [
                {"controle": k.replace("_", " ").capitalize(), "nombre": x.get("nombre"), "montant": x.get("montant")}
                for k, x in v.items()
                if isinstance(x, dict)
            ]
            c.feuille("Contrôles", resume)
        elif cle == "tofe":
            c.feuille(
                "TOFE",
                [
                    {
                        "poste": x["poste"],
                        "sens": x["sens"],
                        "montant": x["donnees"],
                        "source": x["meta"]["application"],
                        "statut": x["meta"]["statut_source"],
                    }
                    for x in v
                ],
            )
        elif isinstance(v, (list, dict)):
            c.feuille(cle.replace("_", " ").capitalize(), v)


class ExportView(APIView):
    permission_classes = [DoubleAuthentification]

    @extend_schema(parameters=PARAMETRES_COMMUNS, responses={200: OpenApiTypes.BINARY})
    def get(self, request, page: str):
        if page not in PAGES:
            raise NotFound("Page inconnue.")
        domaine, source, titre = PAGES[page]
        u = request.user
        if not (u.voit_tout() or u.peut_exporter(domaine)) or (domaine == Domaine.SYNTHESE and u.role == "lecteur"):
            raise PermissionDenied("Votre profil ne permet pas l'export de cette page.")
        f = resoudre_filtres(request.query_params, source)
        p = request.query_params
        filtres = " · ".join(
            filter(
                None,
                [
                    f"Nature : {NATURES.get(p['nature'], p['nature'])}" if p.get("nature") else "",
                    f"Section : {p['section']}" if p.get("section") else "",
                    "Paiements bruts (procédures hors chaîne incluses)" if p.get("paiement") == "brut" else "",
                ],
            )
        )
        c = Classeur(titre, meta(source, f), u.get_username(), filtres)
        _contenu(page, request, c)
        journaliser(
            request, JournalAudit.Action.EXPORT, objet=f"{page}.xlsx", detail={"filtres": dict(request.query_params)}
        )
        reponse = HttpResponse(
            c.octets(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        date_nom = meta(source, f).get("date_situation") or timezone.localdate().isoformat()
        reponse["Content-Disposition"] = f'attachment; filename="tdb-{page}-{date_nom}.xlsx"'
        return reponse
