# Clés publiques des partenaires (dépôt SFTP)

Déposer ici une clé publique par partenaire (`nom-du-partenaire.pub`, format OpenSSH). Aucun mot de passe
n'est accepté. Après ajout ou retrait d'une clé : `docker compose restart sftp`.

Le partenaire se connecte au compte `depot` et dépose ses fichiers dans `sources/<code de la source>/`
(par exemple `sources/telemo/`). Formats : `.xlsx`, `.csv`, `.xml`, `.json`.

Sur le serveur, rendre le script des clés d'hôte exécutable une fois : `chmod +x sftp/cles-hote.sh`.
