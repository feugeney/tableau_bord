"""Plan d'engagement de la Chaîne Dépense (GDEP.TD_PLAN_ENG*), lecture seule.

Le plan d'engagement fixe, chaque trimestre, le plafond d'engagement de chaque
section et de chaque titre (décret D/2013/015/PRG/SGG, art. 19 ; arrêté du ministre
du Budget). Sens des montants, d'après les procédures Oracle :

- PLAN_ENG_OUV_PERIODE copie LBUDG à l'ouverture : MONTANT_CREDIT = crédit,
  MONTANT_ENGAGEMENT = engagé visé CF cumulé à cette date ;
- PLAN_ENG_GENERATION calcule MONTANT_REPARTISSABLE, le plafond du trimestre
  (enveloppe mobilisable − imprévus − dépenses obligatoires, réparti au prorata du disponible) ;
- le déclencheur BEF_REGUL_LBUDG refuse toute régulation qui dépasse ce plafond.

Un chargement par exercice ; la date de situation est la date d'extraction.
"""

from __future__ import annotations

from datetime import date, datetime
from datetime import time as dtime
from decimal import Decimal
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

import pandas as pd
from django.conf import settings

from apps.depense.models import FaitPlanEngagement, FaitPlanEngagementAjustement, PlanEngagementPeriode
from etl import nettoyage as n

from .base import BaseConnector, ErreurChargement, RapportValidation

PERIODES = "periodes"
PLAFONDS = "plafonds"
AJUSTEMENTS = "ajustements"
SQL = Path(__file__).resolve().parent.parent / "sql" / "chaine_depense"
REQUETES = {
    PERIODES: "plan_engagement_periodes.sql",
    PLAFONDS: "plan_engagement_plafonds.sql",
    AJUSTEMENTS: "plan_engagement_ajustements.sql",
}
ORDRE_PERIODES = {"T1": 1, "T2": 2, "T3": 3, "T4": 4}
TAILLE_LOT = 2000


def exercices_disponibles() -> list[int]:
    """Exercices pour lesquels un plan d'engagement a été ouvert dans la Chaîne Dépense."""
    from .oracle import connexion_lecture_seule

    with connexion_lecture_seule() as cnx, cnx.cursor() as cur:
        cur.execute("SELECT DISTINCT NO_EX FROM GDEP.TD_PLAN_ENG_PARAMETRE ORDER BY NO_EX")
        return [int(r[0]) for r in cur.fetchall()]


def _drapeau(v) -> bool:
    return n.code(v) == "1"


class PlanEngagementConnector(BaseConnector):
    """Extraction Oracle (ou jeu de données fourni, pour les essais) d'un exercice."""

    source_code = "plan_engagement"
    HEURES_OUVREES = (dtime(7, 30), dtime(18, 30))

    def __init__(
        self,
        exercice: int,
        donnees: Optional[dict[str, pd.DataFrame]] = None,
        replique: bool = False,
        exception_ponctuelle: bool = False,
        maintenant: Optional[datetime] = None,
        **kwargs,
    ):
        super().__init__(exercice=exercice, **kwargs)
        self._fournies = donnees
        self.replique = replique
        self.exception_ponctuelle = exception_ponctuelle
        self.maintenant = maintenant
        self.informations_chargement = {"exception_horaire_ponctuelle": exception_ponctuelle}

    @property
    def nom_fichier(self) -> str:
        return "oracle://chaine_depense/plan_engagement" if self._fournies is None else "plan_engagement"

    def verifier_creneau(self) -> None:
        """Même règle que la Chaîne Dépense : pas de lecture de la production aux heures ouvrées."""
        if not settings.ORACLE_RESTRICTION_HEURES_OUVREES or self.replique or self.exception_ponctuelle:
            return
        maintenant = self.maintenant or datetime.now(ZoneInfo(settings.TIME_ZONE))
        debut, fin = self.HEURES_OUVREES
        if maintenant.weekday() < 5 and debut <= maintenant.time() <= fin:
            raise ErreurChargement(
                "Interrogation de la base de production interdite aux heures ouvrées "
                "(réplique, exception ponctuelle ou exécution de nuit)."
            )

    def extract(self) -> dict[str, pd.DataFrame]:
        if self.date_situation is None:
            self.date_situation = date.today()
        if self._fournies is not None:
            return {k: v.astype(object) for k, v in self._fournies.items()}
        from .oracle import connexion_lecture_seule

        self.verifier_creneau()
        if not settings.SOURCES_EXTERNES["chaine_depense_oracle"]["dsn"]:
            raise ErreurChargement("Connexion Oracle non configurée (CHAINE_DEPENSE_ORACLE_DSN).")
        donnees = {}
        with connexion_lecture_seule() as cnx:
            for cle, fichier in REQUETES.items():
                with cnx.cursor() as cur:
                    cur.arraysize = 1000
                    cur.execute((SQL / fichier).read_text(encoding="utf-8"), exercice=self.exercice)
                    donnees[cle] = pd.DataFrame(cur.fetchall(), columns=[c[0] for c in cur.description], dtype=object)
        return donnees

    def _exercices_ouverts(self) -> list[int]:
        """Exercices ayant un plan dans Oracle, pour orienter l'utilisateur ; vide si la source est un jeu fourni."""
        if self._fournies is not None:
            return []
        try:
            return exercices_disponibles()
        except Exception:  # message indicatif seulement : l'échec principal reste celui de l'exercice demandé
            return []

    def validate(self) -> RapportValidation:
        rapport = RapportValidation()
        periodes = self.donnees.get(PERIODES)
        plafonds = self.donnees.get(PLAFONDS)
        if periodes is None or periodes.empty:
            message = f"aucun plan d'engagement ouvert pour {self.exercice}"
            disponibles = self._exercices_ouverts()
            if disponibles:
                message += f" ; exercices disponibles dans la Chaîne Dépense : {', '.join(map(str, disponibles))}"
            rapport.ajouter(
                "periodes",
                "Trimestres du plan d'engagement présents",
                "bloquant",
                False,
                detail={"message": message, "exercices_disponibles": disponibles},
            )
            return rapport
        inconnues = sorted({n.code(p) for p in periodes["periode"]} - set(ORDRE_PERIODES))
        rapport.ajouter(
            "periodes_trimestrielles",
            "Périodes trimestrielles (T1 à T4)",
            "avertissement",
            not inconnues,
            nombre=len(inconnues),
            detail={"message": ", ".join(inconnues) or "ok"},
        )
        doublons = int(periodes["periode"].map(n.code).duplicated().sum())
        rapport.ajouter("periode_unique", "Un en-tête par trimestre", "bloquant", doublons == 0, nombre=doublons)
        plafonds = plafonds if plafonds is not None else pd.DataFrame(columns=["periode", "section", "titre"])
        cles = plafonds[["periode", "section", "titre"]].map(n.code)
        doublons_cle = int(cles.duplicated().sum())
        rapport.ajouter(
            "plafond_unique",
            "Un plafond par trimestre, section et titre",
            "bloquant",
            doublons_cle == 0,
            nombre=doublons_cle,
        )
        sans_section = int((cles["section"] == "").sum())
        rapport.ajouter(
            "plafond_sans_section",
            "Plafonds sans code section (rejetés)",
            "avertissement",
            sans_section == 0,
            nombre=sans_section,
        )
        # Contrôle de cohérence : la somme des plafonds répartis doit retrouver l'enveloppe mobilisable.
        ecarts = []
        for p in periodes.to_dict("records"):
            mobilisable = n.montant(p.get("montant_mobilisable"))
            if mobilisable[1] or not mobilisable[0]:
                continue
            code = n.code(p.get("periode"))
            total = sum((n.montant_ou_zero(v) for v in plafonds.loc[cles["periode"] == code, "plafond"]), Decimal(0))
            if total and abs(total - mobilisable[0]) > max(Decimal(1), mobilisable[0] * Decimal("0.001")):
                ecarts.append({"periode": code, "mobilisable": str(mobilisable[0]), "plafonds": str(total)})
        rapport.ajouter(
            "plafonds_enveloppe",
            "Somme des plafonds égale à l'enveloppe mobilisable",
            "avertissement",
            not ecarts,
            nombre=len(ecarts),
            detail={"ecarts": ecarts, "message": "écart possible si le plan a été modifié après génération"},
        )
        return rapport

    def _tech(self, chargement) -> dict:
        return {
            "exercice": self.exercice,
            "date_situation": self.date_situation,
            "source_id": chargement.source_id,
            "chargement_id": chargement.id,
        }

    def load(self, chargement) -> int:
        tech = self._tech(chargement)
        periodes = [
            PlanEngagementPeriode(
                **tech,
                periode=n.code(p.get("periode")),
                etat_code=n.code(p.get("etat_code")),
                etat_libelle=n.libelle(p.get("etat_libelle")),
                montant_mobilisable=(
                    None
                    if n.est_vide(p.get("montant_mobilisable"))
                    else n.montant_ou_zero(p.get("montant_mobilisable"))
                ),
                montant_imprevu=(
                    None if n.est_vide(p.get("montant_imprevu")) else n.montant_ou_zero(p.get("montant_imprevu"))
                ),
                montant_obligatoire_titre2=(
                    None
                    if n.est_vide(p.get("montant_obligatoire_titre2"))
                    else n.montant_ou_zero(p.get("montant_obligatoire_titre2"))
                ),
                montant_repartissable=(
                    None
                    if n.est_vide(p.get("montant_repartissable"))
                    else n.montant_ou_zero(p.get("montant_repartissable"))
                ),
                # « 0 » saisi faute de référence n'est pas une référence d'arrêté.
                reference_arrete=(
                    "" if n.code(p.get("reference_arrete")) in ("", "0") else n.libelle(p.get("reference_arrete"))
                ),
                date_validation=n.date_(p.get("date_validation")),
                date_ouverture=n.date_(p.get("date_ouverture")),
                periode_courante=_drapeau(p.get("periode_courante")),
                periode_execution=_drapeau(p.get("periode_execution")),
            )
            for p in self.donnees[PERIODES].to_dict("records")
        ]
        PlanEngagementPeriode.objects.bulk_create(periodes)

        plafonds, rejetees = [], 0
        df = self.donnees.get(PLAFONDS, pd.DataFrame())
        for r in df.to_dict("records"):
            if not n.code(r.get("section")):
                rejetees += 1
                continue
            plafonds.append(
                FaitPlanEngagement(
                    **tech,
                    periode=n.code(r.get("periode")),
                    section_code=n.code(r.get("section")),
                    section_libelle=n.titre_francais(r.get("libelle_section"))[:255],
                    titre=n.code(r.get("titre")),
                    **{
                        m: n.montant_ou_zero(r.get(m))
                        for m in ("credit", "engage_ouverture", "plafond", "montant_propose", "montant_arbitrage")
                    },
                )
            )
        FaitPlanEngagement.objects.bulk_create(plafonds, batch_size=TAILLE_LOT)

        ajustements = [
            FaitPlanEngagementAjustement(
                **tech,
                periode=n.code(a.get("periode")),
                section_source=n.code(a.get("section_source")),
                titre_source=n.code(a.get("titre_source")),
                section_destination=n.code(a.get("section_destination")),
                titre_destination=n.code(a.get("titre_destination")),
                montant=n.montant_ou_zero(a.get("montant")),
                observation=n.libelle(a.get("observation")),
                date_ajustement=n.date_(a.get("date_ajustement")),
            )
            for a in self.donnees.get(AJUSTEMENTS, pd.DataFrame()).to_dict("records")
        ]
        FaitPlanEngagementAjustement.objects.bulk_create(ajustements)
        self.comptes = {
            PERIODES: {"lues": len(periodes), "chargees": len(periodes), "rejetees": 0},
            PLAFONDS: {"lues": len(df), "chargees": len(plafonds), "rejetees": rejetees},
            AJUSTEMENTS: {"lues": len(ajustements), "chargees": len(ajustements), "rejetees": 0},
        }
        return len(periodes) + len(plafonds) + len(ajustements)

    def apres_chargement(self, chargement) -> None:
        # Aucune vue matérialisée ne dépend du plan : seul le cache de l'API est invalidé.
        from etl.mart import invalider_cache_api

        invalider_cache_api()
