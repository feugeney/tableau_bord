# Flux Chaîne de dépenses ↔ Telemo (marchés publics)

Ce document décrit la prise en charge, dans l'entrepôt, des cinq flux d'échange entre la Chaîne de dépenses
et Telemo, et ce qu'en affiche la page « Marchés publics ».

## 1. Prise en charge des flux

| Flux | Sens | Contenu | Prise en charge | Table de l'entrepôt |
|---|---|---|---|---|
| F1 | Chaîne de dépenses → Telemo | LFI / LFR : lignes budgétaires, dotations AE / CP | **Déjà couvert** par l'extraction de la Chaîne Dépense (crédits votés et actuels par ligne). Pas de second chargement. | `dw.fait_situation_ligne` (existant) |
| F2 | Chaîne de dépenses → Telemo | Modifications des lignes budgétaires (virements, reports, annulations) | **Déjà couvert** par la Chaîne Dépense (crédits actuels, mouvements). | `dw.fait_situation_ligne` (existant) |
| F3 | Chaîne de dépenses → Telemo | Réservations de crédit visées par le contrôleur financier | **Chargé** | `dw.fait_reservation_credit` |
| F4 | Telemo → Chaîne de dépenses | Marchés immatriculés | **Chargé** | `dw.fait_marche` |
| F5 | Chaîne de dépenses → Telemo | Paiements effectifs (BCRG) | **Chargé** | `dw.fait_paiement_marche` |

Les trois flux chargés le sont **en un seul chargement** par date de situation : trois chargements séparés à la
même date se masqueraient les uns les autres.

### Champs repris

**F3 – Réservations de crédit** : numéro de réservation, exercice, dates de création, de validation et de visa,
ligne budgétaire (clé d'imputation complète), objet, autorité contractante, montant réservé, devise.

**F4 – Marchés immatriculés** : numéro et date d'immatriculation, numéro de la réservation associée, objet, type
de marché, mode de passation, autorité contractante, exercice, NIF et raison sociale du titulaire, montants HT,
TTC et taxes, devise, dates de signature et d'approbation, délai d'exécution, modalités de paiement.

**F5 – Paiements** : numéro d'immatriculation du marché, date, référence et montant du paiement.

### Champs volontairement écartés (minimisation)

Les **coordonnées bancaires** du titulaire (banque, RIB / IBAN), son **adresse et ses coordonnées**, et son
**RCCM** sont transmis par F4 mais **ne sont pas repris** dans l'entrepôt. Le NIF et la raison sociale suffisent
au pilotage ; ces données n'ont pas à circuler dans un tableau de bord.

### Libellés reconnus

Le type de marché et le mode de passation sont convertis en codes. Sont reconnus, sans tenir compte des
accents ni des majuscules : le code, le libellé complet, et les variantes courantes (« Gré à gré », « ED » →
entente directe ; « AO ouvert » → appel d'offres ouvert ; « Fourniture », « PI »…). Une valeur inconnue
**rejette la ligne** (comptée dans le compte rendu du chargement) au lieu d'être devinée.

## 2. Contrôles de cohérence

Le rapprochement se fait sur le **numéro de réservation** (F3 ↔ F4) et le **numéro d'immatriculation**
(F4 ↔ F5).

| Contrôle | Flux | Gravité |
|---|---|---|
| Marchés immatriculés sans réservation de crédit | F3 ↔ F4 | sérieux (alerte) |
| Marchés dont le montant TTC dépasse le crédit réservé | F3 ↔ F4 | vigilance |
| Paiements cumulés au-delà du montant du marché (avenants compris) | F4 ↔ F5 | sérieux (alerte) |
| Paiements sans marché immatriculé | F4 ↔ F5 | sérieux (alerte) |
| Réservations visées non utilisées depuis plus de 90 jours | F3 ↔ F4 | vigilance |

L'alerte « Anomalies de rapprochement des marchés » est levée dès qu'un contrôle « sérieux » n'est pas nul.
L'alerte « Entente directe » est levée quand la part de l'entente directe, en montant, dépasse le seuil
(paramètre `entente_directe_part_max`, 10 % par défaut).

## 3. Indicateurs de la page « Marchés publics »

| Indicateur | Définition |
|---|---|
| Marchés immatriculés | Σ montant TTC des marchés (F4) ; nombre ; montant HT. |
| Part de l'entente directe | Montant TTC en entente directe / montant TTC total. |
| De la réservation à l'immatriculation | Moyenne, en jours, de la date d'immatriculation (F4) moins la date de visa de la réservation (F3). |
| Jusqu'au premier paiement | Moyenne, en jours, du premier paiement (F5) moins la date d'immatriculation (F4). |
| Exécution financière | Σ paiements (F5) / Σ montant TTC des marchés. |
| Du crédit réservé au paiement | Montants cumulés de F3, F4 et F5 sur l'exercice. |
| Titulaires | Regroupés par NIF (une même entreprise peut apparaître sous plusieurs raisons sociales). |
| Engagements en procédure « marché public » | Chaîne Dépense (réel), procédures dont le libellé contient « MP ». |

## 4. Raccordement

Deux voies, au choix, sans modification de code.

### a) Classeur Excel (en attendant l'API)

Un classeur à **trois onglets** : « F3 Réservations », « F4 Marchés », « F5 Paiements », avec en première ligne
les intitulés de la description des flux (ex. « Numéro d'immatriculation du marché », « Montant du marché
TTC »). Nom de fichier conseillé : `Telemo en date du JJ-MM-AAAA.xlsx` (la date de situation et l'exercice
en sont déduits). Importer depuis **Administration › Sources et connecteurs › Telemo**, sans préciser de table
cible : les trois onglets sont chargés ensemble.

Les correspondances colonne → champ sont préremplies (**Administration › Mappings de colonnes**, source
Telemo) et modifiables si les intitulés réels diffèrent.

### b) API (mode d'échange « API » de la description des flux)

1. Renseigner dans l'environnement du serveur `TELEMO_API_URL` (adresse de base) et `TELEMO_API_TOKEN`
   (jeton, transmis en `Authorization: Bearer …`). Le jeton n'est jamais stocké en base.
2. **Sources et connecteurs › Telemo** : connecteur « API », puis « Tester la connexion ».
3. Points d'accès configurés par défaut (modifiables dans la configuration de la source) :
   `/reservations-credit` → F3, `/marches-immatricules` → F4, `/paiements` → F5, chacun appelé avec
   `?exercice=AAAA`.

Réponses acceptées : liste d'objets JSON, ou objet `{"results" | "data" | "items": […], "next": "url"}`
(pagination suivie automatiquement). Les clés des objets suivent les intitulés de la description des flux.

## 5. Points à confirmer

- Mode d'échange réel de l'API Telemo : adresse, authentification, format et pagination.
- Structure propriétaire de Telemo (pour la fiche de la source).
- Seuil réglementaire de l'entente directe (10 % par défaut, à aligner sur le code des marchés publics).
- Source de référence pour F3 et F5 : Telemo (qui les reçoit) ou directement la Chaîne de dépenses (qui les
  émet).
- Ajout éventuel, depuis F1, du programme / action / activité, de la localisation et de la distinction AE / CP
  dans les analyses des marchés.
