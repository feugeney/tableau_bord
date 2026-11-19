# Rapport d'étape n° 1

Système intégré de pilotage des finances publiques — Ministère de l'Économie, des Finances et du Budget.
Livrable n° 3 des termes de référence (rapports d'étape périodiques). Arrêté au 10 octobre 2026.

## 1. Synthèse

La plateforme existe et fonctionne sur le poste de développement : entrepôt, connecteurs, tableau de bord de
dix pages, alertes, administration, exploration. Elle est conforme à la plupart des exigences techniques des
termes de référence. **Elle n'est pas encore un entrepôt « couvrant l'ensemble des applications critiques » :
une seule application y verse des données réelles**, et elle n'a jamais été installée sur un serveur.

Les deux actions qui font le plus avancer le projet ne dépendent pas du prestataire :

1. obtenir un accès ou une extraction pour chaque application source ;
2. mettre à disposition un serveur de recette.

## 2. Avancement par chantier

| N° | Chantier | État | Commentaire |
|---|---|---|---|
| — | Socle : entrepôt, connecteurs, règles de gestion, tableau de bord, alertes, administration | Fait | Antérieur aux termes de référence |
| 1 | Modèle de données et traçabilité | Fait | Dimension temps, zones géographiques, UUID des flux, zone brute |
| 2 | Échanges et collecte automatisée | Fait, à démarrer sur serveur | SFTP, RabbitMQ, schémas JSON, XML, TLS 1.3 |
| 3 | Profil analyste, exploration, accès BI | Fait | |
| 8 | Livrables | Fait (première version) | Six documents dans `docs/livrables/` |
| 4 | Raccordement des sources réelles | **Bloqué** | En attente des accès et des extractions |
| 5 | Analyses prédictives | Fait | Projections de fin d'exercice : dépenses (réel), recettes (illustration) |
| 6 | Données ouvertes | **En attente d'une décision** | Quelles données sont publiables |
| 7 | Second site, sauvegarde, reprise | **En attente d'une décision** | Choix de l'hébergeur |

## 3. État des sources

| Source | État | Ce qui manque |
|---|---|---|
| Chaîne Dépense | Données réelles (extraction du 16 août 2026) | Tolérance de concordance à arbitrer ; compte Oracle en lecture seule pour l'alimentation automatique |
| SAFIG, SYDONIA, SCIE, dette, FUGAS | Illustration | Une extraction réelle et l'intitulé de ses colonnes |
| SICOM, SYSOP | Illustration | Un compte PostgreSQL en lecture seule et la requête de lecture |
| Telemo | Illustration | L'adresse de l'API, son mode d'authentification, ou un classeur des flux F3, F4, F5 |
| SIGPIP, PLEB | Non raccordées | Périmètre à définir |

## 4. Qualité

| Vérification | Résultat |
|---|---|
| Tests automatiques du serveur | 253, tous réussis |
| Tests automatiques de l'interface | 17, tous réussis |
| Navigation au clavier | 12 vérifications réussies |
| Couverture de code | 99 % sur les règles de gestion, 93 % sur les connecteurs |
| Vérification à l'écran | Pages, administration et exploration contrôlées sur l'application en marche |
| Installation sur serveur | **Non faite** |

### Premier résultat des projections

Sur l'extraction du 16 août 2026, 13 % des crédits sont engagés. Au rythme constaté, **26 à 29 % le seraient
au 31 décembre**. Cette fourchette est à prendre avec prudence : l'exécution n'a commencé qu'en avril, et la
méthode, appliquée fin juin, aurait sous-estimé de 9 % le montant constaté mi-août.

## 5. Risques

| Risque | Gravité | Parade |
|---|---|---|
| Les directions ne fournissent pas d'accès à leurs applications | Critique : sans cela, pas d'entrepôt | Lettre de mission du cabinet aux directions ; un référent par application |
| Écart de concordance dans l'extraction de la Chaîne Dépense | Sérieux : met en doute les totaux | Séance de rapprochement avec la DGB sur l'extraction du 16 août |
| Première installation sur serveur non encore faite | Sérieux | Serveur de recette au plus tôt ; dérouler le dossier de recette, parties A, B et F |
| Périmètre des termes de référence non défini (section 5) | Sérieux : dérive du calendrier | Liste nominative des applications validée par le SMSI |
| Poste de développement unique, sans dépôt de code partagé | Sérieux : perte possible du travail | Dépôt de code du ministère, sauvegardé |
| Libellés officiels non confirmés (régulation, types de budget, ministères) | Vigilance | Validation par la DGB |

## 6. Décisions attendues du ministère

1. Liste des applications du périmètre et référent de chacune.
2. Tolérance du contrôle de concordance de la Chaîne Dépense.
3. Serveur de recette et, à terme, hébergeur du second site.
4. Données publiables en données ouvertes.
5. Fichier officiel des armoiries.
6. Maintien ou non de la double authentification pour les analystes.

## 7. Prochaine étape proposée

- Installation sur le serveur de recette et première séance de recette (parties A, B, F du dossier).
- Raccordement de la deuxième source réelle, dès réception d'un accès.
