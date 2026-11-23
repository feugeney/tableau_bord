# Armoiries

`armoiries.svg` est **provisoire** : version publiée sur Wikimedia Commons
(« Coat of arms of Guinea.svg », auteur Turn685 d'après Ttzavaras, licence CC BY-SA 3.0).
Cette licence impose de citer l'auteur. Depuis le 23/11/2026, la mention n'est plus visible en pied de page :
elle figure dans l'infobulle des armoiries (`CREDIT_ARMOIRIES` dans `src/components/cadre/Signature.tsx`), dans les
propriétés des PDF (`CREDIT_ARMOIRIES` dans `backend/apps/core/export_pdf.py`) et dans l'infobulle de l'image des
courriels (`backend/apps/core/templates/mails/notification.html`).

Pour passer au fichier officiel fourni par le ministère :

1. remplacer `armoiries.svg` (de préférence) ou déposer `armoiries.png` (au moins 128 × 128 px,
   fond transparent) après avoir supprimé le SVG ;
2. vider `CREDIT_ARMOIRIES` dans `Signature.tsx` et dans `export_pdf.py`, et retirer l'attribut `title` de l'image
   du gabarit de courriel.

L'en-tête, l'écran de connexion et l'impression utilisent le fichier automatiquement. Sans fichier,
un emplacement neutre est affiché. Aucune armoirie n'est dessinée dans le code.

## Logos de l’écran de connexion

- `sceau-mef.png` : sceau du Ministère de l’Économie et des Finances, découpé en cercle sur fond transparent, entre le nom du ministère et le titre.
