"""Module d'administration technique de l'entrepôt (rôle dnsi_admin, double authentification).

/api/v1/admin/… : sources et connecteurs, mappings de colonnes, chargements, règles d'alerte,
utilisateurs et accès, partage de données (jetons), état de l'entrepôt, données d'illustration.
Les secrets de connexion ne transitent jamais par l'API : ils restent dans les variables d'environnement.
"""

from __future__ import annotations

import re
from pathlib import Path

from django.apps import apps as django_apps
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.db import connection, models
from django.http import FileResponse
from django.utils.crypto import get_random_string
from django_otp.plugins.otp_totp.models import TOTPDevice
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .audit import journaliser
from .models import (
    Chargement,
    Domaine,
    JetonPartage,
    JournalAudit,
    MappingColonnes,
    RegleAlerte,
    Role,
    Source,
    StatutSource,
    TypeConnecteur,
    Utilisateur,
)
from .permissions import AdminDNSI, DoubleAuthentification

PERMISSIONS_ADMIN = [DoubleAuthentification, AdminDNSI]
CRON = re.compile(r"^(\S+\s+){4}\S+$")
VARIABLES_CONNEXION = {
    "telemo": "TELEMO_API_URL / TELEMO_API_TOKEN",
    "chaine_depense": "CHAINE_DEPENSE_ORACLE_DSN",
    "sicom": "SICOM_DATABASE_URL",
    "sysop": "SYSOP_DATABASE_URL",
}


def _audit(request, objet: str, detail: dict | None = None):
    journaliser(request, JournalAudit.Action.PARAMETRE, objet=objet, detail=detail or {})


def _invalider():
    from etl.mart import invalider_cache_api

    invalider_cache_api()


# ------------------------------------------------------------ sources et connecteurs


def connexion_configuree(source: Source) -> bool | None:
    """Vrai si la variable d'environnement de connexion est renseignée (sa valeur n'est jamais exposée)."""
    if source.code == "chaine_depense" and source.connecteur == TypeConnecteur.ORACLE_CHAINE_DEPENSE:
        return bool(settings.SOURCES_EXTERNES["chaine_depense_oracle"]["dsn"])
    if source.connecteur in (TypeConnecteur.POSTGRES, TypeConnecteur.API):
        return bool(
            settings.SOURCES_EXTERNES.get(source.code, {}).get("url") or (source.configuration or {}).get("url")
        )
    return None


class SourceAdminSerializer(serializers.ModelSerializer):
    connexion_configuree = serializers.SerializerMethodField()
    variable_connexion = serializers.SerializerMethodField()
    nb_chargements = serializers.IntegerField(source="chargements.count", read_only=True)

    class Meta:
        model = Source
        fields = [
            "code",
            "domaine",
            "application",
            "structure",
            "statut",
            "connecteur",
            "configuration",
            "planification_cron",
            "en_production_depuis",
            "remarque",
            "connexion_configuree",
            "variable_connexion",
            "nb_chargements",
        ]
        read_only_fields = ["code", "domaine"]

    def get_connexion_configuree(self, s) -> bool | None:
        return connexion_configuree(s)

    def get_variable_connexion(self, s) -> str | None:
        return (
            VARIABLES_CONNEXION.get(s.code)
            if s.connecteur in (TypeConnecteur.POSTGRES, TypeConnecteur.ORACLE_CHAINE_DEPENSE, TypeConnecteur.API)
            else None
        )

    def validate_planification_cron(self, v):
        if v and not CRON.match(v.strip()):
            raise ValidationError("Expression cron à 5 champs attendue, ex. « 0 2 * * * ».")
        return v.strip()

    def validate_configuration(self, conf):
        if not isinstance(conf, dict):
            raise ValidationError("Objet JSON attendu.")
        interdits = [k for k in conf if re.search(r"pass|secret|mot_de_passe|token|cle", k, re.I)]
        if interdits:
            raise ValidationError(
                f"Pas de secret dans la configuration ({', '.join(interdits)}) : "
                "utiliser les variables d'environnement."
            )
        requetes = [conf.get("requete", "")] + list((conf.get("requetes") or {}).values())
        for sql in filter(None, requetes):
            if not re.match(r"^\s*(select|with)\b", sql, re.I) or re.search(
                r"\b(insert|update|delete|drop|alter|truncate|grant|create)\b", sql, re.I
            ):
                raise ValidationError("Seules les requêtes de lecture (SELECT) sont autorisées.")
        return conf


class SourceAdminViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet
):
    queryset = Source.objects.all()
    serializer_class = SourceAdminSerializer
    permission_classes = PERMISSIONS_ADMIN
    lookup_field = "code"
    pagination_class = None
    http_method_names = ["get", "patch", "post"]

    def perform_update(self, serializer):
        avant = SourceAdminSerializer(serializer.instance).data
        s = serializer.save()
        _audit(
            self.request,
            f"source {s.code}",
            {"avant": {k: avant[k] for k in serializer.validated_data}, "apres": serializer.validated_data},
        )
        _invalider()

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    @action(detail=True, methods=["get"])
    def schemas(self, request, code=None):
        """Schémas JSON des flux de la source (contrat d'échange à remettre au partenaire)."""
        from etl.schemas import schemas_source

        return Response(
            schemas_source(self.get_object().code),
            headers={"Content-Disposition": f'attachment; filename="schemas-{code}.json"'},
        )

    @extend_schema(request=None, responses={200: OpenApiTypes.OBJECT})
    @action(detail=True, methods=["post"])
    def tester(self, request, code=None):
        """Teste la connexion en lecture seule (sans rien charger)."""
        s = self.get_object()
        ok, message = tester_connexion(s)
        _audit(request, f"test de connexion {s.code}", {"ok": ok})
        return Response({"ok": ok, "message": message})


def tester_connexion(s: Source) -> tuple[bool, str]:
    if s.connecteur in (TypeConnecteur.EXCEL_CHAINE_DEPENSE, TypeConnecteur.EXCEL_GENERIQUE):
        return True, "Connecteur par import de fichier : aucune connexion à tester."
    if s.connecteur == TypeConnecteur.AUCUN:
        return False, "Aucun connecteur défini pour cette source."
    try:
        if s.connecteur == TypeConnecteur.POSTGRES:
            import psycopg

            url = settings.SOURCES_EXTERNES.get(s.code, {}).get("url")
            if not url:
                return False, f"Variable {VARIABLES_CONNEXION.get(s.code, '?')} non renseignée."
            with psycopg.connect(url, connect_timeout=5, options="-c default_transaction_read_only=on") as cnx:
                cnx.execute("SELECT 1")
            return True, "Connexion PostgreSQL établie (lecture seule)."
        if s.connecteur == TypeConnecteur.ORACLE_CHAINE_DEPENSE:
            import oracledb

            conf = settings.SOURCES_EXTERNES["chaine_depense_oracle"]
            if not conf["dsn"]:
                return False, "Variable CHAINE_DEPENSE_ORACLE_DSN non renseignée."
            with oracledb.connect(
                user=conf["user"], password=conf["password"], dsn=conf["dsn"], tcp_connect_timeout=5
            ) as cnx:
                cnx.cursor().execute("SELECT 1 FROM dual")
            return True, "Connexion Oracle établie."
        if s.connecteur == TypeConnecteur.API:
            import urllib.request

            from etl.connecteurs.generique import ApiConnector

            api = ApiConnector(s.code, s.configuration or {})
            if not api.url:
                return False, "URL de l'API absente (configuration « url » ou variable d'environnement)."
            requete = urllib.request.Request(api.url, headers={"Accept": "application/json"})
            if api.jeton:
                requete.add_header("Authorization", f"Bearer {api.jeton}")
            with urllib.request.urlopen(requete, timeout=5) as r:  # noqa: S310 (URL saisie par l'administrateur)
                return 200 <= r.status < 400, f"Réponse HTTP {r.status}{' (jeton transmis)' if api.jeton else ''}."
    except Exception as exc:  # message technique renvoyé à l'administrateur, sans secret
        return False, f"Échec : {type(exc).__name__}."
    return False, "Type de connecteur non pris en charge."


# ---------------------------------------------------------------- mappings


class MappingSerializer(serializers.ModelSerializer):
    source = serializers.SlugRelatedField(slug_field="code", queryset=Source.objects.all())

    class Meta:
        model = MappingColonnes
        fields = [
            "id",
            "source",
            "table_cible",
            "onglet",
            "colonne_source",
            "champ_cible",
            "type_donnee",
            "obligatoire",
        ]

    def validate(self, data):
        from etl.connecteurs.generique import CHAMPS_TECHNIQUES, modele_fait

        table = data.get("table_cible") or self.instance.table_cible
        champ = data.get("champ_cible") or self.instance.champ_cible
        try:
            modele = modele_fait(table)
        except Exception as exc:
            raise ValidationError({"table_cible": "Table cible inconnue."}) from exc
        champs = {f.name for f in modele._meta.concrete_fields} - CHAMPS_TECHNIQUES
        if champ not in champs:
            raise ValidationError({"champ_cible": f"Champ inconnu. Champs possibles : {', '.join(sorted(champs))}."})
        return data


class MappingViewSet(viewsets.ModelViewSet):
    serializer_class = MappingSerializer
    permission_classes = PERMISSIONS_ADMIN
    pagination_class = None

    def get_queryset(self):
        qs = MappingColonnes.objects.select_related("source").order_by("source__code", "table_cible", "id")
        p = self.request.query_params
        if p.get("source"):
            qs = qs.filter(source__code=p["source"])
        if p.get("table_cible"):
            qs = qs.filter(table_cible=p["table_cible"])
        return qs

    def perform_create(self, serializer):
        m = serializer.save()
        _audit(self.request, f"mapping {m.source.code}.{m.table_cible}.{m.champ_cible}", {"action": "création"})

    def perform_update(self, serializer):
        m = serializer.save()
        _audit(self.request, f"mapping {m.source.code}.{m.table_cible}.{m.champ_cible}", {"action": "modification"})

    def perform_destroy(self, instance):
        _audit(
            self.request,
            f"mapping {instance.source.code}.{instance.table_cible}.{instance.champ_cible}",
            {"action": "suppression"},
        )
        instance.delete()


class TablesCiblesView(APIView):
    """Tables de faits alimentables par un connecteur générique, avec leurs champs."""

    permission_classes = PERMISSIONS_ADMIN

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        from etl.connecteurs.generique import CHAMPS_TECHNIQUES

        tables = []
        for m in django_apps.get_models():
            nom = m._meta.db_table.split('"."')[-1]
            if not nom.startswith("fait_") or m._meta.app_label == "depense":
                continue
            champs = []
            for f in m._meta.concrete_fields:
                if f.name in CHAMPS_TECHNIQUES:
                    continue
                type_ = (
                    "reference"
                    if isinstance(f, models.ForeignKey)
                    else (
                        "montant"
                        if isinstance(f, models.DecimalField)
                        else (
                            "entier"
                            if isinstance(f, models.IntegerField)
                            else (
                                "date"
                                if isinstance(f, models.DateField)
                                else "booleen" if isinstance(f, models.BooleanField) else "texte"
                            )
                        )
                    )
                )
                champs.append(
                    {
                        "nom": f.name,
                        "type": type_,
                        "obligatoire": not f.null and not f.has_default(),
                        "reference": f.related_model.__name__ if f.is_relation else None,
                    }
                )
            tables.append(
                {"table": nom, "domaine": m._meta.app_label, "libelle": m._meta.verbose_name, "champs": champs}
            )
        return Response(sorted(tables, key=lambda t: (t["domaine"], t["table"])))


# ---------------------------------------------------------------- chargements


class ChargementAdminSerializer(serializers.ModelSerializer):
    source = serializers.CharField(source="source.code")
    utilisateur = serializers.CharField(source="utilisateur.username", default=None)
    demo = serializers.SerializerMethodField()

    class Meta:
        model = Chargement
        fields = [
            "id",
            "uuid",
            "source",
            "fichier",
            "fichier_archive",
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
            "demo",
            "detail",
        ]

    def get_demo(self, c) -> bool:
        return bool((c.detail or {}).get("demo"))


class ChargementAdminViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ChargementAdminSerializer
    permission_classes = PERMISSIONS_ADMIN

    def get_queryset(self):
        qs = Chargement.objects.select_related("source", "utilisateur")
        p = self.request.query_params
        if p.get("source"):
            qs = qs.filter(source__code=p["source"])
        if p.get("statut"):
            qs = qs.filter(statut=p["statut"])
        return qs

    @extend_schema(responses={(200, "application/octet-stream"): OpenApiTypes.BINARY})
    @action(detail=True, methods=["get"])
    def fichier(self, request, pk=None):
        """Fichier (ou réponse d'API) tel que reçu, conservé en zone brute."""
        from etl import zone_brute

        ch = self.get_object()
        if not ch.fichier_archive:
            raise NotFound("Aucun fichier conservé pour ce chargement.")
        chemin = zone_brute.chemin_absolu(ch.fichier_archive)
        if not chemin.is_file():
            raise NotFound("Le fichier n'est plus présent dans la zone brute.")
        _audit(request, f"téléchargement du fichier brut du chargement {ch.id}", {"uuid": str(ch.uuid)})
        nom = Path(ch.fichier).name if ch.fichier and not ch.fichier.startswith("api://") else chemin.name
        if not Path(nom).suffix:
            nom += chemin.suffix
        return FileResponse(open(chemin, "rb"), as_attachment=True, filename=nom)


# ------------------------------------------------------------ règles d'alerte


class RegleAlerteSerializer(serializers.ModelSerializer):
    nb_alertes_ouvertes = serializers.SerializerMethodField()

    class Meta:
        model = RegleAlerte
        fields = [
            "id",
            "code",
            "domaine",
            "severite",
            "classe",
            "seuils",
            "titre_modele",
            "message_modele",
            "action_recommandee",
            "lien",
            "actif",
            "nb_alertes_ouvertes",
        ]
        read_only_fields = ["code", "domaine", "classe"]

    def get_nb_alertes_ouvertes(self, r) -> int:
        return r.alertes.exclude(statut="traitee").count()


class RegleAlerteViewSet(mixins.ListModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    queryset = RegleAlerte.objects.all()
    serializer_class = RegleAlerteSerializer
    permission_classes = PERMISSIONS_ADMIN
    pagination_class = None
    http_method_names = ["get", "patch", "post"]

    def perform_update(self, serializer):
        r = serializer.save()
        _audit(self.request, f"règle d'alerte {r.code}", {"modifie": list(serializer.validated_data)})

    @extend_schema(request=None, responses={200: OpenApiTypes.OBJECT})
    @action(detail=False, methods=["post"])
    def evaluer(self, request):
        from .alertes import evaluer_alertes

        n = len(evaluer_alertes())
        _invalider()
        _audit(request, "évaluation des alertes", {"alertes": n})
        return Response({"alertes_creees": n})


# ------------------------------------------------------------ utilisateurs


class UtilisateurSerializer(serializers.ModelSerializer):
    mot_de_passe = serializers.CharField(write_only=True, required=False, allow_blank=True)
    a_2fa = serializers.SerializerMethodField()

    class Meta:
        model = Utilisateur
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "role",
            "domaines",
            "structure",
            "is_active",
            "last_login",
            "date_joined",
            "a_2fa",
            "mot_de_passe",
        ]
        read_only_fields = ["last_login", "date_joined"]

    def get_a_2fa(self, u) -> bool:
        return TOTPDevice.objects.filter(user=u, confirmed=True).exists()

    def validate_domaines(self, v):
        inconnus = set(v) - set(Domaine.values)
        if inconnus:
            raise ValidationError(f"Domaines inconnus : {', '.join(sorted(inconnus))}")
        return v

    def create(self, data):
        mdp = data.pop("mot_de_passe", "") or get_random_string(20) + "aA1!"
        u = Utilisateur(**data)
        validate_password(mdp, u)
        u.set_password(mdp)
        u.save()
        u._mot_de_passe_initial = mdp
        return u

    def update(self, u, data):
        mdp = data.pop("mot_de_passe", "")
        for k, v in data.items():
            setattr(u, k, v)
        if mdp:
            validate_password(mdp, u)
            u.set_password(mdp)
        u.save()
        return u


class UtilisateurViewSet(viewsets.ModelViewSet):
    serializer_class = UtilisateurSerializer
    permission_classes = PERMISSIONS_ADMIN
    pagination_class = None
    http_method_names = ["get", "post", "patch"]  # pas de suppression : désactiver (traçabilité)

    def get_queryset(self):
        return Utilisateur.objects.filter(jeton_partage__isnull=True).order_by("username")

    def create(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        try:
            u = s.save()
        except Exception as exc:
            raise ValidationError({"mot_de_passe": list(getattr(exc, "messages", [str(exc)]))}) from exc
        _audit(request, f"utilisateur {u.username}", {"action": "création", "role": u.role})
        donnees = self.get_serializer(u).data
        if not request.data.get("mot_de_passe"):
            donnees["mot_de_passe_initial"] = u._mot_de_passe_initial  # affiché une seule fois
        return Response(donnees, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        if serializer.instance == self.request.user and serializer.validated_data.get("is_active") is False:
            raise ValidationError("Vous ne pouvez pas désactiver votre propre compte.")
        u = serializer.save()
        _audit(
            self.request,
            f"utilisateur {u.username}",
            {"modifie": [k for k in serializer.validated_data if k != "mot_de_passe"]},
        )

    @extend_schema(request=None, responses={200: OpenApiTypes.OBJECT})
    @action(detail=True, methods=["post"], url_path="reinitialiser-2fa")
    def reinitialiser_2fa(self, request, pk=None):
        u = self.get_object()
        TOTPDevice.objects.filter(user=u).delete()
        _audit(request, f"utilisateur {u.username}", {"action": "réinitialisation 2FA"})
        return Response({"detail": "Double authentification réinitialisée : réenrôlement à la prochaine connexion."})


# ------------------------------------------------------------ partage de données


class JetonSerializer(serializers.ModelSerializer):
    cree_par = serializers.CharField(source="cree_par.username", default=None, read_only=True)

    class Meta:
        model = JetonPartage
        fields = [
            "id",
            "nom",
            "destinataire",
            "domaines",
            "prefixe",
            "expire_le",
            "actif",
            "cree_le",
            "cree_par",
            "derniere_utilisation",
        ]
        read_only_fields = ["prefixe", "cree_le", "cree_par", "derniere_utilisation"]

    def validate_domaines(self, v):
        permis = set(Domaine.values) - {Domaine.PREPARATION}
        if not v or set(v) - permis:
            raise ValidationError("Au moins un domaine valide.")
        return v


class JetonViewSet(viewsets.ModelViewSet):
    queryset = JetonPartage.objects.select_related("cree_par")
    serializer_class = JetonSerializer
    permission_classes = PERMISSIONS_ADMIN
    pagination_class = None
    http_method_names = ["get", "post", "patch", "delete"]

    def create(self, request, *args, **kwargs):
        from .partage import creer_jeton

        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        v = s.validated_data
        jeton, cle = creer_jeton(v["nom"], v["destinataire"], v["domaines"], v.get("expire_le"), request.user)
        _audit(request, f"jeton de partage {jeton.prefixe}", {"action": "création", "domaines": v["domaines"]})
        return Response({**self.get_serializer(jeton).data, "cle": cle}, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        j = serializer.save()
        # Le compte technique suit l'état et le périmètre du jeton.
        j.compte.domaines = j.domaines
        j.compte.is_active = j.actif
        j.compte.save(update_fields=["domaines", "is_active"])
        _audit(self.request, f"jeton de partage {j.prefixe}", {"modifie": list(serializer.validated_data)})

    def perform_destroy(self, instance):
        _audit(self.request, f"jeton de partage {instance.prefixe}", {"action": "révocation"})
        instance.compte.delete()  # supprime aussi le jeton (cascade)


# ------------------------------------------------------------ entrepôt


class EntrepotView(APIView):
    """État de l'entrepôt : volumes par table et par source, vues mart ; rafraîchissement."""

    permission_classes = PERMISSIONS_ADMIN

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        from etl.mart import VUES_MART, version_donnees

        with connection.cursor() as c:
            c.execute("""SELECT schemaname, relname, n_live_tup FROM pg_stat_user_tables
                         WHERE schemaname IN ('ref', 'dw') ORDER BY schemaname, relname""")
            tables = [{"schema": s, "table": t, "lignes": n} for s, t, n in c.fetchall()]
            vues = []
            for v in VUES_MART:
                c.execute(f"SELECT count(*) FROM mart.{v}")
                vues.append({"vue": v, "lignes": c.fetchone()[0]})
            c.execute("SELECT pg_size_pretty(pg_database_size(current_database()))")
            taille = c.fetchone()[0]
        from etl import depots, zone_brute

        fichiers = [f for f in zone_brute.racine().rglob("*") if f.is_file()]
        depots.preparer_dossiers()
        en_attente = [
            {"source": d.name, "fichier": f.name, "octets": f.stat().st_size}
            for d in sorted(depots.racine().iterdir())
            if d.is_dir()
            for f in sorted(d.iterdir())
            if f.is_file() and not f.name.startswith(".")
        ]
        return Response(
            {
                "depot": {
                    "dossier": str(depots.racine()),
                    "releve_minutes": settings.DEPOT_RELEVE_MINUTES,
                    "en_attente": en_attente,
                },
                "evenements_amqp": bool(settings.EVENEMENTS_AMQP_URL),
                "tables": tables,
                "vues": vues,
                "taille_base": taille,
                "zone_brute": {"fichiers": len(fichiers), "octets": sum(f.stat().st_size for f in fichiers)},
                "version_cache": version_donnees(),
                "sources": [
                    {
                        "code": s.code,
                        "application": s.application,
                        "statut": s.statut,
                        "chargements": s.chargements.count(),
                    }
                    for s in Source.objects.all()
                ],
            }
        )

    @extend_schema(request=None, responses={200: OpenApiTypes.OBJECT})
    def post(self, request):
        """Actions : rafraichir (vues mart + cache), demo (générer), demo_supprimer."""
        from etl.mart import invalider_cache_api, rafraichir_vues

        from . import demo

        a = request.data.get("action")
        if a == "rafraichir":
            rafraichir_vues()
            invalider_cache_api()
            resultat = {"detail": "Vues matérialisées rafraîchies et cache invalidé."}
        elif a == "demo":
            resultat = {"detail": "Données d'illustration chargées.", "sources": demo.generer()}
        elif a == "demo_supprimer":
            demo.supprimer()
            resultat = {"detail": "Données d'illustration supprimées."}
        elif a == "relever":
            from etl.depots import relever

            releves = relever()
            resultat = {
                "detail": f"{len(releves)} fichier(s) relevé(s) dans le dépôt.",
                "sources": {f"{x['source']} · {x['fichier']}": x["statut"] for x in releves},
            }
        else:
            raise ValidationError({"action": "rafraichir | demo | demo_supprimer | relever"})
        _audit(request, f"entrepôt : {a}")
        return Response(resultat)


ROLES = [{"code": r.value, "libelle": r.label} for r in Role]
DOMAINES = [{"code": d.value, "libelle": d.label} for d in Domaine]
CONNECTEURS = [{"code": c.value, "libelle": c.label} for c in TypeConnecteur]
STATUTS = [{"code": s.value, "libelle": s.label} for s in StatutSource]


class ReferentielsAdminView(APIView):
    """Listes de valeurs des formulaires d'administration."""

    permission_classes = PERMISSIONS_ADMIN

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        return Response(
            {
                "roles": ROLES,
                "domaines": DOMAINES,
                "connecteurs": CONNECTEURS,
                "statuts": STATUTS,
                "types_donnee": [
                    {"code": c, "libelle": l} for c, l in MappingColonnes._meta.get_field("type_donnee").choices
                ],
            }
        )
