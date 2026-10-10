# Armoiries

`armoiries.svg` est **provisoire** : version publiée sur Wikimedia Commons
(« Coat of arms of Guinea.svg », auteur Turn685 d'après Ttzavaras, licence CC BY-SA 3.0).
Cette licence impose de citer l'auteur : la mention figure en pied de page (`CREDIT_ARMOIRIES`
dans `src/components/cadre/Signature.tsx`).

Pour passer au fichier officiel fourni par le ministère :

1. remplacer `armoiries.svg` (de préférence) ou déposer `armoiries.png` (au moins 128 × 128 px,
   fond transparent) après avoir supprimé le SVG ;
2. vider `CREDIT_ARMOIRIES` dans `Signature.tsx` (la mention disparaît du pied de page).

L'en-tête, l'écran de connexion et l'impression utilisent le fichier automatiquement. Sans fichier,
un emplacement neutre est affiché. Aucune armoirie n'est dessinée dans le code.
