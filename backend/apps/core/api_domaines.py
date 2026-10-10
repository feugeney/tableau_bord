"""API des pages de domaine : /recettes-fiscales/, /douanes/, /tresor/, /dette/, /paie/, /patrimoine/, /portefeuille/.

Chaque réponse porte `meta.statut_source` (reel | demo | non_raccorde) ; une page mixte donne en plus
la source de chacun de ses blocs.
"""

from importlib import import_module

from .domaines import filtres_source
from .models import Domaine
from .reponses import VueDomaine, en_cache, meta


class VuePageDomaine(VueDomaine):
    module = ""

    def calculer(self, request, f):
        return import_module(self.module).page(f)


class VuePaie(VueDomaine):
    """Masse salariale : le volet Chaîne Dépense (réel) s'affiche même si FUGAS n'est pas raccordé."""

    domaine = Domaine.PAIE
    source_code = "fugas"
    page = "masse-salariale"

    @en_cache
    def _get(self, request, **kwargs):
        from apps.paie.services import page

        f = self.filtres(request)
        if f.date_situation is None:
            f = None
        fc = filtres_source("chaine_depense")
        if f is None and fc is None:
            return {"meta": meta("fugas"), "data": None}
        return {"meta": meta("fugas", f), "data": page(f, exercice=f.exercice if f else fc.exercice)}


PAGES_DOMAINES = {
    # préfixe d'URL : (domaine, source, module de services, page journalisée)
    "recettes-fiscales": (Domaine.RECETTES_FISCALES, "safig", "apps.recettes_fiscales.services", "recettes-fiscales"),
    "douanes": (Domaine.DOUANES, "sydonia", "apps.douanes.services", "recettes-douanieres"),
    "tresor": (Domaine.TRESOR, "scie", "apps.tresor.services", "tresorerie"),
    "dette": (Domaine.DETTE, "dette", "apps.dette.services", "dette-publique"),
    "patrimoine": (Domaine.PATRIMOINE, "sicom", "apps.patrimoine.services", "patrimoine"),
    "portefeuille": (Domaine.PORTEFEUILLE, "sysop", "apps.portefeuille.services", "portefeuille"),
    "marches-publics": (Domaine.MARCHES_PUBLICS, "telemo", "apps.marches_publics.services", "marches-publics"),
}


def vue_page(prefixe: str):
    if prefixe == "paie":
        return VuePaie.as_view()
    domaine, source, module, page = PAGES_DOMAINES[prefixe]
    return type(
        f"Page_{source}",
        (VuePageDomaine,),
        {"domaine": domaine, "source_code": source, "module": module, "page": page},
    ).as_view()
