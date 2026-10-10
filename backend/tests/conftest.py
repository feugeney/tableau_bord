import pytest
from django.core.cache import cache

from .classeur import ecrire_classeur


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    from apps.core.initialisation import initialiser_tout

    with django_db_blocker.unblock():
        initialiser_tout()


@pytest.fixture(autouse=True)
def _cache_vide():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def classeur(tmp_path):
    return ecrire_classeur(tmp_path)


@pytest.fixture
def charge(db, classeur):
    """Extraction synthétique chargée ; renvoie le chargement."""
    from etl.connecteurs.chaine_depense import ExcelChaineDepenseConnector

    ch = ExcelChaineDepenseConnector(classeur).executer()
    assert ch.statut == "succes", ch.message_erreur
    return ch


@pytest.fixture
def filtres(charge):
    from apps.core.filtres import resoudre_filtres

    return resoudre_filtres({}, "chaine_depense")
