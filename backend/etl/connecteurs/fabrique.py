"""Choix du connecteur d'une source d'après sa configuration (connecteurs interchangeables)."""

from __future__ import annotations

from datetime import date
from typing import Optional

from apps.core.models import Source, TypeConnecteur

from .base import BaseConnector, ErreurChargement
from .chaine_depense import ExcelChaineDepenseConnector, OracleChaineDepenseConnector
from .generique import ApiConnector, ExcelGenericConnector, PostgresConnector


def connecteur_pour(
    source: Source,
    fichier=None,
    nom_fichier: Optional[str] = None,
    exercice: Optional[int] = None,
    date_situation: Optional[date] = None,
    utilisateur_id: Optional[int] = None,
    table_cible: Optional[str] = None,
    onglet: Optional[str] = None,
) -> BaseConnector:
    utilisateur = None
    if utilisateur_id:
        from apps.core.models import Utilisateur

        utilisateur = Utilisateur.objects.filter(pk=utilisateur_id).first()
    commun = dict(exercice=exercice, date_situation=date_situation, utilisateur=utilisateur)
    conf = source.configuration or {}

    if fichier is not None:
        if source.code == "chaine_depense":
            return ExcelChaineDepenseConnector(fichier, nom_fichier=nom_fichier, **commun)
        # Sans table cible : toutes les tables dont le mapping désigne un onglet du classeur.
        cible = table_cible or conf.get("table_cible")
        return ExcelGenericConnector(
            source.code, cible, fichier, onglet=onglet or conf.get("onglet"), nom_fichier=nom_fichier, **commun
        )

    if source.connecteur == TypeConnecteur.ORACLE_CHAINE_DEPENSE:
        return OracleChaineDepenseConnector(configuration=conf, **commun)
    if source.connecteur == TypeConnecteur.API:
        return ApiConnector(source.code, conf, **commun)
    if source.connecteur == TypeConnecteur.POSTGRES:
        return PostgresConnector(source.code, conf["table_cible"], conf["requete"], **commun)
    raise ErreurChargement(f"Aucun chargement automatique pour {source.code} ({source.connecteur}).")
