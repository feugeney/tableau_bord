from django.core.management.base import BaseCommand

from apps.referentiels.models import RefBailleur, RefSourceFinancement, RefTypeBudget
from etl import nettoyage as n
from etl.connecteurs.oracle import connexion_lecture_seule

# Référentiels de la Chaîne Dépense (lecture seule) : code → libellé.
REQUETES = {
    RefSourceFinancement: "SELECT CODE_SOURCE_FIN, LIBELLE_SOURCE_FIN FROM GDEP.TC_SOURCE_FIN",
    # Un code bailleur peut figurer sous plusieurs sources ou groupes ; on retient le premier libellé.
    RefBailleur: "SELECT CODE_BAILLEUR, MIN(LIBELLE_BAILLEUR) FROM GDEP.TC_BAILLEUR GROUP BY CODE_BAILLEUR",
    RefTypeBudget: "SELECT CODE_TYPE_BUDGET, LIBELLE FROM GDEP.TC_TYPE_BUDGET",
}


class Command(BaseCommand):
    help = (
        "Complète les libellés vides des sources de financement, bailleurs et types de budget "
        "depuis la Chaîne Dépense (Oracle, lecture seule). Les libellés déjà renseignés sont conservés."
    )

    def handle(self, **options):
        with connexion_lecture_seule() as cnx:
            for modele, sql in REQUETES.items():
                with cnx.cursor() as cur:
                    cur.execute(sql)
                    lignes = cur.fetchall()
                crees = completes = 0
                for code, libelle in lignes:
                    code, libelle = n.code(code), n.titre_francais(libelle)
                    if not code:
                        continue
                    objet, cree = modele.objects.get_or_create(code=code, defaults={"libelle": libelle})
                    crees += cree
                    if not cree and not objet.libelle and libelle:
                        objet.libelle = libelle
                        objet.save(update_fields=["libelle"])
                        completes += 1
                self.stdout.write(f"{modele.__name__} : {crees} créés, {completes} libellés complétés.")
