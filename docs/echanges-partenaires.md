# Échanges avec les applications sources et les partenaires

Ce document décrit les quatre façons d'échanger des données avec l'entrepôt, et le contrat technique à
remettre à un partenaire. Protocoles retenus par les termes de référence (section 6.4) : HTTPS (TLS 1.3),
API REST, AMQP 0.9.1, SFTP ; formats JSON, CSV et XML.

## 1. Vue d'ensemble

| Besoin | Moyen | Sens |
|---|---|---|
| L'entrepôt lit une application | Connecteur direct (Oracle, PostgreSQL) ou API REST du partenaire | source → entrepôt |
| Un partenaire envoie un fichier | Dépôt SFTP, ou import manuel par l'administrateur | source → entrepôt |
| Un partenaire lit l'entrepôt | API REST en lecture seule, avec un jeton de partage | entrepôt → partenaire |
| Un partenaire veut être prévenu d'un chargement | Événement AMQP (RabbitMQ) | entrepôt → partenaire |

Tout ce qui est reçu est conservé tel quel en zone brute, avec son empreinte SHA-256, et rattaché à un
chargement identifié par un UUID.

## 2. Dépôt de fichiers par SFTP

- Serveur : port 2222 (variable `SFTP_PORT`), compte `depot`, **authentification par clé uniquement**. La clé
  publique du partenaire est déposée dans `sftp/cles/` par l'administrateur.
- Le partenaire dépose son fichier dans `sources/<code de la source>/`, par exemple `sources/telemo/`.
- Formats : `.xlsx`, `.csv`, `.xml`, `.json`. Taille maximale : `IMPORT_TAILLE_MAX` (100 Mo par défaut).
- Nom conseillé : `<Application> en date du JJ-MM-AAAA.<extension>` ; la date de situation et l'exercice en
  sont déduits.
- La relève a lieu toutes les 5 minutes (`DEPOT_RELEVE_MINUTES`). Un fichier n'est pris que s'il n'a pas
  changé depuis 60 secondes (`DEPOT_STABILITE_SECONDES`), pour ne pas lire un transfert en cours. Les fichiers
  dont le nom commence par un point sont ignorés.
- Après chargement, le fichier est retiré du dépôt. Le résultat se lit dans **Administration › Imports et
  chargements** (colonne « Par » : « Dépôt SFTP »), y compris en cas d'échec.
- Relève immédiate : **Administration › Entrepôt et illustration › Relever maintenant**, ou
  `python manage.py relever_depots`.

## 3. Schémas JSON des flux

Chaque flux a un schéma JSON (brouillon 2020-12) déduit du mapping de colonnes : clés attendues, types, champs
obligatoires, valeurs admises des listes fermées. C'est le contrat à remettre au partenaire.

- Téléchargement : **Administration › Sources et connecteurs › (source) › Schémas JSON des flux**, ou
  `GET /api/v1/admin/sources/<code>/schemas/`.
- Application : pour une API ou un fichier JSON, une ligne qui ne respecte pas le schéma (clé obligatoire
  absente, type inattendu) est **écartée et comptée** dans le contrôle « Lignes conformes au schéma JSON ».
  Les clés supplémentaires sont acceptées et ignorées.
- Un fichier JSON peut contenir une table (liste d'objets) ou plusieurs (objet dont chaque clé est le nom de
  la table, celui de l'onglet du mapping, ou le chemin du flux d'API).
- Un fichier XML contient une table : un élément par ligne sous la racine, un sous-élément par colonne.

## 4. Événements AMQP (RabbitMQ)

À la fin de chaque chargement, réussi ou en échec, un message est publié. Un aperçu n'est pas annoncé.

- Échange : `tdb.evenements`, type `topic`, durable ; messages persistants, format JSON.
- Clé de routage : `chargement.<source>.<statut>`, par exemple `chargement.telemo.succes`. Un partenaire lie
  sa file à `chargement.telemo.*` ou à `chargement.#`.
- Corps du message :

```json
{
  "uuid": "46b3a826-9d80-4f09-a445-7ea1c6daa738",
  "source": "chaine_depense",
  "statut": "succes",
  "exercice": 2026,
  "date_situation": "2026-08-16",
  "lignes_chargees": 2470,
  "lignes_rejetees": 0,
  "empreinte_sha256": "5eb8a77a…",
  "fin": "2026-10-09T16:53:41+00:00"
}
```

Le message ne contient aucune donnée métier : le partenaire vient ensuite lire l'API avec son jeton.
Sans messagerie configurée (`EVENEMENTS_AMQP_URL` vide), rien n'est publié ; une panne de la messagerie ne
fait jamais échouer un chargement.

## 5. Sécurité

- HTTPS en TLS 1.3 uniquement (`nginx/nginx.conf`).
- SFTP : clés publiques, pas de mot de passe ; clés d'hôte conservées d'un redémarrage à l'autre.
- Comptes en lecture seule sur les applications sources ; aucun secret en base.
- RabbitMQ : identifiants dans `.env` (`RABBITMQ_USER`, `RABBITMQ_PASSWORD`) ; ne pas exposer le port hors du
  réseau du ministère.

## 6. Ce qui reste à valider sur le serveur

Les services RabbitMQ et SFTP sont décrits dans `docker-compose.yml` mais n'ont pas pu être démarrés sur le
poste de développement (pas de Docker). La logique est couverte par les tests automatiques (relève du dépôt,
publication des événements sur une messagerie en mémoire) ; le premier démarrage réel est à faire sur le
serveur de recette.
