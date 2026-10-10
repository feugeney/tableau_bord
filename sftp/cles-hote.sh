#!/bin/sh
# Clés d'hôte conservées d'un redémarrage à l'autre : l'empreinte du serveur ne change pas pour les partenaires.
set -e
dossier=/etc/ssh/cles-hote
for type in ed25519 rsa; do
  cle="$dossier/ssh_host_${type}_key"
  [ -f "$cle" ] || ssh-keygen -q -t "$type" -N "" -f "$cle"
  cp "$cle" "$cle.pub" /etc/ssh/
  chmod 600 "/etc/ssh/ssh_host_${type}_key"
done
