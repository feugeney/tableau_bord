"""Situation du portefeuille SYSOP : lecture seule, un chargement par exercice."""

from decimal import Decimal

import pandas as pd
import psycopg
from django.conf import settings
from django.utils import timezone

from apps.portefeuille.models import FaitDividende, FaitGouvernance, FaitSanteFinanciere, FaitSubventionEpa
from apps.referentiels.models import RefOrganisme

from .base import BaseConnector, ErreurChargement, RapportValidation

NIVEAUX_VALIDES = {"4", "6"}


def situation_organisme(validations, resultats):
    """Les validations reçues sont la dernière version de chaque type d'état."""
    transmis = bool(validations) and all(
        str(v["validation_id"]) in NIVEAUX_VALIDES and v["date_rejet"] is None for v in validations
    )
    if len(resultats) > 1:
        raise ErreurChargement("Plusieurs résultats nets XI pour un organisme/exercice : sélection métier nécessaire.")
    resultat = resultats[0]["mt_ligne_gnf"] if transmis and resultats else None
    if not transmis:
        statut = "non_transmis"
    elif resultat is None:
        statut = "indisponible"
    else:
        statut = "excedentaire" if resultat > 0 else "deficitaire" if resultat < 0 else "equilibre"
    return transmis, resultat, statut


class SysopPortefeuilleConnector(BaseConnector):
    source_code = "sysop"

    @property
    def nom_fichier(self):
        return "postgresql://sysop/portefeuille"

    def extract(self):
        if not self.exercice:
            raise ErreurChargement("Exercice SYSOP obligatoire.")
        self.date_situation = self.date_situation or timezone.localdate()
        url = settings.SOURCES_EXTERNES.get("sysop", {}).get("url")
        if not url:
            raise ErreurChargement("Connexion SYSOP non configurée (SYSOP_DATABASE_URL).")
        requetes = {
            "organismes": """SELECT no_op, sigle_op, lib_long_op, lib_court_op, type_op_id
                FROM public.organisme_publique WHERE type_op_id IN ('EPA', 'SP') ORDER BY no_op""",
            "subventions": """SELECT organisme_id, SUM(mt_sub_lfr) AS prevu, SUM(mt_sub_verse) AS paye
                FROM public.subvention_etat WHERE exercice_id = %s AND type_op_id = 'EPA'
                GROUP BY organisme_id""",
            "dividendes": """SELECT organisme_id, SUM(mt_div_prevu) AS vote, SUM(mt_div_realise) AS encaisse
                FROM public.dividende_sp WHERE exercice_id = %s AND type_op_id = 'SP'
                GROUP BY organisme_id""",
            "validations": """SELECT DISTINCT ON (organisme_id, type_etat)
                organisme_id, type_etat, validation_id, date_rejet
                FROM public.validation_etats WHERE exercice = %s
                ORDER BY organisme_id, type_etat, dt_validation DESC NULLS LAST, id DESC""",
            "resultats": """SELECT organisme_id, mt_ligne_gnf FROM public.ligne_cpte_resultat
                WHERE exercice = %s AND cadre_cpte_resultat_id = 'XI'""",
        }
        donnees = {}
        try:
            with psycopg.connect(
                url,
                connect_timeout=10,
                options="-c default_transaction_read_only=on -c statement_timeout=30000",
            ) as cnx:
                cnx.isolation_level = psycopg.IsolationLevel.REPEATABLE_READ
                with cnx.cursor() as cursor:
                    for table, requete in requetes.items():
                        cursor.execute(requete, None if table == "organismes" else (str(self.exercice),))
                        donnees[table] = pd.DataFrame(
                            cursor.fetchall(),
                            columns=[d.name for d in cursor.description],
                            dtype=object,
                        )
        except psycopg.Error:
            raise ErreurChargement(
                "Lecture SYSOP impossible. Vérifier la connexion et les droits SELECT sur les tables du portefeuille."
            ) from None
        self.informations_chargement = {
            "profil": "sysop_portefeuille",
            "base_subventions": "LFR",
            "niveaux_validation": sorted(NIVEAUX_VALIDES),
            "indicateurs_indisponibles": ["mandats_expires", "budget_primitif"],
        }
        return donnees

    def validate(self):
        rapport = RapportValidation()
        organismes = self.donnees["organismes"].to_dict("records")
        codes = {o["no_op"] for o in organismes}
        rapport.ajouter(
            "organismes",
            "Organismes SYSOP présents et uniques",
            "bloquant",
            bool(codes) and len(codes) == len(organismes),
        )
        noms_valides = all(
            len(str(o["no_op"])) <= 32 and bool(o["lib_long_op"] or o["lib_court_op"] or o["sigle_op"])
            for o in organismes
        )
        rapport.ajouter("identite", "Identifiants et noms des organismes renseignés", "bloquant", noms_valides)
        for table in ("subventions", "dividendes", "validations", "resultats"):
            lignes = self.donnees[table].to_dict("records")
            inconnus = {r["organisme_id"] for r in lignes} - codes
            rapport.ajouter(f"liens_{table}", f"Organismes connus pour {table}", "bloquant", not inconnus)
        resultats = self.donnees["resultats"]
        rapport.ajouter(
            "resultat_unique",
            "Un résultat net par organisme et exercice",
            "bloquant",
            not resultats["organisme_id"].duplicated().any(),
        )
        rapport.ajouter("resultats", "Résultats nets disponibles", "avertissement", not resultats.empty)
        return rapport

    def load(self, chargement):
        refs = {}
        for o in self.donnees["organismes"].to_dict("records"):
            obj, _ = RefOrganisme.objects.update_or_create(
                identifiant_etat=o["no_op"],
                defaults={
                    "nom": o["lib_long_op"] or o["lib_court_op"] or o["sigle_op"],
                    "sigle": o["sigle_op"] or "",
                    "type": "epa" if o["type_op_id"] == "EPA" else "societe",
                    "fictif": False,
                },
            )
            refs[o["no_op"]] = obj
        commun = dict(
            exercice=self.exercice,
            date_situation=self.date_situation,
            source_id=chargement.source_id,
            chargement=chargement,
        )
        total = 0
        for table, modele in (("subventions", FaitSubventionEpa), ("dividendes", FaitDividende)):
            objets = []
            for ligne in self.donnees[table].to_dict("records"):
                organisme = refs[ligne.pop("organisme_id")]
                objets.append(modele(organisme=organisme, **ligne, **commun))
            modele.objects.bulk_create(objets)
            self.comptes[table] = {"lues": len(objets), "chargees": len(objets), "rejetees": 0}
            total += len(objets)
        validations, resultats = {}, {}
        for table, index in (("validations", validations), ("resultats", resultats)):
            for ligne in self.donnees[table].to_dict("records"):
                index.setdefault(ligne["organisme_id"], []).append(ligne)
        sante, gouvernance = [], []
        for code, organisme in refs.items():
            transmis, resultat, statut = situation_organisme(validations.get(code, []), resultats.get(code, []))
            sante.append(FaitSanteFinanciere(organisme=organisme, resultat=resultat, statut=statut, **commun))
            gouvernance.append(FaitGouvernance(organisme=organisme, etats_financiers_transmis=transmis, **commun))
        FaitSanteFinanciere.objects.bulk_create(sante)
        FaitGouvernance.objects.bulk_create(gouvernance)
        for table in ("sante", "gouvernance"):
            self.comptes[table] = {"lues": len(refs), "chargees": len(refs), "rejetees": 0}
        # Totaux de rapprochement exacts conservés dans le journal du chargement.
        self.informations_chargement["totaux"] = {
            f"{table}_{champ}": str(sum(self.donnees[table][champ], Decimal(0)))
            for table, champs in (("subventions", ("prevu", "paye")), ("dividendes", ("vote", "encaisse")))
            for champ in champs
        }
        return total + len(sante) + len(gouvernance)
