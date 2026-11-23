"""Configuration publique de la messagerie, test explicite et suivi réservé aux administrateurs."""

import base64

from django.conf import settings
from django_celery_beat.models import PeriodicTask
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from etl.planificateur import planificateur_actif

from .admin_api import PERMISSIONS_ADMIN, _audit
from .mails_institutionnels import ARMOIRIES, MODELES, catalogue_modeles, exemple_mail
from .models import NotificationMail
from .notifications import envoyer_mail


class TestMailThrottle(UserRateThrottle):
    scope = "test_mail"
    rate = "5/min"


class ModeleMailSerializer(serializers.Serializer):
    modele = serializers.ChoiceField(choices=["test", *MODELES], default="test")
    categorie = serializers.ChoiceField(choices=["alerte", "relance"], default="alerte")


class TestMailSerializer(ModeleMailSerializer):
    destinataire = serializers.EmailField(max_length=254)


class NotificationMailSerializer(serializers.ModelSerializer):
    utilisateur = serializers.CharField(source="utilisateur.username", default=None, read_only=True)
    regle = serializers.CharField(source="regle.code", default=None, read_only=True)

    class Meta:
        model = NotificationMail
        fields = [
            "id",
            "date",
            "termine_le",
            "type",
            "statut",
            "sujet",
            "reference",
            "modele",
            "destinataires",
            "regle",
            "alertes_ids",
            "utilisateur",
            "erreur",
        ]


class NotificationMailViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = PERMISSIONS_ADMIN
    serializer_class = NotificationMailSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        qs = NotificationMail.objects.select_related("regle", "utilisateur").all()
        for champ in ("statut", "type"):
            if valeur := self.request.query_params.get(champ):
                qs = qs.filter(**{champ: valeur})
        return qs

    @action(detail=False, methods=["get"])
    def configuration(self, request):
        tache = PeriodicTask.objects.filter(name="notification-alertes").first()
        smtp = settings.EMAIL_BACKEND == "django.core.mail.backends.smtp.EmailBackend"
        return Response(
            {
                "smtp": smtp,
                "hote": settings.EMAIL_HOST,
                "port": settings.EMAIL_PORT,
                "tls": settings.EMAIL_USE_TLS,
                "ssl": settings.EMAIL_USE_SSL,
                "expediteur": settings.DEFAULT_FROM_EMAIL,
                "authentification_configuree": bool(settings.EMAIL_HOST_USER and settings.EMAIL_HOST_PASSWORD),
                "url_application": settings.TDB_URL_PUBLIQUE,
                "planificateur_actif": planificateur_actif(),
                "verification_active": bool(tache and tache.enabled),
                "derniere_verification": tache.last_run_at if tache else None,
                "compteurs": {
                    s: NotificationMail.objects.filter(statut=s).count() for s in NotificationMail.Statut.values
                },
            }
        )

    @action(detail=False, methods=["get"])
    def modeles(self, request):
        return Response(catalogue_modeles())

    @action(detail=False, methods=["get"])
    def apercu(self, request):
        saisie = ModeleMailSerializer(data=request.query_params)
        saisie.is_valid(raise_exception=True)
        mail = exemple_mail(**saisie.validated_data)
        html = mail.html
        if ARMOIRIES.exists():
            image = base64.b64encode(ARMOIRIES.read_bytes()).decode("ascii")
            html = html.replace("cid:armoiries-mefb", f"data:image/png;base64,{image}")
        return Response({"sujet": mail.sujet, "texte": mail.texte, "html": html})

    @action(detail=False, methods=["post"], throttle_classes=[TestMailThrottle])
    def tester(self, request):
        saisie = TestMailSerializer(data=request.data)
        saisie.is_valid(raise_exception=True)
        courriel = exemple_mail(saisie.validated_data["modele"], saisie.validated_data["categorie"])
        trace = envoyer_mail(
            courriel.sujet,
            courriel.texte,
            [saisie.validated_data["destinataire"]],
            html=courriel.html,
            reference=courriel.reference,
            modele=saisie.validated_data["modele"],
            utilisateur=request.user,
        )
        _audit(request, "test de notification mail", {"notification_id": trace.pk, "statut": trace.statut})
        return Response(self.get_serializer(trace).data)
