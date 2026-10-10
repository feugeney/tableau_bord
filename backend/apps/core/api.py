"""API du socle : authentification, sources et imports, alertes, qualité, paramètres."""

from __future__ import annotations

import uuid
from datetime import date
from pathlib import Path

from django.conf import settings
from django.contrib.auth import authenticate
from django.db.models import Max, Q
from django_otp.plugins.otp_totp.models import TOTPDevice
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from . import regles
from .audit import journaliser
from .exploration import peut_explorer
from .models import (
    SEVERITE_ORDRE,
    Alerte,
    Chargement,
    Domaine,
    JournalAudit,
    Parametre,
    Source,
    StatutChargement,
)
from .permissions import PERMISSIONS_DONNEES, AdminDNSI, DoubleAuthentification, LectureOuAdminDNSI
from .reponses import jsonable

# ------------------------------------------------------------------ authentification


def profil(u) -> dict:
    return {
        "id": u.id,
        "identifiant": u.get_username(),
        "nom": u.get_full_name() or u.get_username(),
        "role": u.role,
        "role_libelle": u.get_role_display(),
        "structure": u.structure,
        "domaines": [d for d in Domaine.values if u.peut_voir(d)],
        "peut_exporter": u.peut_exporter("synthese") or any(u.peut_exporter(d) for d in u.domaines or []),
        "est_admin": u.is_superuser or u.role == "dnsi_admin",
        "peut_explorer": peut_explorer(u),
        "exige_2fa": u.exige_2fa,
        "a_2fa": TOTPDevice.objects.filter(user=u, confirmed=True).exists(),
    }


def jetons(u, otp: bool) -> dict:
    refresh = RefreshToken.for_user(u)
    refresh["otp"] = otp
    refresh["role"] = u.role
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


class ConnexionSerializer(serializers.Serializer):
    identifiant = serializers.CharField()
    mot_de_passe = serializers.CharField(trim_whitespace=False)
    code_otp = serializers.CharField(required=False, allow_blank=True)


class ConnexionView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = "login"

    @extend_schema(request=ConnexionSerializer, responses={200: OpenApiTypes.OBJECT})
    def post(self, request):
        s = ConnexionSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        u = authenticate(request, username=s.validated_data["identifiant"], password=s.validated_data["mot_de_passe"])
        if u is None or not u.is_active:
            return Response(
                {"code": "identifiants", "detail": "Identifiant ou mot de passe incorrect."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        otp = False
        devices = TOTPDevice.objects.filter(user=u, confirmed=True)
        if devices.exists():
            code = s.validated_data.get("code_otp") or ""
            if not code:
                return Response(
                    {"code": "otp_requis", "detail": "Saisissez le code de votre application."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            if not any(d.verify_token(code) for d in devices):
                journaliser(request, JournalAudit.Action.ECHEC_CONNEXION, utilisateur=u, objet="code OTP invalide")
                return Response(
                    {"code": "otp_invalide", "detail": "Code de vérification invalide."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            otp = True
        journaliser(request, JournalAudit.Action.CONNEXION, utilisateur=u)
        return Response({**jetons(u, otp), "utilisateur": profil(u)})


class MoiView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        return Response(profil(request.user))


class Activer2FAView(APIView):
    """Enrôlement TOTP : renvoie l'URL otpauth:// à scanner (QR code côté interface)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={200: OpenApiTypes.OBJECT})
    def post(self, request):
        TOTPDevice.objects.filter(user=request.user, confirmed=False).delete()
        d = TOTPDevice.objects.create(user=request.user, name="Tableau de bord", confirmed=False)
        return Response({"otpauth_url": d.config_url})


class Confirmer2FAView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request={"application/json": OpenApiTypes.OBJECT}, responses={200: OpenApiTypes.OBJECT})
    def post(self, request):
        code = str(request.data.get("code_otp", ""))
        d = TOTPDevice.objects.filter(user=request.user, confirmed=False).first()
        if d is None or not d.verify_token(code):
            raise ValidationError({"code_otp": "Code invalide."})
        d.confirmed = True
        d.save()
        return Response({**jetons(request.user, True), "utilisateur": profil(request.user)})


# ------------------------------------------------------------------ sources


class SourceSerializer(serializers.ModelSerializer):
    domaine_libelle = serializers.CharField(source="get_domaine_display")
    dernier_chargement = serializers.SerializerMethodField()
    derniere_date_situation = serializers.SerializerMethodField()

    class Meta:
        model = Source
        fields = [
            "code",
            "domaine",
            "domaine_libelle",
            "application",
            "structure",
            "statut",
            "connecteur",
            "en_production_depuis",
            "remarque",
            "dernier_chargement",
            "derniere_date_situation",
        ]

    def get_dernier_chargement(self, s):
        ch = s.chargements.exclude(statut=StatutChargement.APERCU).order_by("-debut").first()
        if ch is None:
            return None
        return {
            "id": ch.id,
            "date": ch.debut,
            "statut": ch.statut,
            "fichier": ch.fichier,
            "lignes_chargees": ch.lignes_chargees,
            "message_erreur": ch.message_erreur[:500],
        }

    def get_derniere_date_situation(self, s):
        return s.chargements.filter(statut=StatutChargement.SUCCES).aggregate(d=Max("date_situation"))["d"]


class ChargementSerializer(serializers.ModelSerializer):
    source = serializers.CharField(source="source.code")
    utilisateur = serializers.CharField(source="utilisateur.username", default=None)

    class Meta:
        model = Chargement
        fields = [
            "id",
            "uuid",
            "source",
            "fichier",
            "empreinte_sha256",
            "exercice",
            "date_situation",
            "lignes_lues",
            "lignes_rejetees",
            "lignes_chargees",
            "debut",
            "fin",
            "duree_secondes",
            "statut",
            "message_erreur",
            "utilisateur",
            "detail",
        ]


class ImportSerializer(serializers.Serializer):
    fichier = serializers.FileField()
    date_situation = serializers.DateField(required=False)
    exercice = serializers.IntegerField(required=False, min_value=2000, max_value=2100)
    apercu = serializers.BooleanField(default=False)
    table_cible = serializers.CharField(required=False)
    onglet = serializers.CharField(required=False)

    def validate_fichier(self, f):
        if not f.name.lower().endswith((".xlsx", ".csv", ".xml", ".json")):
            raise ValidationError("Formats acceptés : .xlsx, .csv, .xml, .json")
        if f.size > settings.IMPORT_TAILLE_MAX:
            raise ValidationError("Fichier trop volumineux.")
        return f


class SourceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Source.objects.all()
    serializer_class = SourceSerializer
    lookup_field = "code"
    pagination_class = None
    permission_classes = [DoubleAuthentification]

    @action(detail=True, methods=["get"])
    def chargements(self, request, code=None):
        qs = Chargement.objects.filter(source__code=code).select_related("source", "utilisateur")[:50]
        return Response(ChargementSerializer(qs, many=True).data)

    @extend_schema(request={"multipart/form-data": ImportSerializer})
    @action(detail=True, methods=["post"], permission_classes=[DoubleAuthentification, AdminDNSI], url_path="import")
    def importer(self, request, code=None):
        from etl.connecteurs import fabrique
        from etl.connecteurs.base import ErreurChargement

        source = self.get_object()
        s = ImportSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        v = s.validated_data
        f = v["fichier"]
        # Dépôt provisoire : le connecteur range ensuite le fichier en zone brute, sous son empreinte.
        dossier = Path(settings.MEDIA_ROOT) / "depot" / source.code
        dossier.mkdir(parents=True, exist_ok=True)
        chemin = dossier / f"{date.today():%Y%m%d}-{uuid.uuid4().hex[:8]}{Path(f.name).suffix.lower()}"
        with open(chemin, "wb") as sortie:
            for bloc in f.chunks():
                sortie.write(bloc)
        try:
            connecteur = fabrique.connecteur_pour(
                source,
                fichier=chemin,
                nom_fichier=f.name,
                exercice=v.get("exercice"),
                date_situation=v.get("date_situation"),
                utilisateur_id=request.user.id,
                table_cible=v.get("table_cible"),
                onglet=v.get("onglet"),
            )
        except ErreurChargement as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        try:
            ch = connecteur.executer(apercu=v["apercu"])
        finally:
            try:
                chemin.unlink(missing_ok=True)
            except OSError:  # fichier encore ouvert (Windows) : le dépôt provisoire est purgé plus tard
                pass
        journaliser(
            request,
            JournalAudit.Action.IMPORT,
            objet=f"{source.code} : {f.name}",
            detail={
                "chargement": ch.id,
                "uuid": str(ch.uuid),
                "empreinte_sha256": ch.empreinte_sha256,
                "statut": ch.statut,
                "apercu": v["apercu"],
            },
        )
        code_http = status.HTTP_201_CREATED if ch.statut != StatutChargement.ECHEC else status.HTTP_400_BAD_REQUEST
        return Response(ChargementSerializer(ch).data, status=code_http)


# ------------------------------------------------------------------ alertes


class AlerteSerializer(serializers.ModelSerializer):
    source = serializers.CharField(source="source.application", default=None)
    source_code = serializers.CharField(source="source.code", default=None)

    class Meta:
        model = Alerte
        fields = [
            "id",
            "date",
            "domaine",
            "source",
            "source_code",
            "date_situation",
            "severite",
            "titre",
            "message",
            "valeur",
            "action_recommandee",
            "lien",
            "statut",
        ]
        read_only_fields = [f for f in fields if f != "statut"]


class AlerteViewSet(mixins.ListModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    serializer_class = AlerteSerializer
    permission_classes = [DoubleAuthentification]
    pagination_class = None
    http_method_names = ["get", "patch"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Alerte.objects.none()
        qs = Alerte.objects.select_related("source")
        u = self.request.user
        if not u.voit_tout():
            qs = qs.filter(domaine__in=[d for d in Domaine.values if d != "synthese" and u.peut_voir(d)])
        p = self.request.query_params
        for champ in ("domaine", "severite", "statut"):
            if p.get(champ):
                qs = qs.filter(**{f"{champ}__in": p[champ].split(",")})
        return qs

    def list(self, request, *args, **kwargs):
        alertes = sorted(self.get_queryset()[:500], key=lambda a: (SEVERITE_ORDRE.get(a.severite, 9), -a.id))
        return Response(self.get_serializer(alertes, many=True).data)

    def perform_update(self, serializer):
        from etl.mart import invalider_cache_api

        a = serializer.save(statut_modifie_par=self.request.user)
        invalider_cache_api()  # la synthèse affiche le statut des alertes
        journaliser(self.request, JournalAudit.Action.ALERTE, objet=f"alerte {a.id}", detail={"statut": a.statut})


# ------------------------------------------------------------------ qualité


class QualiteView(APIView):
    permission_classes = PERMISSIONS_DONNEES
    domaine = Domaine.DEPENSE

    @extend_schema(parameters=[OpenApiParameter("source", str)], responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        code = request.query_params.get("source", "chaine_depense")
        ch = (
            Chargement.objects.filter(source__code=code)
            .exclude(statut=StatutChargement.APERCU)
            .select_related("source")
            .order_by("-debut")
            .first()
        )
        if ch is None:
            return Response({"meta": {"source": code, "statut_source": "non_raccorde"}, "data": None})
        return Response(
            jsonable(
                {
                    "meta": {"source": code, "date_situation": ch.date_situation, "chargement": ch.id},
                    "data": {
                        "chargement": ChargementSerializer(ch).data,
                        "controles": ch.detail.get("controles", []),
                    },
                }
            )
        )


# ------------------------------------------------------------------ paramètres


class ParametreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parametre
        fields = ["code", "valeur", "libelle", "unite", "modifie_le"]
        read_only_fields = ["code", "libelle", "unite", "modifie_le"]


class ParametreViewSet(mixins.ListModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    queryset = Parametre.objects.all()
    serializer_class = ParametreSerializer
    lookup_field = "code"
    pagination_class = None
    permission_classes = [DoubleAuthentification, LectureOuAdminDNSI]
    http_method_names = ["get", "patch"]

    def perform_update(self, serializer):
        ancien = serializer.instance.valeur
        p = serializer.save(modifie_par=self.request.user)
        regles.invalider_cache_parametres()
        from etl.mart import invalider_cache_api

        invalider_cache_api()
        journaliser(
            self.request, JournalAudit.Action.PARAMETRE, objet=p.code, detail={"avant": ancien, "apres": p.valeur}
        )


class JournalSerializer(serializers.ModelSerializer):
    class Meta:
        model = JournalAudit
        fields = ["date", "identifiant", "action", "objet", "detail", "adresse_ip"]


class JournalViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = JournalAudit.objects.all()
    serializer_class = JournalSerializer
    permission_classes = [DoubleAuthentification, AdminDNSI]

    def get_queryset(self):
        qs = super().get_queryset()
        p = self.request.query_params
        if p.get("action"):
            qs = qs.filter(action=p["action"])
        if p.get("q"):
            qs = qs.filter(Q(identifiant__icontains=p["q"]) | Q(objet__icontains=p["q"]))
        return qs


class SituationsView(APIView):
    """Exercices et dates de situation disponibles (sélecteurs de l'en-tête)."""

    permission_classes = [DoubleAuthentification]

    @extend_schema(parameters=[OpenApiParameter("source", str)], responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        from .filtres import dernieres_situations

        code = request.query_params.get("source", "chaine_depense")
        situations = dernieres_situations(code)
        exercices: dict[int, list[str]] = {}
        for e, d in situations:
            exercices.setdefault(e, []).append(d.isoformat())
        return Response({"source": code, "exercices": [{"exercice": e, "dates": ds} for e, ds in exercices.items()]})
