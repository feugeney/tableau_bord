"""Données d'illustration des domaines non raccordés (commande seed_demo).

Règles :
- statut_source = « demo » : chaque page et chaque indicateur l'affichent (« · illustration ») ;
- aucun chiffre fictif n'est attribué à un organisme ou à une personne réels : bureaux, centres,
  ministères et organismes sont nommés « A, B, C… » ou « fictif » ;
- ordres de grandeur de la maquette (milliards de GNF), tirage déterministe (graine fixe) ;
- une source déjà raccordée (statut « réel ») n'est jamais écrasée.
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.referentiels.models import (
    RefBureauDouane,
    RefCategorieBien,
    RefCentreImpots,
    RefImpot,
    RefNatureDroitDouane,
    RefOrganisme,
    RefSecteurActivite,
    RefSection,
    RefTypeCreancier,
    TypeOrganisme,
)

from .models import Chargement, Source, StatutChargement, StatutSource

MD = Decimal(10**9)
GRAINE = 2026


def mds(x: float) -> Decimal:
    return (Decimal(str(round(x, 3))) * MD).quantize(Decimal("0.01"))


# ---------------------------------------------------------------- référentiels

IMPOTS = [  # code, libellé, objectif annuel (Mds)
    ("TVA_INT", "TVA intérieure", 5400),
    ("MINES", "Impôts et redevances miniers", 4300),
    ("IS", "Impôt sur les sociétés", 3100),
    ("RTS", "Retenue sur traitements et salaires", 2600),
    ("TSPP", "Taxe spécifique sur les produits pétroliers", 1800),
    ("ENREG", "Droits d'enregistrement et de timbre", 900),
    ("FONCIER", "Contribution foncière unique", 600),
    ("AUTRES_F", "Autres impôts et taxes", 500),
]
CENTRES = [(f"CTR_{l}", f"Centre de gestion {l}") for l in "ABCDEF"]
SECTEURS = [
    ("MINES", "Mines et carrières"),
    ("TELECOM", "Télécommunications"),
    ("BANQUE", "Banques et assurances"),
    ("BTP", "Bâtiment et travaux publics"),
    ("COMMERCE", "Commerce"),
    ("INDUSTRIE", "Industrie"),
    ("SERVICES", "Services"),
]
NATURES_DROITS = [  # code, libellé, objectif annuel (Mds)
    ("DD", "Droit de douane", 3100),
    ("TVA_IMP", "TVA à l'importation", 2900),
    ("TSPP_IMP", "Taxe sur les produits pétroliers importés", 1400),
    ("RS", "Redevance statistique", 450),
    ("PC", "Prélèvement communautaire", 350),
    ("AUTRES_D", "Autres droits et taxes", 300),
]
BUREAUX = [
    ("BUR_PA", "Bureau portuaire A"),
    ("BUR_PB", "Bureau portuaire B"),
    ("BUR_AE", "Bureau aéroportuaire"),
    ("BUR_FC", "Bureau frontalier C"),
    ("BUR_FD", "Bureau frontalier D"),
    ("BUR_IE", "Bureau intérieur E"),
]
CREANCIERS = [  # code, libellé, extérieure, encours (Mds)
    ("MULTI", "Créanciers multilatéraux", True, 38000),
    ("BILAT", "Créanciers bilatéraux", True, 21000),
    ("COMM_EXT", "Créanciers commerciaux extérieurs", True, 6500),
    ("TITRES", "Titres publics (marché intérieur)", False, 14500),
    ("ARRIERES", "Arriérés intérieurs", False, 5200),
]
CATEGORIES_BIENS = [  # code, libellé, valeur brute (Mds), taux d'amortissement, nombre de biens
    ("BATIMENTS", "Bâtiments administratifs", 14200, 0.38, 4800),
    ("VEHICULES", "Véhicules et engins", 3900, 0.62, 11200),
    ("INFORMATIQUE", "Matériel informatique", 1100, 0.71, 58000),
    ("MOBILIER", "Mobilier et matériel de bureau", 800, 0.55, 142000),
    ("EQUIPEMENTS", "Équipements techniques", 2600, 0.47, 23000),
    ("TERRAINS", "Terrains", 5400, 0.0, 1300),
]
TYPES_EPA = [
    "Hôpital national",
    "Université publique",
    "Office national",
    "Agence nationale",
    "Institut national",
    "Fonds national",
    "Centre national",
    "École nationale",
]
TYPES_SOCIETES = [
    "Société minière",
    "Société d'électricité",
    "Société des eaux",
    "Banque publique",
    "Société de télécommunications",
    "Société de transport",
    "Société agro-industrielle",
    "Société immobilière",
]

SOURCES_DEMO = ["safig", "sydonia", "scie", "dette", "fugas", "sicom", "sysop", "telemo"]


def _refs(modele, lignes):
    for code, libelle, *_ in lignes:
        modele.objects.update_or_create(code=code, defaults={"libelle": libelle})


def _sections_fictives(n=8) -> list[str]:
    codes = []
    for i in range(n):
        code = f"F{i + 1:02d}"
        RefSection.objects.update_or_create(
            code=code,
            defaults={
                "libelle": f"Ministère fictif {chr(65 + i)}",
                "libelle_court": f"Ministère fictif {chr(65 + i)}",
                "type": "ministere",
                "fictif": True,
            },
        )
        codes.append(code)
    return codes


def _organismes_fictifs(r: random.Random) -> tuple[list[RefOrganisme], list[RefOrganisme]]:
    """232 organismes fictifs : 152 EPA et 80 sociétés publiques."""

    def creer(prefixe, types, n, type_org):
        objets = []
        for i in range(n):
            nom = f"{types[i % len(types)]} {chr(65 + (i // len(types)) % 26)}{'' if i < 26 * len(types) else i}"
            o, _ = RefOrganisme.objects.update_or_create(
                identifiant_etat=f"DEMO-{prefixe}-{i + 1:03d}",
                defaults={"nom": nom, "type": type_org, "fictif": True},
            )
            objets.append(o)
        return objets

    return creer("EPA", TYPES_EPA, 152, TypeOrganisme.EPA), creer("SOC", TYPES_SOCIETES, 80, TypeOrganisme.SOCIETE)


# -------------------------------------------------------------------- génération


class Generateur:
    def __init__(self, exercice: int, date_situation: date):
        self.exercice = exercice
        self.date_situation = date_situation
        self.r = random.Random(GRAINE)
        # Mois écoulés de l'exercice à la date de situation.
        self.mois = list(range(1, 13)) if date_situation.year > exercice else list(range(1, date_situation.month + 1))

    def _chargement(self, source: Source) -> Chargement:
        return Chargement.objects.create(
            source=source,
            fichier="seed_demo (données d'illustration)",
            exercice=self.exercice,
            date_situation=self.date_situation,
            statut=StatutChargement.SUCCES,
            fin=timezone.now(),
            duree_secondes=0,
            detail={"demo": True},
        )

    def _commun(self, ch: Chargement) -> dict:
        return {
            "exercice": self.exercice,
            "date_situation": self.date_situation,
            "source_id": ch.source_id,
            "chargement_id": ch.id,
        }

    def _saison(self, m: int) -> float:
        """Profil mensuel : creux en début d'année, pic en fin d'année."""
        return 0.85 + 0.3 * (m - 1) / 11

    # --- SAFIG
    def safig(self, ch):
        from apps.recettes_fiscales.models import (
            FaitContentieux,
            FaitContribuables,
            FaitRecouvrementFiscal,
            FaitResteARecouvrer,
        )

        _refs(RefImpot, IMPOTS)
        _refs(RefCentreImpots, CENTRES)
        _refs(RefSecteurActivite, SECTEURS)
        c = self._commun(ch)
        poids_centres = [0.42, 0.18, 0.14, 0.11, 0.09, 0.06]
        impots = {i.code: i.id for i in RefImpot.objects.filter(code__in=[x[0] for x in IMPOTS])}
        centres = {x.code: x.id for x in RefCentreImpots.objects.filter(code__in=[x[0] for x in CENTRES])}
        secteurs = {x.code: x.id for x in RefSecteurActivite.objects.filter(code__in=[x[0] for x in SECTEURS])}
        lignes = []
        for code, _, annuel in IMPOTS:
            performance = self.r.uniform(0.74, 1.04)
            for m in self.mois:
                objectif_m = annuel / 12 * self._saison(m)
                for (centre, _), poids in zip(CENTRES, poids_centres):
                    secteur = SECTEURS[self.r.randrange(len(SECTEURS))][0]
                    lignes.append(
                        FaitRecouvrementFiscal(
                            **c,
                            impot_id=impots[code],
                            centre_id=centres[centre],
                            secteur_id=secteurs[secteur],
                            mois=m,
                            objectif=mds(objectif_m * poids),
                            recouvre=mds(objectif_m * poids * performance * self.r.uniform(0.92, 1.08)),
                        )
                    )
        FaitRecouvrementFiscal.objects.bulk_create(lignes)
        restes = []
        for code, _, annuel in IMPOTS:
            for anciennete, part in (("moins d'un an", 0.09), ("1 à 3 ans", 0.04), ("plus de 3 ans", 0.02)):
                restes.append(
                    FaitResteARecouvrer(
                        **c,
                        impot_id=impots[code],
                        anciennete=anciennete,
                        montant=mds(annuel * part * self.r.uniform(0.7, 1.3)),
                    )
                )
        FaitResteARecouvrer.objects.bulk_create(restes)
        FaitContentieux.objects.bulk_create(
            [
                FaitContentieux(
                    **c,
                    impot_id=impots[code],
                    stade=stade,
                    nombre_dossiers=self.r.randint(20, 240),
                    montant=mds(annuel * part * self.r.uniform(0.6, 1.2)),
                )
                for code, _, annuel in IMPOTS[:5]
                for stade, part in (("Réclamation", 0.03), ("Commission de recours", 0.02), ("Tribunal", 0.012))
            ]
        )
        FaitContribuables.objects.bulk_create(
            [
                FaitContribuables(
                    **c,
                    centre_id=centres[code],
                    mois=m,
                    actifs=int(48300 * poids * (0.96 + m / 300)),
                    teledeclarants=int(48300 * poids * (0.96 + m / 300) * (0.52 + m * 0.008)),
                )
                for (code, _), poids in zip(CENTRES, poids_centres)
                for m in self.mois
            ]
        )

    # --- SYDONIA
    def sydonia(self, ch):
        from apps.douanes.models import FaitDeclaration, FaitExoneration, FaitRecetteDouane

        _refs(RefNatureDroitDouane, NATURES_DROITS)
        _refs(RefBureauDouane, BUREAUX)
        c = self._commun(ch)
        natures = {x.code: x.id for x in RefNatureDroitDouane.objects.filter(code__in=[n[0] for n in NATURES_DROITS])}
        bureaux = {x.code: x.id for x in RefBureauDouane.objects.filter(code__in=[b[0] for b in BUREAUX])}
        poids = [0.46, 0.21, 0.12, 0.09, 0.07, 0.05]
        lignes = []
        for code, _, annuel in NATURES_DROITS:
            perf = self.r.uniform(0.8, 1.03)
            for m in self.mois:
                for (bur, _), p in zip(BUREAUX, poids):
                    obj = annuel / 12 * self._saison(m) * p
                    lignes.append(
                        FaitRecetteDouane(
                            **c,
                            nature_droit_id=natures[code],
                            bureau_id=bureaux[bur],
                            mois=m,
                            objectif=mds(obj),
                            recouvre=mds(obj * perf * self.r.uniform(0.9, 1.1)),
                        )
                    )
        FaitRecetteDouane.objects.bulk_create(lignes)
        decl = []
        for m in self.mois:
            for (bur, _), p in zip(BUREAUX, poids):
                for circuit, part, delai in (("vert", 0.55, 1), ("jaune", 0.32, 3), ("rouge", 0.13, 6)):
                    j = date(self.exercice, m, self.r.randint(1, 28))
                    decl.append(
                        FaitDeclaration(
                            **c,
                            bureau_id=bureaux[bur],
                            circuit=circuit,
                            date_enregistrement=j,
                            date_mainlevee=j + timedelta(days=delai + self.r.randint(0, 2)),
                            nombre=int(9000 * p * part * self.r.uniform(0.85, 1.15)),
                        )
                    )
        FaitDeclaration.objects.bulk_create(decl)
        FaitExoneration.objects.bulk_create(
            [
                FaitExoneration(
                    **c,
                    regime=regime,
                    beneficiaire_type=benef,
                    mois=m,
                    montant=mds(base / 12 * self.r.uniform(0.8, 1.2)),
                )
                for regime, benef, base in (
                    ("Conventions minières", "Sociétés minières (fictives)", 1300),
                    ("Code des investissements", "Entreprises agréées", 520),
                    ("Marchés publics sur financement extérieur", "Titulaires de marchés", 410),
                    ("Organisations internationales et ONG", "Organisations", 160),
                )
                for m in self.mois
            ]
        )

    # --- SCIE
    def scie(self, ch):
        from apps.tresor.models import FaitDelaiPaiement, FaitDepotsCorrespondants, FaitFluxTresorerie, FaitTofe

        c = self._commun(ch)
        solde = 3200.0
        flux = []
        jour = date(self.exercice, 1, 1)
        fin = min(self.date_situation, date(self.exercice, 12, 31))
        while jour <= fin:
            if jour.weekday() < 5:
                enc = self.r.uniform(60, 150) * self._saison(jour.month)
                dec = self.r.uniform(55, 160) * self._saison(jour.month) * (1.25 if jour.day > 24 else 1)
                solde = max(400.0, solde + enc - dec)
                flux.append(
                    FaitFluxTresorerie(**c, jour=jour, encaissements=mds(enc), decaissements=mds(dec), solde=mds(solde))
                )
            jour += timedelta(days=1)
        FaitFluxTresorerie.objects.bulk_create(flux, batch_size=1000)
        FaitDelaiPaiement.objects.bulk_create(
            [
                FaitDelaiPaiement(
                    **c,
                    mois=m,
                    delai_moyen_jours=Decimal(str(round(self.r.uniform(18, 46), 1))),
                    nombre_mandats=self.r.randint(2200, 4800),
                )
                for m in self.mois
            ]
        )
        FaitDepotsCorrespondants.objects.bulk_create(
            [
                FaitDepotsCorrespondants(**c, categorie=cat, montant=mds(v))
                for cat, v in (
                    ("Collectivités locales", 640),
                    ("Établissements publics", 1180),
                    ("Particuliers et divers", 210),
                )
            ]
        )
        nb = len(self.mois)
        FaitTofe.objects.bulk_create(
            [
                FaitTofe(**c, poste_code=code, poste_libelle=lib, ordre=i, montant=mds(v * nb / 12))
                for i, (code, lib, v) in enumerate(
                    (
                        ("REC_NON_FISC", "Recettes non fiscales", 1450),
                        ("DONS", "Dons", 1900),
                        ("FIN_EXT", "Financement extérieur (tirages)", 5200),
                        ("FIN_INT", "Financement intérieur net", 3100),
                    )
                )
            ]
        )

    # --- Dette
    def dette(self, ch):
        from apps.dette.models import FaitEcheancierDette, FaitEncoursDette, FaitIndicateurMacro

        c = self._commun(ch)
        for code, lib, ext, _ in CREANCIERS:
            RefTypeCreancier.objects.update_or_create(code=code, defaults={"libelle": lib, "exterieur": ext})
        types = {t.code: t.id for t in RefTypeCreancier.objects.filter(code__in=[x[0] for x in CREANCIERS])}
        FaitEncoursDette.objects.bulk_create(
            [
                FaitEncoursDette(
                    **c,
                    type_creancier_id=types[code],
                    exterieure=ext,
                    date=self.date_situation,
                    encours=mds(v * self.r.uniform(0.97, 1.03)),
                )
                for code, _, ext, v in CREANCIERS
            ]
        )
        FaitEcheancierDette.objects.bulk_create(
            [
                FaitEcheancierDette(
                    **c,
                    annee=self.exercice + k,
                    exterieure=ext,
                    principal=mds(base_p * (1 + 0.06 * k) * self.r.uniform(0.9, 1.1)),
                    interets=mds(base_i * (1 - 0.03 * k) * self.r.uniform(0.9, 1.1)),
                )
                for k in range(5)
                for ext, base_p, base_i in ((True, 4200, 1650), (False, 3100, 1450))
            ]
        )
        FaitIndicateurMacro.objects.bulk_create(
            [
                FaitIndicateurMacro(**c, annee=self.exercice, indicateur="pib", valeur=mds(212000)),
            ]
        )

    # --- FUGAS
    def fugas(self, ch):
        from apps.paie.models import FaitControlePaie, FaitPaie

        c = self._commun(ch)
        sections = _sections_fictives()
        poids = [0.31, 0.22, 0.14, 0.1, 0.08, 0.06, 0.05, 0.04]
        lignes = []
        for m in self.mois:
            effectif_total = 118000 + m * 150
            for s, p in zip(sections, poids):
                eff = int(effectif_total * p)
                brute = eff * self.r.uniform(3.6, 4.1) / 1000  # ≈ 3,8 millions GNF par agent et par mois
                lignes.append(
                    FaitPaie(
                        **c, mois=m, section_id=s, effectif=eff, masse_brute=mds(brute), masse_nette=mds(brute * 0.83)
                    )
                )
        FaitPaie.objects.bulk_create(lignes)
        FaitControlePaie.objects.bulk_create(
            [
                FaitControlePaie(**c, controle=ctl, nombre_agents=n, montant=mds(v))
                for ctl, n, v in (
                    ("doublons", 412, 1.6),
                    ("sans_nif", 2380, 8.9),
                    ("sans_affectation", 1120, 4.2),
                    ("departs_retraite", 1760, 0),
                )
            ]
        )

    # --- SICOM
    def sicom(self, ch):
        from apps.patrimoine.models import (
            FaitControlePatrimoine,
            FaitDeploiementSicom,
            FaitParcVehicules,
            FaitPatrimoine,
        )

        c = self._commun(ch)
        _refs(RefCategorieBien, CATEGORIES_BIENS)
        cats = {x.code: x.id for x in RefCategorieBien.objects.filter(code__in=[k[0] for k in CATEGORIES_BIENS])}
        sections = _sections_fictives()
        poids = [0.24, 0.18, 0.15, 0.12, 0.1, 0.09, 0.07, 0.05]
        lignes = []
        for code, _, brute, amort, nb in CATEGORIES_BIENS:
            for s, p in zip(sections, poids):
                vb = brute * p * self.r.uniform(0.85, 1.15)
                nbs = int(nb * p)
                lignes.append(
                    FaitPatrimoine(
                        **c,
                        categorie_id=cats[code],
                        section_id=s,
                        valeur_brute=mds(vb),
                        valeur_nette=mds(vb * (1 - amort)),
                        nombre_biens=nbs,
                        biens_immatricules=int(nbs * self.r.uniform(0.55, 0.9)),
                    )
                )
        FaitPatrimoine.objects.bulk_create(lignes)
        FaitParcVehicules.objects.bulk_create(
            [
                FaitParcVehicules(**c, etat=etat, type_vehicule=t, nombre=n)
                for etat, t, n in (
                    ("en_service", "Véhicules légers", 6100),
                    ("en_service", "Engins", 740),
                    ("en_panne", "Véhicules légers", 1650),
                    ("en_panne", "Engins", 310),
                    ("hors_usage", "Véhicules légers", 2040),
                    ("hors_usage", "Engins", 360),
                )
            ]
        )
        FaitControlePatrimoine.objects.bulk_create(
            [
                FaitControlePatrimoine(**c, controle=ctl, nombre=n, montant=mds(v))
                for ctl, n, v in (
                    ("non_inventories_2ans", 18400, 1240),
                    ("sans_detenteur", 6200, 310),
                    ("vehicules_a_reformer", 2400, 96),
                    ("ecart_scie", 0, 820),
                )
            ]
        )
        FaitDeploiementSicom.objects.create(**c, institutions_actives=31, institutions_prevues=48)

    # --- SYSOP
    def sysop(self, ch):
        from apps.portefeuille.models import (
            FaitBudgetEpa,
            FaitDividende,
            FaitGouvernance,
            FaitSanteFinanciere,
            FaitSubventionEpa,
        )

        c = self._commun(ch)
        epa, societes = _organismes_fictifs(self.r)
        prorata = len(self.mois) / 12
        FaitSubventionEpa.objects.bulk_create(
            [
                FaitSubventionEpa(
                    **c,
                    organisme_id=o.id,
                    prevu=mds(p := self.r.uniform(4, 180)),
                    paye=mds(p * prorata * self.r.uniform(0.35, 1.0)),
                    transfert_chaine_depense=mds(p * prorata * self.r.uniform(0.5, 1.05)),
                )
                for o in epa
            ]
        )
        FaitDividende.objects.bulk_create(
            [
                FaitDividende(
                    **c,
                    organisme_id=o.id,
                    vote=mds(v := self.r.choice([0, 0, 2, 5, 12, 30, 85, 160])),
                    encaisse=mds(v * self.r.choice([0, 0.4, 1, 1])),
                )
                for o in societes
            ]
        )
        statuts = ["excedentaire"] * 5 + ["equilibre"] * 3 + ["deficitaire"] * 4 + ["non_transmis"] * 3
        sante, gouv, budgets = [], [], []
        for o in epa + societes:
            st = self.r.choice(statuts)
            sante.append(
                FaitSanteFinanciere(
                    **c,
                    organisme_id=o.id,
                    statut=st,
                    resultat=None if st == "non_transmis" else mds(self.r.uniform(-25, 40) if st != "equilibre" else 0),
                )
            )
            gouv.append(
                FaitGouvernance(
                    **c,
                    organisme_id=o.id,
                    etats_financiers_transmis=st != "non_transmis",
                    mandats_expires=self.r.choice([0, 0, 0, 1, 2]),
                )
            )
            if o.type == TypeOrganisme.EPA:
                budgets.append(
                    FaitBudgetEpa(
                        **c,
                        organisme_id=o.id,
                        budget_primitif=mds(self.r.uniform(5, 250)),
                        saisi=self.r.random() < 0.72,
                    )
                )
        FaitSanteFinanciere.objects.bulk_create(sante)
        FaitGouvernance.objects.bulk_create(gouv)
        FaitBudgetEpa.objects.bulk_create(budgets)

    # --- Telemo (marchés publics) : flux F3 (réservations), F4 (marchés immatriculés), F5 (paiements)
    def telemo(self, ch):
        from apps.marches_publics.models import FaitMarche, FaitPaiementMarche, FaitReservationCredit

        c = self._commun(ch)
        autorites = [f"Autorité contractante {chr(65 + i)}" for i in range(12)]
        titulaires = [(f"DEMO-{9000 + i}", f"Entreprise {chr(65 + i % 26)}-{i + 1:03d}") for i in range(70)]
        types = [
            ("travaux", 0.35, (1, 90)),
            ("fournitures", 0.3, (0.2, 15)),
            ("services", 0.2, (0.1, 6)),
            ("prestations_intellectuelles", 0.15, (0.1, 4)),
        ]
        modes = [
            ("aoo", 0.5, 95),
            ("cotation", 0.12, 30),
            ("drp", 0.13, 40),
            ("aor", 0.1, 75),
            ("entente_directe", 0.15, 15),
        ]
        debut = date(self.exercice, 1, 1)
        fin = min(self.date_situation, date(self.exercice, 12, 31))
        duree = max(1, (fin - debut).days)
        libelles_types = dict(FaitMarche.TYPES)
        reservations, marches, paiements = [], [], []
        for i in range(460):
            type_ = self.r.choices(types, weights=[t[1] for t in types])[0]
            mode = self.r.choices(modes, weights=[m[1] for m in modes])[0]
            autorite = self.r.choice(autorites)
            ttc = self.r.uniform(*type_[2]) * (1.3 if mode[0] == "entente_directe" else 1)
            visa = debut + timedelta(days=self.r.randint(0, duree))
            num_res = f"RES-{self.exercice}-{i + 1:05d}"
            # Réservation (F3) : légèrement supérieure au marché ; 4 % des marchés la dépassent.
            reserve = ttc * (self.r.uniform(0.85, 0.97) if self.r.random() < 0.04 else self.r.uniform(1.0, 1.12))
            reservations.append(
                FaitReservationCredit(
                    **c,
                    numero_reservation=num_res,
                    date_creation=visa - timedelta(days=self.r.randint(2, 15)),
                    date_validation=visa - timedelta(days=self.r.randint(0, 2)),
                    date_visa=visa,
                    ligne_budgetaire=f"000.F{self.r.randint(1, 8):02d}.{self.r.choice(['2', '3', '5'])}.1.1.10.01",
                    objet=f"{libelles_types[type_[0]]} (réservation fictive n° {i + 1})",
                    autorite_contractante=autorite,
                    montant_reserve=mds(reserve),
                )
            )
            immatriculation = visa + timedelta(days=max(5, int(self.r.gauss(mode[2], mode[2] * 0.35))))
            if immatriculation > fin or self.r.random() < 0.06:
                continue  # réservation pas encore (ou jamais) utilisée par un marché
            nif, nom = self.r.choice(titulaires)
            ht = ttc / 1.18
            statut = self.r.choices(
                ["immatricule", "en_execution", "receptionne", "resilie"], weights=[0.2, 0.6, 0.17, 0.03]
            )[0]
            numero = f"MP-{self.exercice}-{i + 1:05d}"
            marches.append(
                FaitMarche(
                    **c,
                    numero_immatriculation=numero,
                    date_immatriculation=immatriculation,
                    numero_reservation="" if self.r.random() < 0.03 else num_res,
                    objet=f"{libelles_types[type_[0]]} (marché fictif n° {i + 1})",
                    type_marche=type_[0],
                    mode_passation=mode[0],
                    autorite_contractante=autorite,
                    titulaire_nif=nif,
                    titulaire=nom,
                    montant_ht=mds(ht),
                    montant_taxes=mds(ttc - ht),
                    montant_ttc=mds(ttc),
                    date_signature=immatriculation - timedelta(days=self.r.randint(1, 10)),
                    date_approbation=immatriculation - timedelta(days=self.r.randint(0, 3)),
                    delai_execution_jours=self.r.choice([60, 90, 120, 180, 270, 365]),
                    avance_demarrage_taux=Decimal(self.r.choice(["0", "0.10", "0.15", "0.20"])),
                    retenue_garantie_taux=Decimal("0.05"),
                    modalites_paiement="Avance de démarrage, acomptes sur décomptes, retenue de garantie de 5 %",
                    statut=statut,
                    montant_avenants=mds(ttc * self.r.choice([0, 0, 0, 0.08, 0.15])),
                    recours=self.r.random() < 0.04,
                )
            )
            # Paiements (F5) : 0 à 4 paiements ; 1 % des marchés payés au-delà du montant.
            part = {
                "immatricule": 0,
                "en_execution": self.r.uniform(0.1, 0.7),
                "receptionne": 1.0,
                "resilie": self.r.uniform(0, 0.3),
            }[statut]
            if self.r.random() < 0.01:
                part = 1.12
            nb = 0 if part == 0 else self.r.randint(1, 4)
            for k in range(nb):
                jour = immatriculation + timedelta(days=int(self.r.uniform(15, 60) * (k + 1)))
                if jour > fin:
                    break
                paiements.append(
                    FaitPaiementMarche(
                        **c,
                        numero_immatriculation=numero,
                        date_paiement=jour,
                        reference_paiement=f"BCRG-{self.exercice}-{len(paiements) + 1:06d}",
                        montant_paiement=mds(ttc * part / nb),
                    )
                )
        # Paiements sans marché connu (anomalie de rapprochement).
        for k in range(3):
            paiements.append(
                FaitPaiementMarche(
                    **c,
                    numero_immatriculation=f"MP-{self.exercice}-X{k:03d}",
                    date_paiement=fin,
                    reference_paiement=f"BCRG-{self.exercice}-X{k:03d}",
                    montant_paiement=mds(self.r.uniform(0.5, 3)),
                )
            )
        FaitReservationCredit.objects.bulk_create(reservations)
        FaitMarche.objects.bulk_create(marches)
        FaitPaiementMarche.objects.bulk_create(paiements)


def situation_par_defaut() -> tuple[int, date]:
    """Même exercice et même date que la dernière situation Chaîne Dépense, sinon aujourd'hui."""
    ch = (
        Chargement.objects.filter(source__code="chaine_depense", statut=StatutChargement.SUCCES)
        .exclude(date_situation=None)
        .order_by("-date_situation")
        .first()
    )
    if ch:
        return ch.exercice, ch.date_situation
    today = date.today()
    return today.year, today


def generer(
    exercice: int | None = None, date_situation: date | None = None, sources: list[str] | None = None
) -> dict[str, str]:
    """Charge les données d'illustration ; renvoie l'état par source."""
    if exercice is None or date_situation is None:
        e, d = situation_par_defaut()
        exercice, date_situation = exercice or e, date_situation or d
    g = Generateur(exercice, date_situation)
    resultat = {}
    for code in sources or SOURCES_DEMO:
        source = Source.objects.get(code=code)
        if source.statut == StatutSource.REEL:
            resultat[code] = "ignorée (source réelle raccordée)"
            continue
        with transaction.atomic():
            # Les anciennes données d'illustration sont remplacées (suppression en cascade des faits).
            Chargement.objects.filter(source=source, detail__demo=True).delete()
            ch = g._chargement(source)
            getattr(g, code)(ch)
            source.statut = StatutSource.DEMO
            source.save(update_fields=["statut"])
        resultat[code] = "chargée"

    from etl.mart import invalider_cache_api, rafraichir_vues

    rafraichir_vues()
    try:
        from .alertes import evaluer_alertes

        evaluer_alertes()
    finally:
        invalider_cache_api()
    return resultat


def supprimer() -> None:
    """Retire toutes les données d'illustration ; les sources redeviennent « non raccordées »."""
    for source in Source.objects.filter(statut=StatutSource.DEMO):
        Chargement.objects.filter(source=source, detail__demo=True).delete()
        source.statut = StatutSource.NON_RACCORDE
        source.save(update_fields=["statut"])
    from etl.mart import invalider_cache_api, rafraichir_vues

    rafraichir_vues()
    invalider_cache_api()
