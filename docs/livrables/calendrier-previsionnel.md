# Calendrier prévisionnel de mise en œuvre

Système intégré de pilotage des finances publiques — Ministère de l'Économie, des Finances et du Budget.
Livrable n° 1 des termes de référence. Version 1.0, 10 octobre 2026.

Ce calendrier est exprimé en mois à partir du lancement officiel (M1), sans date : la date de lancement et la
disponibilité des directions sont à arrêter avec le SMSI.

## 1. Écart avec le calendrier indicatif des termes de référence

Le calendrier indicatif des TdR place la mise en place de l'entrepôt (mois 7-8) après le développement des
flux d'alimentation (mois 4-6). L'ordre proposé ici est différent, pour deux raisons :

- l'entrepôt, les connecteurs et le tableau de bord **existent déjà** ; le travail restant est surtout le
  raccordement des applications ;
- le raccordement dépend des directions, et c'est lui qui fixe la durée du projet. Il démarre donc dès le
  premier mois et se poursuit tout au long du projet.

## 2. Calendrier proposé

| Phase | Mois | Contenu | Dépend de | État |
|---|---|---|---|---|
| 1. Diagnostic et cartographie | M1 – M2 | Liste nominative des applications, référents, modes d'accès, volumes ; validation du rapport d'analyse et de conception | SMSI, directions | Rapport rédigé ; liste à valider |
| 2. Architecture et modèles | M1 – M2 | Modèle de l'entrepôt, dimensions communes, traçabilité | — | **Fait** |
| 3. Installation en recette | M2 | Serveur de recette, certificat, première installation, sauvegarde et restauration | SMSI (serveur) | À faire |
| 4. Raccordement des sources | M2 – M9 | Une application à la fois : accès, mapping, chargement, rapprochement des totaux avec la direction | Directions | Chaîne Dépense faite ; huit à raccorder |
| 5. Tableaux de bord et exploration | M2 – M9 | Chaque page passe de l'illustration au réel au fil des raccordements ; ajustements demandés par les directions | Phase 4 | Pages faites, en illustration |
| 6. Échanges avec les partenaires | M3 – M6 | SFTP, messagerie, jetons de partage, schémas remis aux partenaires | Partenaires | Développé ; à mettre en service |
| 7. Analyses prédictives | M5 – M8 | Projections de fin d'exercice ; affinage avec l'exercice précédent, puis extension aux autres domaines | Historique chargé | Première version faite |
| 8. Second site et reprise | M6 – M9 | Hébergement cloud, réplication, plan de reprise | Décision du ministère | À décider |
| 9. Données ouvertes | M8 – M10 | Jeux publiables, portail | Décision du ministère | À décider |
| 10. Formation et transfert | M9 – M11 | Utilisateurs (par profil), administrateurs, équipe technique du SMSI | SMSI | Manuels rédigés |
| 11. Pilote et généralisation | M10 – M12 | Usage réel par le cabinet et deux directions, puis ouverture à tous ; recette finale | Cabinet | — |

## 3. Ordre de raccordement proposé

L'ordre tient compte de ce qui est déjà prêt et de la valeur pour le pilotage. Il est à ajuster selon la
disponibilité réelle des directions.

| Rang | Application | Raison |
|---|---|---|
| 1 | Chaîne Dépense, lecture directe Oracle | Déjà en données réelles par fichier ; l'alimentation automatique supprime l'import manuel |
| 2 | SICOM, SYSOP | Bases PostgreSQL exploitées par la DNSI : accès le plus simple à obtenir |
| 3 | SAFIG, SYDONIA | Recettes : indispensables à la synthèse |
| 4 | SCIE | Trésorerie |
| 5 | Application de la dette | Encours et échéancier |
| 6 | Telemo | Mode d'échange à confirmer |
| 7 | FUGAS, SIGPIP, PLEB | Périmètre à préciser |

Durée indicative par application, une fois l'accès obtenu : deux à trois semaines, dont la moitié pour le
rapprochement des totaux avec la direction.

## 4. Jalons

| Jalon | Mois | Critère |
|---|---|---|
| J1. Périmètre arrêté | M2 | Liste des applications et des référents signée |
| J2. Recette technique | M3 | Dossier de recette, parties A, B et F conformes sur le serveur de recette |
| J3. Trois sources réelles | M5 | Synthèse alimentée en réel pour les dépenses et les recettes |
| J4. Toutes les sources du périmètre | M9 | Plus aucune page en illustration |
| J5. Recette finale | M12 | Dossier de recette complet, procès-verbal signé |

## 5. Hypothèses

- Un référent désigné par application, disponible pour le rapprochement des chiffres.
- Des comptes en lecture seule ou des extractions fournis dans le mois qui suit la demande.
- Un serveur de recette disponible au mois 2.
- Les décisions sur le second site et les données ouvertes prises avant le mois 6.

Tout retard sur une hypothèse décale d'autant les phases qui en dépendent, sans bloquer les autres
raccordements.
