"""Moteur d'alertes : évalue les règles actives (core_regle_alerte) et écrit dans core_alerte.

Chaque règle désigne une classe évaluatrice (chemin Python). Un évaluateur renvoie
zéro, une ou plusieurs constatations ; chaque constatation fournit les variables du
message modèle. Une règle défaillante est journalisée sans bloquer les autres.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

from django.utils.module_loading import import_string

from . import regles
from .models import Alerte, Chargement, Domaine, RegleAlerte, Severite, Source

logger = logging.getLogger(__name__)


@dataclass
class Constat:
    variables: dict = field(default_factory=dict)
    valeur: str = ""
    lien: Optional[str] = None
    # Alerte par dossier : clé stable d'une évaluation à l'autre et détail structuré.
    cle: str = ""
    donnees: dict = field(default_factory=dict)


def mds(montant) -> str:
    """Montant GNF → « 1 234,5 Mds » (espace fine insécable)."""
    v = regles.en_milliards(montant, 1) or Decimal(0)
    entier, _, dec = f"{v:,.1f}".partition(".")
    entier = entier.replace(",", ESPACE_FINE)
    return f"{entier},{dec} Mds"


ESPACE_FINE = " "


def pct(t) -> str:
    return "—" if t is None else f"{round(Decimal(t) * 100):.0f} %"


class Evaluateur:
    source_code = ""

    def __init__(self, regle: RegleAlerte):
        self.regle = regle
        self.seuils = regle.seuils or {}

    def filtres(self):
        from .filtres import Filtres, dernieres_situations

        situations = dernieres_situations(self.source_code)
        if not situations:
            return None
        return Filtres(situations[0][0], situations[0][1])

    def evaluer(self) -> list[Constat]:
        raise NotImplementedError


# ------------------------------------------------------------------ Chaîne Dépense


class SousExecution(Evaluateur):
    source_code = "chaine_depense"

    def evaluer(self):
        from apps.depense.services import sections

        f = self.filtres()
        if not f:
            return []
        liste = [s for s in sections(f) if s["statut"]["code"] == "sous_execution"]
        if not liste:
            return []
        noms = ", ".join(f"{s['libelle_court']} ({pct(s['taux_engagement'])})" for s in liste[:5])
        return [
            Constat(
                {
                    "nombre": len(liste),
                    "ministeres": noms,
                    "montant": mds(sum(s["credit_actuel"] - s["credit_engage"] for s in liste)),
                },
                valeur=str(len(liste)),
            )
        ]


class PaiementsRetard(Evaluateur):
    source_code = "chaine_depense"

    def evaluer(self):
        from apps.depense.services import sections

        f = self.filtres()
        if not f:
            return []
        liste = [s for s in sections(f) if s["statut"]["code"] == "paiements_retard"]
        if not liste:
            return []
        noms = ", ".join(f"{s['libelle_court']} ({pct(s['paye_sur_ordonnance'])})" for s in liste[:5])
        return [
            Constat(
                {"nombre": len(liste), "ministeres": noms, "montant": mds(sum(s["reste_a_payer"] for s in liste))},
                valeur=str(len(liste)),
            )
        ]


class ProjectionEngagement(Evaluateur):
    """Au rythme constaté, l'engagement de fin d'exercice resterait loin des crédits."""

    source_code = "chaine_depense"

    def evaluer(self):
        from apps.depense.services import projection

        f = self.filtres()
        if not f:
            return []
        p = projection(f)
        e = p["engagement"]
        if not p["sous_le_seuil"]:
            return []
        return [
            Constat(
                {
                    "bas": pct(e["taux_bas"]),
                    "haut": pct(e["taux_haut"]),
                    "realise": pct(e["taux_realise"]),
                    "seuil": pct(p["seuil"]),
                    "non_engages": mds(e["cible"] - e["haut"]),
                    "nb_ministeres": p["nb_ministeres_sous_le_seuil"],
                },
                valeur=pct(e["taux_haut"]),
            )
        ]


class InvestissementFaible(Evaluateur):
    source_code = "chaine_depense"

    def evaluer(self):
        from apps.depense.services import synthese_investissement

        f = self.filtres()
        if not f:
            return []
        s = synthese_investissement(f)
        seuil = Decimal(str(self.seuils.get("taux_engagement_max", 0.5)))
        t = s["taux_engagement"]
        if t is None or (t >= seuil and not s["nb_projets_sans_engagement"]):
            return []
        return [
            Constat(
                {
                    "taux": pct(t),
                    "credits": mds(s["credit_actuel"]),
                    "nb_projets": s["nb_projets_sans_engagement"],
                    "nb_total": s["nb_projets"],
                    "montant": mds(s["credits_projets_sans_engagement"]),
                },
                valeur=pct(t),
            )
        ]


class LignesDepassement(Evaluateur):
    source_code = "chaine_depense"

    def evaluer(self):
        from apps.depense.services import lignes_en_depassement

        f = self.filtres()
        if not f:
            return []
        nb = lignes_en_depassement(f)
        return [Constat({"nombre": nb}, valeur=str(nb))] if nb else []


class HorsChaine(Evaluateur):
    source_code = "chaine_depense"

    def evaluer(self):
        from apps.depense.services import indicateurs

        f = self.filtres()
        if not f:
            return []
        hc = indicateurs(f)["hors_chaine"]
        if not hc["ordonnance"]:
            return []
        return [Constat({"ordonnance": mds(hc["ordonnance"]), "paye": mds(hc["paye"])}, valeur=mds(hc["ordonnance"]))]


class RestesAPayerAnciens(Evaluateur):
    source_code = "chaine_depense"

    def evaluer(self):
        from apps.depense.services import restes_a_payer_anciennete

        f = self.filtres()
        if not f:
            return []
        r = restes_a_payer_anciennete(f)
        if not r["reste_a_payer_risque_arriere"]:
            return []
        return [
            Constat(
                {"montant": mds(r["reste_a_payer_risque_arriere"]), "mois": r["seuil_mois"]},
                valeur=mds(r["reste_a_payer_risque_arriere"]),
            )
        ]


class DossiersArbitrage(Evaluateur):
    """Dossiers bloqués au-delà du délai et au-delà d'un seuil de montant : arbitrage de la Ministre.

    Une alerte par dossier. Seuils (modifiables dans Administration → Règles d'alerte) :
    montant_min (GNF), delai_jours, max_dossiers, etats_exclus (motifs de libellé d'état),
    destinataires et destinataires_relance (identifiants ou adresses), relance_heures.
    """

    source_code = "chaine_depense"

    def evaluer(self):
        from apps.depense.titres import ETATS_CLOS, dossiers_en_attente_visa

        f = self.filtres()
        if not f:
            return []
        dossiers = dossiers_en_attente_visa(
            f,
            int(self.seuils.get("delai_jours", 15)),
            Decimal(str(self.seuils.get("montant_min", 10 * 10**9))),
            tuple(self.seuils.get("etats_exclus", ETATS_CLOS)),
        )
        constats = []
        for d in dossiers[: int(self.seuils.get("max_dossiers", 50))]:
            variables = {
                "titre": d["libelle_titre"],
                "ministere": d["ministere"],
                "montant": mds(d["montant"]),
                "jours": d["jours"],
                "numero": d["numero"],
                "beneficiaire": d["beneficiaire"] or "bénéficiaire non renseigné",
                "etape": d["etape"].lower(),
                "acteur": d["acteur"],
                "etat": d["etat"] or "état non renseigné",
            }
            donnees = {
                k: d[k]
                for k in (
                    "numero",
                    "section",
                    "ministere",
                    "titre",
                    "libelle_titre",
                    "beneficiaire",
                    "objet",
                    "jours",
                    "etat",
                    "etape",
                    "acteur",
                    "procedure",
                    "service",
                    "sous_section",
                    "imputation",
                )
            }
            donnees |= {
                "montant": str(d["montant"]),
                "depuis": d["depuis"].isoformat(),
                **{k: d[k].isoformat() if d[k] else None for k in ("date_creation", "date_etat")},
            }
            constats.append(
                Constat(
                    variables,
                    valeur=mds(d["montant"]),
                    lien=f"/depenses?vue_titre={d['titre']}",
                    cle=d["cle"],
                    donnees=donnees,
                )
            )
        return constats


# ------------------------------------------------------- autres domaines (réels ou illustration)


class TresorerieSousSeuil(Evaluateur):
    source_code = "scie"

    def evaluer(self):
        from apps.tresor.services import _solde

        f = self.filtres()
        if not f:
            return []
        s = _solde(f)
        if not s["sous_seuil"]:
            return []
        jours = s["jours_de_decaissements"]
        return [Constat({"jours": f"{jours:.0f}" if jours is not None else "—"}, valeur=mds(s["solde"]))]


class ImpotsSousObjectif(Evaluateur):
    source_code = "safig"

    def evaluer(self):
        from apps.recettes_fiscales.services import page

        f = self.filtres()
        if not f:
            return []
        retard = [i for i in page(f)["par_impot"] if i["en_retard"]]
        if not retard:
            return []
        liste = ", ".join(f"{i['libelle']} ({pct(i['taux'])})" for i in retard[:5])
        return [Constat({"nombre": len(retard), "impots": liste}, valeur=str(len(retard)))]


class Exonerations(Evaluateur):
    source_code = "sydonia"

    def evaluer(self):
        from apps.douanes.services import exonerations

        f = self.filtres()
        if not f:
            return []
        e = exonerations(f)
        seuil = Decimal(str(self.seuils.get("part_min", 0.1)))
        if not e["montant"] or (e["part"] or 0) < seuil:
            return []
        return [Constat({"montant": mds(e["montant"]), "part": pct(e["part"])}, valeur=mds(e["montant"]))]


class DoublonsPaie(Evaluateur):
    source_code = "fugas"

    def evaluer(self):
        from apps.core.domaines import chargements_actifs
        from apps.paie.models import FaitControlePaie

        f = self.filtres()
        if not f:
            return []
        d = FaitControlePaie.objects.filter(
            chargement_id__in=chargements_actifs("fugas", f), controle="doublons"
        ).first()
        if not d or not d.nombre_agents:
            return []
        return [Constat({"nombre": d.nombre_agents, "montant": mds(d.montant)}, valeur=str(d.nombre_agents))]


class BiensNonInventories(Evaluateur):
    source_code = "sicom"

    def evaluer(self):
        from apps.patrimoine.services import biens_non_inventories

        f = self.filtres()
        if not f:
            return []
        c = biens_non_inventories(f)
        if not c or not c.nombre:
            return []
        return [
            Constat(
                {"nombre": f"{c.nombre:,}".replace(",", ESPACE_FINE), "montant": mds(c.montant)},
                valeur=f"{c.nombre:,}".replace(",", ESPACE_FINE),
            )
        ]


class DividendesNonVerses(Evaluateur):
    source_code = "sysop"

    def evaluer(self):
        from apps.portefeuille.services import dividendes_non_verses

        f = self.filtres()
        if not f:
            return []
        d = dividendes_non_verses(f)
        if not d["nombre"]:
            return []
        return [Constat({"nombre": d["nombre"], "montant": mds(d["montant"])}, valeur=mds(d["montant"]))]


class OrganismesDeficitaires(Evaluateur):
    source_code = "sysop"

    def evaluer(self):
        from apps.portefeuille.services import sante

        f = self.filtres()
        if not f:
            return []
        s = sante(f)
        if not (s["deficitaires"] or s["non_transmis"]):
            return []
        return [Constat(s, valeur=str(s["deficitaires"] + s["non_transmis"]))]


class EntenteDirecte(Evaluateur):
    source_code = "telemo"

    def evaluer(self):
        from apps.marches_publics.services import entente_directe

        f = self.filtres()
        if not f:
            return []
        e = entente_directe(f)
        if not e["excessive"]:
            return []
        variables = {
            "part": pct(e["part"]),
            "montant": mds(e["montant"]),
            "nombre": e["nombre"],
            "seuil": pct(regles.parametre("entente_directe_part_max")),
        }
        return [Constat(variables, valeur=pct(e["part"]))]


class CoherenceMarches(Evaluateur):
    """Rapprochement des flux Telemo : réservations (F3), marchés (F4), paiements (F5)."""

    source_code = "telemo"

    def evaluer(self):
        from apps.marches_publics.services import controles

        f = self.filtres()
        if not f:
            return []
        c = controles(f)
        sans = c["marches_sans_reservation"]["nombre"]
        sur = c["paiements_superieurs"]["nombre"]
        orph = c["paiements_sans_marche"]["nombre"]
        if not (sans or sur or orph):
            return []
        variables = {
            "sans_reservation": sans,
            "sur_payes": sur,
            "montant": mds(c["paiements_superieurs"]["montant"]),
            "orphelins": orph,
        }
        return [Constat(variables, valeur=str(sans + sur + orph))]


# --------------------------------------------------------------------- définitions

REGLES = [
    # code, domaine, sévérité, classe, seuils, titre, message, action, lien
    (
        "depense_sous_execution",
        Domaine.DEPENSE,
        Severite.CRITIQUE,
        "SousExecution",
        {},
        "{nombre} ministère(s) en sous-exécution",
        "Crédits ≥ 20 Mds engagés à moins de 50 % : {ministeres}. Crédits non engagés : {montant}.",
        "Inviter les DAF concernés, à travers la DGB, à arrêter un plan d'engagement.",
        "/depenses",
    ),
    (
        "depense_projection_faible",
        Domaine.DEPENSE,
        Severite.VIGILANCE,
        "ProjectionEngagement",
        {},
        "Engagement projeté entre {bas} et {haut} des crédits au 31 décembre",
        "Engagé à ce jour : {realise}. Au rythme constaté, au moins {non_engages} de crédits resteraient non "
        "engagés en fin d'exercice (seuil : {seuil}) ; {nb_ministeres} ministère(s) sont sous le seuil.",
        "Examiner avec la DGB les ministères les plus éloignés et les crédits à redéployer.",
        "/depenses#projection",
    ),
    (
        "investissement_faible",
        Domaine.INVESTISSEMENT,
        Severite.CRITIQUE,
        "InvestissementFaible",
        {"taux_engagement_max": 0.5},
        "Investissement engagé à {taux}",
        "Sur {credits} de crédits d'investissement, {nb_projets} projets de plus de 1 Md (sur {nb_total} "
        "projets) n'ont aucun engagement, pour {montant}.",
        "Demander aux ministères porteurs un calendrier de passation des marchés.",
        "/investissements",
    ),
    (
        "depense_paiements_retard",
        Domaine.DEPENSE,
        Severite.SERIEUX,
        "PaiementsRetard",
        {},
        "Paiements en retard dans {nombre} ministère(s)",
        "Payé / ordonnancé ajusté < 35 % : {ministeres}. Reste à payer : {montant}.",
        "Examiner le plan de trésorerie avec le Trésor.",
        "/depenses",
    ),
    (
        "depense_lignes_depassement",
        Domaine.DEPENSE,
        Severite.SERIEUX,
        "LignesDepassement",
        {},
        "{nombre} lignes budgétaires en dépassement",
        "{nombre} lignes ont des crédits disponibles négatifs.",
        "Faire régulariser par virement de crédits ou LFR.",
        "/depenses",
    ),
    (
        "depense_hors_chaine",
        Domaine.DEPENSE,
        Severite.VIGILANCE,
        "HorsChaine",
        {},
        "Dette et salaires payés hors chaîne",
        "{ordonnance} ordonnancés par procédure Solde ou débit d'office (dont {paye} constatés payés dans la "
        "chaîne). Ils sont exclus du paiement ajusté.",
        "Rapprocher avec le Trésor (SCIE) les paiements hors chaîne.",
        "/depenses",
    ),
    (
        "depense_restes_anciens",
        Domaine.DEPENSE,
        Severite.SERIEUX,
        "RestesAPayerAnciens",
        {},
        "Restes à payer de plus de {mois} mois",
        "{montant} ordonnancés depuis plus de {mois} mois restent à payer : risque d'arriérés.",
        "Apurer les restes à payer les plus anciens en priorité.",
        "/depenses",
    ),
    (
        "depense_arbitrage_ministre",
        Domaine.DEPENSE,
        Severite.CRITIQUE,
        "DossiersArbitrage",
        {
            "montant_min": 10 * 10**9,
            "delai_jours": 15,
            "max_dossiers": 50,
            "etats_exclus": ["abandon", "rejet"],
            "destinataires": [],
            "destinataires_relance": [],
            "relance_heures": 48,
        },
        "Arbitrage : {titre} · {ministere} · {montant}",
        "Dossier n° {numero} ({beneficiaire}) en attente du {etape} depuis {jours} jours ({etat}). Acteur : {acteur}.",
        "Arbitrer ou demander au {acteur} de statuer sur le dossier.",
        "/depenses",
    ),
    # Autres domaines : évaluateurs activés au raccordement ou avec les données de démonstration.
    (
        "tresorerie_sous_seuil",
        Domaine.TRESOR,
        Severite.CRITIQUE,
        "TresorerieSousSeuil",
        {},
        "Trésorerie sous le seuil",
        "Le solde couvre {jours} jours de décaissements (seuil : 1 mois).",
        "Prioriser les décaissements et mobiliser les recettes.",
        "/tresorerie",
    ),
    (
        "impots_sous_objectif",
        Domaine.RECETTES_FISCALES,
        Severite.SERIEUX,
        "ImpotsSousObjectif",
        {},
        "{nombre} impôt(s) sous 80 % de l'objectif",
        "{impots}.",
        "Renforcer le recouvrement avec la DGI.",
        "/recettes-fiscales",
    ),
    (
        "douanes_exonerations",
        Domaine.DOUANES,
        Severite.VIGILANCE,
        "Exonerations",
        {},
        "Exonérations douanières : {montant}",
        "Les exonérations représentent {part} des recettes douanières.",
        "Examiner les régimes d'exonération avec la DGD.",
        "/recettes-douanieres",
    ),
    (
        "paie_doublons",
        Domaine.PAIE,
        Severite.SERIEUX,
        "DoublonsPaie",
        {},
        "{nombre} doublons de paie",
        "{nombre} agents en doublon pour {montant} par mois.",
        "Suspendre les paiements en doublon et faire contrôler par la Fonction publique.",
        "/masse-salariale",
    ),
    (
        "patrimoine_non_inventories",
        Domaine.PATRIMOINE,
        Severite.VIGILANCE,
        "BiensNonInventories",
        {},
        "{nombre} biens non inventoriés depuis plus de 2 ans",
        "Valeur concernée : {montant}.",
        "Programmer un inventaire avec la DNCM.",
        "/patrimoine",
    ),
    (
        "portefeuille_dividendes",
        Domaine.PORTEFEUILLE,
        Severite.SERIEUX,
        "DividendesNonVerses",
        {},
        "Dividendes non versés : {montant}",
        "{nombre} sociétés n'ont pas versé les dividendes votés.",
        "Relancer les sociétés via la DGPEIP.",
        "/portefeuille",
    ),
    (
        "marches_entente_directe",
        Domaine.MARCHES_PUBLICS,
        Severite.SERIEUX,
        "EntenteDirecte",
        {},
        "Entente directe : {part} des marchés passés",
        "{nombre} marchés passés par entente directe (gré à gré) pour {montant}, au-delà du seuil de {seuil}.",
        "Demander à la direction des marchés publics la justification des ententes directes.",
        "/marches-publics",
    ),
    (
        "marches_coherence",
        Domaine.MARCHES_PUBLICS,
        Severite.SERIEUX,
        "CoherenceMarches",
        {},
        "Anomalies de rapprochement des marchés",
        "{sans_reservation} marchés sans réservation de crédit, {sur_payes} marchés payés au-delà de leur montant "
        "({montant} en trop), {orphelins} paiements sans marché immatriculé.",
        "Faire vérifier par le contrôle financier et la direction des marchés publics.",
        "/marches-publics",
    ),
    (
        "portefeuille_organismes",
        Domaine.PORTEFEUILLE,
        Severite.VIGILANCE,
        "OrganismesDeficitaires",
        {},
        "{deficitaires} organismes déficitaires, {non_transmis} sans états financiers",
        "Santé financière du portefeuille à surveiller.",
        "Exiger la transmission des états financiers.",
        "/portefeuille",
    ),
]


def initialiser_regles_alerte() -> None:
    for code, domaine, sev, classe, seuils, titre, message, action, lien in REGLES:
        RegleAlerte.objects.get_or_create(
            code=code,
            defaults=dict(
                domaine=domaine,
                severite=sev,
                classe=f"apps.core.alertes.{classe}",
                seuils=seuils,
                titre_modele=titre,
                message_modele=message,
                action_recommandee=action,
                lien=lien,
            ),
        )


class _Variables(dict):
    def __missing__(self, cle):
        return "{" + cle + "}"


def evaluer_alertes(chargement: Optional[Chargement] = None, domaine: Optional[str] = None) -> list[Alerte]:
    """Évalue les règles actives et remplace les alertes « nouvelles » du même domaine.

    Les alertes déjà vues ou traitées sont conservées (historique).
    """
    regles_actives = RegleAlerte.objects.filter(actif=True)
    if chargement is not None:
        regles_actives = regles_actives.filter(domaine__in=_domaines_source(chargement.source))
    elif domaine:
        regles_actives = regles_actives.filter(domaine=domaine)
    creees = []
    for regle in regles_actives:
        try:
            classe = import_string(regle.classe)
        except ImportError:
            logger.info("Évaluateur %s non disponible : règle %s ignorée", regle.classe, regle.code)
            continue
        try:
            evaluateur = classe(regle)
            constats = evaluateur.evaluer()
        except Exception:
            logger.exception("Règle d'alerte %s en échec", regle.code)
            continue
        source = Source.objects.filter(code=evaluateur.source_code).first()
        # Alertes par dossier : mises à jour sur place (statut et notification conservés) ; celles dont le
        # dossier n'est plus bloqué disparaissent si personne ne les a encore vues.
        par_cle = {a.cle: a for a in Alerte.objects.filter(regle=regle).exclude(cle="")}
        cles = {c.cle for c in constats if c.cle}
        Alerte.objects.filter(regle=regle, statut="nouvelle").exclude(cle__in=cles).delete()
        for c in constats:
            v = _Variables(c.variables)
            champs = dict(
                domaine=regle.domaine,
                source=source,
                severite=regle.severite,
                titre=regle.titre_modele.format_map(v)[:255],
                message=regle.message_modele.format_map(v),
                valeur=c.valeur[:64],
                action_recommandee=regle.action_recommandee.format_map(v),
                lien=c.lien or regle.lien,
                donnees=c.donnees,
            )
            if chargement is not None:
                champs |= {"chargement": chargement, "date_situation": chargement.date_situation}
            existante = par_cle.get(c.cle) if c.cle else None
            if existante is not None:
                for k, val in champs.items():
                    setattr(existante, k, val)
                existante.save()
                continue
            creees.append(Alerte.objects.create(regle=regle, cle=c.cle, **champs))
    try:
        from .notifications import notifier_nouvelles_alertes

        notifier_nouvelles_alertes()
    except Exception:  # un serveur de messagerie absent ne doit pas bloquer l'évaluation
        logger.exception("Notification des alertes en échec")
    return creees


def _domaines_source(source: Source) -> list[str]:
    if source.code == "chaine_depense":
        return [Domaine.DEPENSE, Domaine.INVESTISSEMENT, Domaine.PAIE, Domaine.DETTE, Domaine.PORTEFEUILLE]
    return [source.domaine]
