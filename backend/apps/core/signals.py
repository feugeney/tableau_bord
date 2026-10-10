from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.db.models.signals import post_save
from django.dispatch import receiver

from .audit import journaliser
from .models import JournalAudit, Source


@receiver(user_logged_in)
def audit_connexion(sender, request, user, **kwargs):
    journaliser(request, JournalAudit.Action.CONNEXION, utilisateur=user)


@receiver(user_login_failed)
def audit_echec_connexion(sender, credentials, request=None, **kwargs):
    journaliser(
        request,
        JournalAudit.Action.ECHEC_CONNEXION,
        identifiant=(credentials or {}).get("username", ""),
    )


@receiver(post_save, sender=Source)
def planifier_source(sender, instance, **kwargs):
    from etl.planification import synchroniser_planification

    synchroniser_planification(instance)
