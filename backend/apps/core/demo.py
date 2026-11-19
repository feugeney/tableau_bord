"""Données d'illustration des domaines non raccordés (commande seed_demo).

Règles :
- statut_source = « demo » : chaque page et chaque indicateur l'affichent (« · illustration ») ;
- aucun chiffre fictif n'est attribué à un organisme ou à une personne réels : bureaux, centres,
  ministères et organismes sont nommés « A, B, C… » ou « fictif » ;
- ordres de grandeur de la maquette (milliards de GNF), tirage déterministe (graine fixe) ;
- une source déjà raccordée (statut « réel ») n'est jamais écrasée.
"""

from __future__ import annotations

import hashlib
import random
from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.referentiels.models import (
    TITRES,
    RefBeneficiaire,
    RefBureauDouane,
    RefCategorieBien,
    RefCentreImpots,
    RefEtatDossier,
    RefImpot,
    RefNatureDroitDouane,
    RefNatureEconomique,
    RefOrganisme,
    RefSecteurActivite,
    RefSection,
    RefSousSection,
    RefTypeCreancier,
    RefTypeProcedure,
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
CENTRES = [
    ("CTR_A", "Centre fictif des grandes entreprises"),
    ("CTR_B", "Centre fictif des moyennes entreprises"),
    ("CTR_C", "Centre des impôts fictif de Kaloum"),
    ("CTR_D", "Centre des impôts fictif de Matoto"),
    ("CTR_E", "Centre des impôts fictif de Kindia"),
    ("CTR_F", "Centre des impôts fictif de Kankan"),
]
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
    ("BUR_PA", "Bureau portuaire fictif (conteneurs)"),
    ("BUR_PB", "Bureau portuaire fictif (vracs et hydrocarbures)"),
    ("BUR_AE", "Bureau aéroportuaire fictif"),
    ("BUR_FC", "Bureau frontalier fictif de Pamelap"),
    ("BUR_FD", "Bureau frontalier fictif de Nzérékoré"),
    ("BUR_IE", "Bureau intérieur fictif de Kankan"),
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

# Ministères fictifs (codes F01 à F08) : libellé, libellé court, pilier Simandou 2040 (libellé de la source,
# None = hors pilier), programmes, projets d'investissement.
# Noms crédibles, toujours marqués « fictif » : aucun ne désigne un ministère réel.
MINISTERES_FICTIFS = [
    (
        "Ministère fictif de la Santé",
        "Santé (fictif)",
        "Sante et Bien-etre",
        ["Soins de santé primaires", "Lutte contre les maladies", "Pilotage et soutien"],
        [
            "Hôpital régional de Kankan",
            "Centres de santé de Boké",
            "Maternité de Labé",
            "Équipement des hôpitaux préfectoraux",
            "Laboratoire national de référence",
        ],
    ),
    (
        "Ministère fictif de l'Éducation",
        "Éducation (fictif)",
        "Education et Culture",
        ["Enseignement primaire", "Enseignement secondaire", "Alphabétisation"],
        [
            "Écoles primaires de Kindia",
            "Collèges de Faranah",
            "Cantines scolaires",
            "Manuels scolaires",
            "Lycée technique de Mamou",
        ],
    ),
    (
        "Ministère fictif des Infrastructures",
        "Infrastructures (fictif)",
        "Infrastructures, Technologie et Transport",
        ["Routes nationales", "Ouvrages d'art", "Entretien routier"],
        [
            "Route Kindia–Mamou",
            "Pont de Kouroussa",
            "Voirie urbaine de Conakry",
            "Pistes rurales de Siguiri",
            "Route Labé–Mali",
        ],
    ),
    (
        "Ministère fictif de l'Agriculture",
        "Agriculture (fictif)",
        "Agriculture, Industrie alimentaire et Commerce",
        ["Production végétale", "Élevage", "Aménagements hydro-agricoles"],
        [
            "Plaine rizicole de Koba",
            "Périmètres maraîchers de Pita",
            "Vaccination du cheptel",
            "Magasins de stockage de Gueckédou",
            "Semences améliorées",
        ],
    ),
    (
        "Ministère fictif de l'Énergie et de l'Hydraulique",
        "Énergie et Hydraulique (fictif)",
        "Infrastructures, Technologie et Transport",
        ["Électrification", "Eau potable", "Énergies renouvelables"],
        [
            "Ligne électrique Linsan–Fomi",
            "Forages de Dabola",
            "Centrales solaires rurales",
            "Adduction d'eau de Kissidougou",
            "Réseau électrique de Matoto",
        ],
    ),
    (
        "Ministère fictif de la Sécurité",
        "Sécurité (fictif)",
        None,
        ["Police nationale", "Protection civile", "Pilotage et soutien"],
        [
            "Commissariats de Nzérékoré",
            "Casernes de la protection civile",
            "Équipement des brigades",
            "Centre de formation de la police",
            "Vidéosurveillance de Conakry",
        ],
    ),
    (
        "Ministère fictif de l'Enseignement supérieur",
        "Enseignement supérieur (fictif)",
        "Education et Culture",
        ["Enseignement universitaire", "Recherche scientifique", "Bourses et œuvres universitaires"],
        [
            "Campus de Kankan",
            "Résidences universitaires",
            "Bibliothèque universitaire",
            "Laboratoires de recherche",
            "Institut supérieur de Boké",
        ],
    ),
    (
        "Ministère fictif de l'Économie et des Finances",
        "Économie et Finances (fictif)",
        "Economie, Finances et Assurances",
        ["Gestion des finances publiques", "Mobilisation des recettes", "Pilotage et soutien"],
        [
            "Informatisation des régies financières",
            "Hôtel des finances de Kindia",
            "Archivage numérique",
            "Formation des comptables publics",
            "Réseau du Trésor en préfecture",
        ],
    ),
]
VILLES = [
    "Conakry",
    "Kindia",
    "Boké",
    "Labé",
    "Mamou",
    "Faranah",
    "Kankan",
    "Nzérékoré",
    "Siguiri",
    "Kissidougou",
    "Guéckédou",
    "Macenta",
    "Kamsar",
    "Fria",
    "Dabola",
    "Pita",
    "Coyah",
    "Dubréka",
    "Kouroussa",
]
ACTIVITES_FOURNISSEURS = [
    "BTP",
    "Génie civil",
    "Informatique",
    "Fournitures de bureau",
    "Équipements médicaux",
    "Pharmacie",
    "Transport et logistique",
    "Hydraulique",
    "Énergie solaire",
    "Restauration collective",
]
FORMES = ["SARL", "SA", "SARLU"]
MOIS_FR = [
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
]
OBJETS_DEPENSE = {
    "3": [
        "Achat de fournitures de bureau",
        "Carburant et lubrifiants",
        "Entretien des véhicules",
        "Maintenance informatique",
        "Frais de mission",
        "Location de bureaux",
        "Électricité et eau",
    ],
    "4": [
        "Subvention de fonctionnement",
        "Bourses d'études",
        "Transfert aux collectivités locales",
        "Contribution aux organisations internationales",
    ],
}

SOURCES_DEMO = ["safig", "sydonia", "scie", "dette", "fugas", "sicom", "sysop", "telemo", "tofe"]
# Source raccordée en production : son illustration n'est chargée que sur demande explicite (--sources).
SOURCES_DEMO_SUR_DEMANDE = ["chaine_depense"]

# Chaîne Dépense : part des crédits par titre et taux d'engagement relatif au temps écoulé.
BUDGET_DEPENSE = 42000  # Mds, LFI totale illustrée
TITRES_DEPENSE = {"1": (0.14, 0.95), "2": (0.24, 1.0), "3": (0.19, 0.85), "4": (0.15, 0.9), "5": (0.28, 0.6)}
PROCEDURES_PAR_TITRE = {  # (libellé du référentiel, poids)
    "1": [("Debit d'office - NE PAS PAYER", 0.7), ("Procedure normale", 0.3)],
    "2": [("Procedure Solde", 0.8), ("Procedure normale", 0.2)],
    "autres": [
        ("Procedure normale", 0.55),
        ("Procedure Normale MP", 0.2),
        ("Procedure Normale Amenagee", 0.15),
        ("Procedure Normale devise", 0.05),
        ("Procedure Normale Amenagee MP", 0.05),
    ],
}


def _hors_chaine(procedure: str) -> bool:
    """Procédures payées hors chaîne (solde, débit d'office, régularisations)."""
    return procedure == "Procedure Solde" or "NE PAS PAYER" in procedure


def _refs(modele, lignes):
    for code, libelle, *_ in lignes:
        modele.objects.update_or_create(code=code, defaults={"libelle": libelle})


def _sections_fictives(n=8) -> list[str]:
    codes = []
    for i, (libelle, court, *_) in enumerate(MINISTERES_FICTIFS[:n]):
        code = f"F{i + 1:02d}"
        RefSection.objects.update_or_create(
            code=code,
            defaults={"libelle": libelle, "libelle_court": court, "type": "ministere", "fictif": True},
        )
        codes.append(code)
    return codes


def _entreprises_fictives(n: int) -> list[str]:
    """Raisons sociales crédibles, toujours marquées « fictive » : activité, ville, forme juridique."""
    return [
        f"{ACTIVITES_FOURNISSEURS[i % len(ACTIVITES_FOURNISSEURS)]} {VILLES[(i * 7) % len(VILLES)]} "
        f"{FORMES[i % len(FORMES)]} (fictive)"
        for i in range(n)
    ]


def _organismes_fictifs(r: random.Random) -> tuple[list[RefOrganisme], list[RefOrganisme]]:
    """232 organismes fictifs : 152 EPA et 80 sociétés publiques."""

    def creer(prefixe, types, n, type_org):
        objets = []
        for i in range(n):
            rang = "" if i < len(types) * len(VILLES) else f" {i // (len(types) * len(VILLES)) + 1}"
            nom = f"{types[i % len(types)]} de {VILLES[(i // len(types)) % len(VILLES)]}{rang} (organisme fictif)"
            o, _ = RefOrganisme.objects.update_or_create(
                identifiant_etat=f"DEMO-{prefixe}-{i + 1:03d}",
                defaults={"nom": nom, "type": type_org, "fictif": True},
            )
            objets.append(o)
        return objets

    return creer("EPA", TYPES_EPA, 152, TypeOrganisme.EPA), creer("SOC", TYPES_SOCIETES, 80, TypeOrganisme.SOCIETE)


# -------------------------------------------------------------------- génération


class Generateur:
    def tofe(self, ch: Chargement):
        from .tofe import creer_scenario

        if self.date_situation < date(self.exercice, 1, 1):
            raise ValueError("La date de situation TOFE ne peut pas précéder le début de l'exercice.")
        ch.detail = {**ch.detail, "profil": "tofe_illustration_v1", "scenario": creer_scenario(self.exercice)}
        ch.lignes_chargees = len(ch.detail["scenario"]["postes"])
        ch.save(update_fields=["detail", "lignes_chargees"])

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

    # --- Chaîne Dépense
    def chaine_depense(self, ch):
        from apps.depense.models import FaitEngagement, FaitOperation, FaitRegie, FaitSituationLigne

        c = self._commun(ch)
        sections = _sections_fictives()
        for code, libelle in TITRES.items():
            RefNatureEconomique.objects.update_or_create(
                code=code, defaults={"libelle": libelle, "niveau": 1, "titre": code}
            )
        procedures = {
            libelle: RefTypeProcedure.objects.get_or_create(
                libelle=libelle, defaults={"paiement_hors_chaine": _hors_chaine(libelle)}
            )[0].id
            for choix in PROCEDURES_PAR_TITRE.values()
            for libelle, _ in choix
        }
        etats = {
            libelle: RefEtatDossier.objects.get_or_create(libelle=libelle, defaults={"engagement_valide": valide})[0].id
            for libelle, valide in (("Depense engagee", True), ("Nouvel engagement", False))
        }
        fournisseurs = [
            RefBeneficiaire.objects.update_or_create(nom_normalise=nom.upper(), defaults={"nom_affiche": nom})[0].id
            for nom in _entreprises_fictives(60)
        ]
        poids_fournisseurs = [1 / (i + 1) ** 0.9 for i in range(len(fournisseurs))]
        beneficiaires_titre = {
            t: RefBeneficiaire.objects.update_or_create(nom_normalise=nom.upper(), defaults={"nom_affiche": nom})[0].id
            for t, nom in (("1", "Créancier fictif (service de la dette)"), ("2", "Agents publics (paie fictive)"))
        }

        avancement = len(self.mois) / 12
        poids_sections = [self.r.uniform(0.5, 2.0) for _ in sections]
        total_poids = sum(poids_sections)
        lignes, engagements, operations, regies = [], [], [], []
        k = 0
        for s, (section, poids) in enumerate(zip(sections, poids_sections)):
            _, _, pilier, programmes, projets = MINISTERES_FICTIFS[s]
            for titre, (part, rythme) in TITRES_DEPENSE.items():
                projet = titre == "5"
                n_sous = 5 if projet else 3
                for j in range(1, n_sous + 1):
                    code_ss = f"{section}-{'P' if projet else ''}{j}"
                    RefSousSection.objects.update_or_create(
                        code=code_ss,
                        defaults={
                            "libelle": f"{projets[j - 1]} (projet fictif)" if projet else programmes[j - 1],
                            "section_id": section,
                        },
                    )
                    lfi = BUDGET_DEPENSE * part * poids / total_poids / n_sous * self.r.uniform(0.6, 1.4)
                    lfi_absent = self.r.random() < 0.02
                    actuel = lfi * self.r.uniform(0.93, 1.10)
                    if lfi_absent:
                        lfi = 0
                    if projet and j == n_sous and s % 3 == 0:
                        taux = 0.0  # projet sans engagement
                    elif self.r.random() < 0.03:
                        taux = 1.03  # ligne en dépassement
                    else:
                        taux = min(avancement * rythme * self.r.uniform(0.75, 1.2), 0.98)

                    imputation = {
                        **c,
                        "type_budget": "BG",
                        "section_id": section,
                        "sous_section_id": code_ss,
                        "titre": titre,
                        "nature_id": titre,
                        "source_financement": "EXT" if projet and j % 2 == 0 else "INT",
                    }
                    choix = PROCEDURES_PAR_TITRE.get(titre, PROCEDURES_PAR_TITRE["autres"])
                    # Dette et personnel : un engagement par mois ; autres titres : 4 à 14 engagements.
                    mois_eng = (
                        self.mois
                        if titre in ("1", "2")
                        else [
                            self.r.choices(self.mois, weights=[self._saison(m) for m in self.mois])[0]
                            for _ in range(self.r.randint(4, 14))
                        ]
                    )
                    tailles = [self.r.uniform(0.3, 1.0) for _ in mois_eng]
                    engage_ligne = actuel * taux
                    somme = {"engage": 0.0, "liquide": 0.0, "ordonnance": 0.0, "vbp": 0.0, "paye": 0.0}
                    for m, t in zip(mois_eng, tailles):
                        if not engage_ligne:
                            break
                        k += 1
                        jour = (
                            min(self.r.randint(1, 28), self.date_situation.day)
                            if (self.date_situation.year == self.exercice and m == self.date_situation.month)
                            else self.r.randint(1, 28)
                        )
                        creation = date(self.exercice, m, jour)
                        age = (self.date_situation.year - creation.year) * 12 + self.date_situation.month - m
                        procedure = self.r.choices([p for p, _ in choix], weights=[w for _, w in choix])[0]
                        hors_chaine = _hors_chaine(procedure)
                        engage = engage_ligne * t / sum(tailles)
                        nouveau = not hors_chaine and age == 0 and self.r.random() < 0.3
                        liquide = 0.0 if nouveau else engage * min(1.0, 0.55 + 0.12 * age) * self.r.uniform(0.85, 1)
                        ordonnance = liquide * self.r.uniform(0.9, 1)
                        vbp = ordonnance * self.r.uniform(0.93, 1)
                        if hors_chaine:
                            paye = ordonnance
                        elif age >= 4 and self.r.random() < 0.15:
                            paye = vbp * self.r.uniform(0.2, 0.6)  # restes à payer anciens
                        else:
                            paye = vbp * self.r.uniform(0.8, 1)
                        beneficiaire = (
                            beneficiaires_titre.get(titre)
                            or self.r.choices(fournisseurs, weights=poids_fournisseurs)[0]
                        )
                        numero = f"DEMO-{self.exercice}-{k:06d}"
                        engagements.append(
                            FaitEngagement(
                                **imputation,
                                numero=numero,
                                cle_imputation=hashlib.sha1(code_ss.encode()).hexdigest(),
                                type_procedure_id=procedures[procedure],
                                etat_dossier_id=etats["Nouvel engagement" if nouveau else "Depense engagee"],
                                beneficiaire_id=beneficiaire,
                                objet=self._objet_depense(titre, m, projets[j - 1] if projet else ""),
                                devise="GNF",
                                date_creation=creation,
                                date_visa_cf=None if nouveau else creation + timedelta(days=self.r.randint(2, 15)),
                                date_maj=self.date_situation,
                                montant_initial=mds(engage),
                                montant_engage=mds(engage),
                                montant_engage_cf=mds(0 if nouveau else engage),
                                montant_liquide=mds(liquide),
                                montant_ordonnance=mds(ordonnance),
                                montant_vbp=mds(vbp),
                                montant_ecp=mds(vbp - paye),
                                montant_paye=mds(paye),
                            )
                        )
                        if paye:
                            operations.append(
                                FaitOperation(
                                    **imputation,
                                    numero_engagement=numero,
                                    type_procedure_id=procedures[procedure],
                                    etat_dossier_id=etats["Depense engagee"],
                                    type_origine="Mandat de paiement",
                                    beneficiaire_id=beneficiaire,
                                    objet=f"Paiement de l'engagement {numero} (fictif)",
                                    code_devise="GNF",
                                    date_visa_vbp=min(creation + timedelta(days=30 + 20 * age), self.date_situation),
                                    montant_engage=mds(engage),
                                    montant_liquide=mds(liquide),
                                    montant_vbp=mds(vbp),
                                    montant_ordonnance=mds(ordonnance),
                                    montant_paye=mds(paye),
                                    montant=mds(paye),
                                )
                            )
                        for cle, v in zip(somme, (engage, liquide, ordonnance, vbp, paye)):
                            somme[cle] += v

                    reserve = actuel * self.r.uniform(0, 0.03)
                    regie = actuel * 0.01 if titre == "3" and j == 1 else 0
                    lignes.append(
                        FaitSituationLigne(
                            **imputation,
                            cle_ligne=hashlib.sha1(f"BG|{code_ss}|{titre}".encode()).hexdigest(),
                            credit_initial_lfi=mds(lfi),
                            credit_lfr=mds(actuel),
                            credit_actuel=mds(actuel),
                            credit_disponible=mds(actuel - reserve - somme["engage"]),
                            credit_reserve=mds(reserve),
                            credit_engage=mds(somme["engage"]),
                            credit_engage_projet=mds(somme["engage"] * 0.02),
                            credit_engage_cf=mds(somme["engage"] * 0.98),
                            montant_liquide=mds(somme["liquide"]),
                            montant_ordonnance=mds(somme["ordonnance"]),
                            montant_vbp=mds(somme["vbp"]),
                            montant_encours_paiement=mds(somme["vbp"] - somme["paye"]),
                            montant_paye=mds(somme["paye"]),
                            avance_demarrage=mds(somme["engage"] * 0.05 if projet else 0),
                            montant_regie=mds(regie),
                            lfi_absent=lfi_absent,
                            attributs=self._attributs_depense(pilier, titre),
                        )
                    )
                    if regie:
                        regies.append(
                            FaitRegie(
                                **imputation,
                                gestionnaire=f"RG{s + 1:02d}",
                                numero_regie=f"REG-{section}",
                                nature_flux="avance",
                                montant_regie=mds(regie),
                                date_creation=date(self.exercice, 1, 15),
                                etat_dossier_brut="Régie ouverte",
                            )
                        )
        FaitSituationLigne.objects.bulk_create(lignes)
        FaitEngagement.objects.bulk_create(engagements, batch_size=1000)
        FaitOperation.objects.bulk_create(operations, batch_size=1000)
        FaitRegie.objects.bulk_create(regies)
        self._controles_depense(ch, lignes, engagements)

    def _attributs_depense(self, pilier: str | None, titre: str) -> dict:
        """Colonnes additionnelles de l'extraction, en proportions proches d'une extraction réelle."""
        from apps.depense.services import GREEN, PILIER

        attributs = {}
        # Dette hors pilier ; environ 8 % des autres lignes sans pilier renseigné.
        if pilier and titre != "1" and self.r.random() > 0.08:
            attributs[PILIER] = pilier
        if titre == "5":
            attributs[GREEN] = "OUI" if self.r.random() < 0.15 else "NON"
        elif titre == "3" and self.r.random() < 0.05:
            attributs[GREEN] = "OUI"
        return attributs

    def _objet_depense(self, titre: str, mois: int, projet: str) -> str:
        nom_mois = MOIS_FR[mois - 1]
        if titre == "1":
            objet = f"Service de la dette, échéance de {nom_mois}"
        elif titre == "2":
            objet = f"Salaires de {nom_mois}"
        elif titre == "5":
            objet = f"{self.r.choice(['Travaux', 'Équipements', 'Études et contrôle'])} : {projet}"
        else:
            objet = self.r.choice(OBJETS_DEPENSE[titre])
        return f"{objet} (fictif)"

    def _controles_depense(self, ch, lignes, engagements):
        """Mêmes contrôles que l'import Chaîne Dépense, calculés sur les données d'illustration (page Qualité)."""
        from apps.core import regles
        from apps.qualite.models import ResultatControle

        total_sc = sum((l.credit_engage for l in lignes), Decimal(0))
        total_eng = sum((e.montant_engage for e in engagements), Decimal(0))
        depassements = sum(regles.est_ligne_en_depassement(l.credit_disponible) for l in lignes)
        liq_sup = sum(regles.liquide_depasse_engage(l.montant_liquide, l.credit_engage) for l in lignes)
        absents = sum(l.lfi_absent for l in lignes)
        controles = [
            ResultatControle(
                chargement=ch,
                code="concordance_engage",
                libelle="Concordance du total engagé entre onglets",
                niveau="bloquant",
                reussi=regles.concordance_ok(total_sc, total_eng),
                valeur=total_sc - total_eng,
                detail={"situation_courante": str(total_sc), "liste_engagements": str(total_eng)},
            )
        ] + [
            ResultatControle(
                chargement=ch,
                code=code,
                libelle=libelle,
                niveau=niveau,
                reussi=nombre == 0 or niveau == "info",
                nombre=nombre,
            )
            for code, libelle, niveau, nombre in (
                ("doublons_cle_ligne", "Doublons sur la clé de ligne budgétaire", "avertissement", 0),
                (
                    "absents_credit_initial_lfi",
                    "Valeurs absentes dans « credit_initial_lfi » (comptées 0)",
                    "info",
                    absents,
                ),
                ("lignes_depassement", "Lignes en dépassement (disponible < 0)", "avertissement", depassements),
                ("liquide_sup_engage", "Lignes où le liquidé dépasse l'engagé", "avertissement", liq_sup),
                ("lignes_sans_section", "Lignes sans code section (rejetées)", "avertissement", 0),
            )
        ]
        ResultatControle.objects.bulk_create(controles)
        ch.lignes_lues = ch.lignes_chargees = len(lignes) + len(engagements)
        ch.detail["controles"] = [
            {
                "code": c.code,
                "libelle": c.libelle,
                "niveau": c.niveau,
                "reussi": c.reussi,
                "valeur": str(c.valeur) if c.valeur is not None else None,
                "nombre": c.nombre,
                "detail": c.detail,
            }
            for c in controles
        ]
        ch.save(update_fields=["detail", "lignes_lues", "lignes_chargees"])

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
        autorites = [f"Autorité contractante : {m[0]}" for m in MINISTERES_FICTIFS] + [
            f"Autorité contractante : {nom} (organisme fictif)"
            for nom in ("Hôpital national de Conakry", "Université de Kankan", "Agence des routes", "Office de l'eau")
        ]
        titulaires = [(f"DEMO-{9000 + i}", nom) for i, nom in enumerate(_entreprises_fictives(70))]
        projets = [p for m in MINISTERES_FICTIFS for p in m[4]]
        objets_marche = {
            "travaux": projets,
            "fournitures": [
                "Fournitures de bureau",
                "Véhicules de service",
                "Matériel informatique",
                "Médicaments essentiels",
                "Mobilier scolaire",
            ],
            "services": [
                "Gardiennage",
                "Nettoyage des locaux",
                "Maintenance des groupes électrogènes",
                "Transport du personnel",
            ],
            "prestations_intellectuelles": [
                "Étude de faisabilité",
                "Contrôle des travaux",
                "Audit financier",
                "Assistance technique",
            ],
        }
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
            objet = f"{libelles_types[type_[0]]} : {self.r.choice(objets_marche[type_[0]])}"
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
                    objet=f"{objet} (réservation fictive n° {i + 1})",
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
                    objet=f"{objet} (marché fictif n° {i + 1})",
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
    # Comme un chargement réel : exercice et dimension temps (regroupements par période de l'exploration).
    from apps.referentiels.models import RefExercice
    from apps.referentiels.temps import assurer_calendrier

    RefExercice.objects.get_or_create(annee=exercice, defaults={"libelle": str(exercice)})
    assurer_calendrier(exercice, exercice)
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
