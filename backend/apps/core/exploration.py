"""Exploration libre de l'entrepôt (profil analyste).

L'utilisateur choisit un jeu de données (une table de faits), des axes de regroupement, des mesures et des
filtres. Aucune requête SQL libre : chaque nom de champ est vérifié contre le modèle, la requête est construite
par l'ORM, et seuls les jeux des domaines de l'utilisateur sont accessibles. Les résultats portent sur le
dernier chargement réussi de la source pour l'exercice et la date de situation demandés.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from django.apps import apps
from django.db import models
from django.db.models import Avg, Count, Max, Min, Sum
from django.db.models.functions import TruncMonth, TruncQuarter, TruncYear
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.referentiels.models import DimTemps

from .domaines import chargements_actifs
from .entrepot import FaitBase
from .filtres import Filtres, dernieres_situations
from .models import Domaine, Role, Source

# Application Django → (domaine, source).
JEUX_PAR_APPLICATION = {
    "depense": (Domaine.DEPENSE, "chaine_depense"),
    "recettes_fiscales": (Domaine.RECETTES_FISCALES, "safig"),
    "douanes": (Domaine.DOUANES, "sydonia"),
    "tresor": (Domaine.TRESOR, "scie"),
    "dette": (Domaine.DETTE, "dette"),
    "investissement": (Domaine.INVESTISSEMENT, "sigpip"),
    "paie": (Domaine.PAIE, "fugas"),
    "patrimoine": (Domaine.PATRIMOINE, "sicom"),
    "portefeuille": (Domaine.PORTEFEUILLE, "sysop"),
    "marches_publics": (Domaine.MARCHES_PUBLICS, "telemo"),
}
LIBELLES_JEUX = {
    "fait_situation_ligne": "Situation des crédits par ligne budgétaire",
    "fait_engagement": "Engagements",
    "fait_operation": "Détail des opérations",
    "fait_regie": "Régies",
    "fait_recouvrement_fiscal": "Recouvrement fiscal",
    "fait_reste_a_recouvrer": "Restes à recouvrer",
    "fait_contentieux": "Contentieux fiscal",
    "fait_contribuables": "Contribuables actifs et télédéclarants",
    "fait_recette_douane": "Recettes douanières",
    "fait_declaration": "Déclarations en douane",
    "fait_exoneration": "Exonérations douanières",
    "fait_flux_tresorerie": "Flux de trésorerie",
    "fait_depots_correspondants": "Dépôts des correspondants",
    "fait_delai_paiement": "Délais de paiement",
    "fait_tofe": "Tableau des opérations financières de l'État",
    "fait_encours_dette": "Encours de la dette",
    "fait_echeancier_dette": "Échéancier de la dette",
    "fait_indicateur_macro": "Indicateurs macroéconomiques",
    "fait_avancement_projet": "Avancement physique des projets",
    "fait_paie": "Paie mensuelle",
    "fait_controle_paie": "Contrôles de paie",
    "fait_patrimoine": "Patrimoine par catégorie",
    "fait_parc_vehicules": "Parc de véhicules",
    "fait_controle_patrimoine": "Contrôles du patrimoine",
    "fait_deploiement_sicom": "Déploiement de SICOM",
    "fait_subvention_epa": "Subventions aux EPA",
    "fait_dividende": "Dividendes",
    "fait_sante_financiere": "Santé financière des organismes",
    "fait_gouvernance": "Gouvernance des organismes",
    "fait_budget_epa": "Budgets des EPA",
    "fait_reservation_credit": "Réservations de crédit (F3)",
    "fait_marche": "Marchés immatriculés (F4)",
    "fait_paiement_marche": "Paiements des marchés (F5)",
}
CHAMPS_TECHNIQUES = {"id", "exercice", "date_situation", "source", "chargement"}
# Entiers qui sont des axes et non des quantités.
ENTIERS_AXES = {"mois", "annee", "ordre"}
AGREGATS = {"somme": Sum, "moyenne": Avg, "minimum": Min, "maximum": Max}
PERIODES = {"mois": TruncMonth, "trimestre": TruncQuarter, "annee": TruncYear}
OPERATEURS = {
    "egal": "exact",
    "different": "exact",
    "contient": "icontains",
    "superieur": "gte",
    "inferieur": "lte",
    "parmi": "in",
}
MAX_AXES, MAX_MESURES, MAX_FILTRES = 5, 8, 8
LIMITE_DEFAUT, LIMITE_MAX, LIMITE_EXPORT = 500, 5000, 50000


def peut_explorer(u) -> bool:
    return bool(u and u.is_authenticated and (u.is_superuser or u.role in (Role.ANALYSTE, Role.DNSI_ADMIN)))


# Libellés des champs dont le nom technique ne suffit pas.
LIBELLES_CHAMPS = {
    "section": "Ministère ou institution",
    "sous_section": "Sous-section",
    "nature": "Nature économique",
    "titre": "Titre",
    "type_budget": "Type de budget",
    "source_financement": "Source de financement",
    "groupe_bailleur": "Groupe de bailleurs",
    "regulation": "Régulation",
    "cle_ligne": "Clé de la ligne budgétaire",
    "cle_imputation": "Clé d'imputation",
    "credit_initial_lfi": "Crédit initial (LFI)",
    "credit_lfr": "Crédit (LFR)",
    "credit_douzieme_provisoire": "Crédit (douzième provisoire)",
    "credit_engage_cf": "Crédit engagé visé par le contrôle financier",
    "credit_engage_projet": "Crédit engagé (projets)",
    "montant_vbp": "Montant visé bon à payer",
    "montant_ecp": "Montant en cours de paiement",
    "montant_encours_paiement": "Montant en cours de paiement",
    "montant_engage_cf": "Montant engagé visé par le contrôle financier",
    "montant_ht": "Montant HT",
    "montant_ttc": "Montant TTC",
    "montant_taxes": "TVA et autres taxes",
    "montant_avenants": "Montant des avenants",
    "montant_reserve": "Montant réservé",
    "montant_paiement": "Montant du paiement",
    "montant_paye": "Montant payé",
    "montant_engage": "Montant engagé",
    "montant_liquide": "Montant liquidé",
    "montant_ordonnance": "Montant ordonnancé",
    "montant_bloque": "Montant bloqué",
    "montant_delegation": "Montant délégué",
    "montant_regie": "Montant en régie",
    "avance_demarrage": "Avance de démarrage",
    "avance_demarrage_taux": "Taux de l'avance de démarrage",
    "retenue_garantie_taux": "Taux de la retenue de garantie",
    "avancement_physique": "Avancement physique",
    "taux_physique": "Taux d'avancement physique",
    "type_procedure": "Type de procédure",
    "etat_dossier": "État du dossier",
    "beneficiaire": "Bénéficiaire",
    "beneficiaire_brut": "Bénéficiaire (libellé de l'extraction)",
    "beneficiaire_type": "Type de bénéficiaire",
    "date_creation": "Date de création",
    "date_visa_cf": "Date du visa du contrôle financier",
    "date_visa_ministre": "Date du visa du ministre",
    "date_visa_vbp": "Date du visa bon à payer",
    "date_visa": "Date du visa",
    "date_validation": "Date de validation",
    "date_etat": "Date de l'état",
    "date_maj": "Date de mise à jour",
    "date_immatriculation": "Date d'immatriculation",
    "date_lancement": "Date de lancement",
    "date_signature": "Date de signature",
    "date_approbation": "Date d'approbation",
    "date_paiement": "Date de paiement",
    "date_enregistrement": "Date d'enregistrement",
    "date_mainlevee": "Date de mainlevée",
    "numero_immatriculation": "Numéro d'immatriculation du marché",
    "numero_reservation": "Numéro de la réservation de crédit",
    "numero_engagement": "Numéro d'engagement",
    "numero_regie": "Numéro de régie",
    "reference_paiement": "Référence du paiement",
    "ligne_budgetaire": "Ligne budgétaire",
    "type_marche": "Type de marché",
    "mode_passation": "Mode de passation",
    "autorite_contractante": "Autorité contractante",
    "titulaire_nif": "NIF du titulaire",
    "titulaire": "Titulaire",
    "delai_execution_jours": "Délai d'exécution (jours)",
    "delai_moyen_jours": "Délai moyen (jours)",
    "modalites_paiement": "Modalités de paiement",
    "impot": "Impôt",
    "centre": "Centre des impôts",
    "secteur": "Secteur d'activité",
    "recouvre": "Recouvré",
    "anciennete": "Ancienneté",
    "nombre_dossiers": "Nombre de dossiers",
    "teledeclarants": "Télédéclarants",
    "nature_droit": "Nature du droit de douane",
    "bureau": "Bureau de douane",
    "regime": "Régime",
    "categorie": "Catégorie",
    "poste_code": "Code du poste",
    "poste_libelle": "Poste",
    "type_creancier": "Type de créancier",
    "exterieure": "Dette extérieure",
    "encours": "Encours",
    "interets": "Intérêts",
    "annee": "Année",
    "projet": "Projet",
    "masse_brute": "Masse salariale brute",
    "masse_nette": "Masse salariale nette",
    "controle": "Contrôle",
    "nombre_agents": "Nombre d'agents",
    "valeur_brute": "Valeur brute",
    "valeur_nette": "Valeur nette",
    "nombre_biens": "Nombre de biens",
    "biens_immatricules": "Biens immatriculés",
    "etat": "État",
    "type_vehicule": "Type de véhicule",
    "institutions_actives": "Institutions utilisant SICOM",
    "institutions_prevues": "Institutions prévues",
    "organisme": "Organisme",
    "prevu": "Prévu",
    "paye": "Payé",
    "transfert_chaine_depense": "Transfert (Chaîne Dépense)",
    "vote": "Voté",
    "encaisse": "Encaissé",
    "resultat": "Résultat",
    "etats_financiers_transmis": "États financiers transmis",
    "mandats_expires": "Mandats expirés",
    "budget_primitif": "Budget primitif",
    "saisi": "Budget saisi",
    "nombre_mandats": "Nombre de mandats",
    "encaissements": "Encaissements",
    "decaissements": "Décaissements",
    "recours": "Recours",
}


def _libelle(f: models.Field) -> str:
    if f.name in LIBELLES_CHAMPS:
        return LIBELLES_CHAMPS[f.name]
    texte = str(f.verbose_name)
    return texte[0].upper() + texte[1:]


@dataclass
class Jeu:
    code: str
    modele: type[models.Model]
    domaine: str
    source: str
    champs: dict[str, models.Field] = field(default_factory=dict)

    @property
    def libelle(self) -> str:
        return LIBELLES_JEUX.get(self.code, self.code)

    def axes(self) -> list[dict]:
        axes = []
        for nom, f in self.champs.items():
            if isinstance(f, models.DateField):
                axes.append({"code": nom, "libelle": _libelle(f), "type": "date"})
                axes += [
                    {"code": f"{nom}:{p}", "libelle": f"{_libelle(f)} ({lib})", "type": "periode"}
                    for p, lib in (("mois", "par mois"), ("trimestre", "par trimestre"), ("annee", "par année"))
                ]
            elif isinstance(f, models.BooleanField):
                axes.append({"code": nom, "libelle": _libelle(f), "type": "booleen"})
            elif isinstance(f, models.ForeignKey):
                axes.append({"code": nom, "libelle": _libelle(f), "type": "reference"})
            elif isinstance(f, (models.CharField, models.TextField)):
                axes.append({"code": nom, "libelle": _libelle(f), "type": "liste" if f.choices else "texte"})
            elif isinstance(f, models.IntegerField) and nom in ENTIERS_AXES:
                axes.append({"code": nom, "libelle": _libelle(f), "type": "nombre"})
        return axes

    def mesures(self) -> list[dict]:
        mesures = []
        for nom, f in self.champs.items():
            if isinstance(f, models.DecimalField) or (isinstance(f, models.IntegerField) and nom not in ENTIERS_AXES):
                # Un taux ou un délai se moyenne ; un montant ou un nombre se somme.
                moyenne = any(x in nom for x in ("taux", "delai", "avancement", "valeur")) and "valeur_" not in nom
                mesures.append(
                    {"code": nom, "libelle": _libelle(f), "agregat_defaut": "moyenne" if moyenne else "somme"}
                )
        return mesures


def jeux() -> dict[str, Jeu]:
    resultat = {}
    for m in apps.get_models():
        if not issubclass(m, FaitBase) or m._meta.app_label not in JEUX_PAR_APPLICATION:
            continue
        domaine, source = JEUX_PAR_APPLICATION[m._meta.app_label]
        code = m._meta.db_table.split('"."')[-1]
        champs = {
            f.name: f
            for f in m._meta.concrete_fields
            if f.name not in CHAMPS_TECHNIQUES and not isinstance(f, models.JSONField)
        }
        resultat[code] = Jeu(code, m, domaine, source, champs)
    return resultat


def jeux_visibles(u) -> list[Jeu]:
    return sorted((j for j in jeux().values() if u.peut_voir(j.domaine)), key=lambda j: (j.domaine, j.libelle))


def catalogue(u) -> list[dict]:
    """Jeux accessibles à l'utilisateur, avec leurs axes, leurs mesures et les situations chargées."""
    sources = {s.code: s for s in Source.objects.all()}
    libelles_domaines = dict(Domaine.choices)
    resultat = []
    for j in jeux_visibles(u):
        s = sources.get(j.source)
        resultat.append(
            {
                "code": j.code,
                "libelle": j.libelle,
                "domaine": j.domaine,
                "domaine_libelle": libelles_domaines.get(j.domaine, j.domaine),
                "source": j.source,
                "statut_source": s.statut if s else "non_raccorde",
                "axes": j.axes(),
                "mesures": j.mesures(),
                "situations": [
                    {"exercice": e, "date_situation": d.isoformat()} for e, d in dernieres_situations(j.source)
                ],
            }
        )
    return resultat


# ------------------------------------------------------------------ requête


def lire_requete(brut) -> dict:
    if isinstance(brut, str):
        try:
            brut = json.loads(brut)
        except ValueError as exc:
            raise ValidationError({"q": f"JSON invalide : {exc}"}) from exc
    if not isinstance(brut, dict):
        raise ValidationError({"q": "Objet attendu : { jeu, axes, mesures, filtres }."})
    return brut


def _convertir(f: models.Field, valeur: Any):
    """Valeur de filtre convertie selon le type du champ ; erreur lisible sinon."""
    try:
        if isinstance(f, models.DateField):
            return date.fromisoformat(str(valeur))
        if isinstance(f, models.BooleanField):
            return str(valeur).strip().lower() in {"1", "true", "vrai", "oui"}
        if isinstance(f, models.DecimalField):
            return Decimal(str(valeur).replace(" ", "").replace(",", "."))
        if isinstance(f, models.IntegerField):
            return int(str(valeur).strip())
    except (ValueError, InvalidOperation) as exc:
        raise ValidationError({"filtres": f"Valeur invalide pour « {f.name} » : {valeur!r}"}) from exc
    return str(valeur)


def _champ_filtre(f: models.Field) -> str:
    # Clé étrangère : le filtre porte sur le code stocké (colonne <champ>_code ou identifiant).
    return f.attname if isinstance(f, models.ForeignKey) else f.name


def _filtrer(qs, jeu: Jeu, filtres: list) -> Any:
    if len(filtres) > MAX_FILTRES:
        raise ValidationError({"filtres": f"{MAX_FILTRES} filtres au plus."})
    for x in filtres:
        if not isinstance(x, dict) or x.get("champ") not in jeu.champs or x.get("operateur") not in OPERATEURS:
            raise ValidationError({"filtres": f"Filtre invalide : {x!r}"})
        f, op, valeur = jeu.champs[x["champ"]], x["operateur"], x.get("valeur")
        if valeur in (None, ""):
            continue
        if op == "contient" and not isinstance(f, (models.CharField, models.TextField)):
            raise ValidationError({"filtres": f"« contient » ne s'applique qu'à un texte ({f.name})."})
        if op == "parmi":
            valeurs = valeur if isinstance(valeur, list) else [v.strip() for v in str(valeur).split(";") if v.strip()]
            condition = {f"{_champ_filtre(f)}__in": [_convertir(f, v) for v in valeurs]}
        else:
            condition = {f"{_champ_filtre(f)}__{OPERATEURS[op]}": _convertir(f, valeur)}
        qs = qs.exclude(**condition) if op == "different" else qs.filter(**condition)
    return qs


def _situation(jeu: Jeu, q: dict) -> Filtres:
    situations = dernieres_situations(jeu.source)
    try:
        exercice = int(q["exercice"]) if q.get("exercice") else (situations[0][0] if situations else None)
        jour = date.fromisoformat(q["date_situation"]) if q.get("date_situation") else None
    except (ValueError, TypeError) as exc:
        raise ValidationError({"detail": f"Exercice ou date de situation invalide : {exc}"}) from exc
    if jour is None:
        jour = next((d for e, d in situations if e == exercice), None)
    return Filtres(exercice, jour)


def _libelles_references(f: models.ForeignKey, valeurs: set) -> dict:
    """Clé stockée → « code — libellé » du référentiel."""
    cle = f.target_field.name
    resultat = {}
    for o in f.related_model.objects.filter(**{f"{cle}__in": [v for v in valeurs if v is not None]}):
        libelle = getattr(o, "libelle_affiche", None) or getattr(o, "libelle", None) or getattr(o, "nom", None)
        code = getattr(o, "code", None)
        resultat[getattr(o, cle)] = " — ".join(str(x) for x in (code, libelle) if x) or str(o)
    return resultat


def executer(u, q: dict, limite_max: int = LIMITE_MAX) -> dict:
    """Exécute une requête d'exploration ; renvoie colonnes, lignes, totaux et situation retenue."""
    jeu = jeux().get(str(q.get("jeu", "")))
    if jeu is None:
        raise ValidationError({"jeu": "Jeu de données inconnu."})
    if not u.peut_voir(jeu.domaine):
        raise PermissionDenied("Ce jeu de données ne fait pas partie de votre périmètre.")

    axes = list(q.get("axes") or [])
    mesures = list(q.get("mesures") or [])
    if len(axes) > MAX_AXES or len(mesures) > MAX_MESURES or len(set(axes)) != len(axes):
        raise ValidationError({"detail": f"{MAX_AXES} axes distincts et {MAX_MESURES} mesures au plus."})
    axes_connus = {a["code"]: a for a in jeu.axes()}
    mesures_connues = {m["code"]: m for m in jeu.mesures()}
    if any(a not in axes_connus for a in axes):
        raise ValidationError({"axes": "Axe inconnu pour ce jeu de données."})

    f = _situation(jeu, q)
    qs = jeu.modele.objects.filter(chargement_id__in=chargements_actifs(jeu.source, f) if f.date_situation else [])
    qs = _filtrer(qs, jeu, list(q.get("filtres") or []))

    # Axes : champ direct, clé de référentiel, ou date ramenée au mois, au trimestre ou à l'année.
    colonnes, annotations, cles = [], {}, []
    for a in axes:
        nom, _, periode = a.partition(":")
        champ = jeu.champs[nom]
        if periode:
            alias = f"{nom}_{periode}"
            annotations[alias] = PERIODES[periode](nom)
        else:
            alias = champ.attname if isinstance(champ, models.ForeignKey) else nom
        cles.append(alias)
        colonnes.append({"code": a, "libelle": axes_connus[a]["libelle"], "type": axes_connus[a]["type"], "cle": alias})

    agregats = {"nombre_lignes": Count("id")}
    colonnes_mesures = []
    for m in mesures:
        if not isinstance(m, dict) or m.get("champ") not in mesures_connues:
            raise ValidationError({"mesures": f"Mesure invalide : {m!r}"})
        agregat = m.get("agregat") or mesures_connues[m["champ"]]["agregat_defaut"]
        if agregat not in AGREGATS:
            raise ValidationError({"mesures": f"Agrégat inconnu : {agregat}"})
        alias = f"{m['champ']}__{agregat}"
        if alias in agregats:
            continue
        agregats[alias] = AGREGATS[agregat](m["champ"])
        colonnes_mesures.append(
            {
                "code": alias,
                "libelle": f"{mesures_connues[m['champ']]['libelle']} ({agregat})",
                "type": "mesure",
                "agregat": agregat,
            }
        )
    colonnes_mesures.append(
        {"code": "nombre_lignes", "libelle": "Nombre de lignes", "type": "mesure", "agregat": "nombre"}
    )

    try:
        limite = min(int(q.get("limite") or LIMITE_DEFAUT), limite_max)
    except (ValueError, TypeError) as exc:
        raise ValidationError({"limite": "Nombre attendu."}) from exc
    tri = q.get("tri") or {}
    ordre_connu = {c["cle"] for c in colonnes} | set(agregats)
    # Par défaut : première mesure demandée, décroissante.
    premiere_mesure = next((a for a in agregats if a != "nombre_lignes"), None)
    champ_tri = tri.get("champ") if tri.get("champ") in ordre_connu else premiere_mesure
    if champ_tri is None:
        champ_tri = cles[0] if cles else "nombre_lignes"
        descendant = not cles
    else:
        descendant = tri.get("sens", "desc") != "asc"

    totaux = qs.aggregate(**agregats)
    if cles:
        groupes = qs.annotate(**annotations).values(*cles).annotate(**agregats)
        groupes = groupes.order_by(
            models.F(champ_tri).desc(nulls_last=True) if descendant else models.F(champ_tri).asc()
        )
        nb_groupes = groupes.count()
        lignes = list(groupes[:limite])
    else:
        nb_groupes, lignes = 1, [dict(totaux)]

    # Libellés : référentiels, listes fermées, périodes (dimension temps).
    for c in colonnes:
        nom, _, periode = c["code"].partition(":")
        champ, cle = jeu.champs[nom], c["cle"]
        valeurs = {x[cle] for x in lignes}
        if isinstance(champ, models.ForeignKey):
            table = _libelles_references(champ, valeurs)
        elif periode:
            jours = {v for v in valeurs if v is not None}
            attribut = {"mois": "libelle_mois", "trimestre": "libelle_trimestre", "annee": "annee"}[periode]
            table = {d: str(lib) for d, lib in DimTemps.objects.filter(date__in=jours).values_list("date", attribut)}
        elif champ.choices:
            table = dict(champ.choices)
        elif isinstance(champ, models.BooleanField):
            table = {True: "Oui", False: "Non"}
        else:
            table = {}
        for x in lignes:
            v = x.pop(cle)
            x[c["code"]] = v
            x[f"{c['code']}__libelle"] = table.get(v, "(non renseigné)" if v in (None, "") else str(v))
        del c["cle"]

    return {
        "jeu": {"code": jeu.code, "libelle": jeu.libelle, "domaine": jeu.domaine, "source": jeu.source},
        "situation": f,
        "colonnes": colonnes + colonnes_mesures,
        "lignes": lignes,
        "totaux": totaux,
        "nb_groupes": nb_groupes,
        "tronque": nb_groupes > len(lignes),
    }
