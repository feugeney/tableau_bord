"""Installation et exploitation natives Windows, sans service de conteneurs."""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
BACKEND = RACINE / "backend"
ETAT = BACKEND / ".local"
FICHIER_ENV = BACKEND / ".env"
MANAGE = BACKEND / "manage.py"
PORT_HTTP = 8000
URL = f"http://127.0.0.1:{PORT_HTTP}"
MASQUE_FENETRE = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
WINDOWS = Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32"


def lire_env(fichier):
    valeurs = {}
    if fichier.is_file():
        for ligne in fichier.read_text(encoding="utf-8-sig").splitlines():
            if ligne.strip() and not ligne.lstrip().startswith("#") and "=" in ligne:
                cle, valeur = ligne.split("=", 1)
                valeur = valeur.strip()
                if len(valeur) > 1 and valeur[0] == valeur[-1] and valeur[0] in "\"'":
                    valeur = valeur[1:-1]
                valeurs[cle.strip()] = valeur
    return valeurs


def configurer():
    """Préserve les secrets et les connexions métier déjà configurées."""
    valeurs = lire_env(FICHIER_ENV if FICHIER_ENV.exists() else RACINE / ".env")
    defauts = {
        "POSTGRES_DB": "tdb",
        "POSTGRES_USER": "tdb",
        "POSTGRES_HOST": "::1",
        "POSTGRES_PORT": "55432",
        "POSTGRES_PASSWORD": secrets.token_urlsafe(32),
        "DJANGO_SECRET_KEY": secrets.token_urlsafe(48),
    }
    mises_a_jour = {k: valeurs.get(k) or v for k, v in defauts.items()}
    for cle in ("DJANGO_SECRET_KEY", "POSTGRES_PASSWORD"):
        if mises_a_jour[cle].startswith("a-generer") or mises_a_jour[cle] in (
            "a-changer",
            "dev-insecure-change-me",
        ):
            mises_a_jour[cle] = defauts[cle]
    if mises_a_jour["POSTGRES_HOST"] not in ("::1", "127.0.0.1", "localhost"):
        raise RuntimeError(
            "La base configuree n'est pas locale. Aucun parametre distant n'a ete remplace."
        )
    mises_a_jour.update(
        {
            "DJANGO_DEBUG": "true",
            "DJANGO_ALLOWED_HOSTS": "127.0.0.1,localhost,[::1]",
            "DJANGO_SECURE_SSL_REDIRECT": "false",
            "SERVIR_FRONTEND_LOCAL": "true",
            "REDIS_URL": "",
            "CELERY_BROKER_URL": "memory://",
            "CELERY_RESULT_BACKEND": "cache+memory://",
            "EVENEMENTS_AMQP_URL": "",
        }
    )
    texte = (
        FICHIER_ENV.read_text(encoding="utf-8-sig")
        if FICHIER_ENV.exists()
        else "".join(f"{k}={v}\n" for k, v in valeurs.items())
    )
    for cle, valeur in mises_a_jour.items():
        expression = rf"(?m)^{re.escape(cle)}=.*$"
        ligne = f"{cle}={valeur}"
        if re.search(expression, texte):
            texte = re.sub(expression, lambda _m, contenu=ligne: contenu, texte)
        else:
            texte = texte.rstrip() + "\n" + ligne + "\n"
    FICHIER_ENV.write_text(texte, encoding="utf-8")
    valeurs.update(mises_a_jour)
    for cle, valeur in valeurs.items():
        os.environ[cle] = valeur
    os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.dev"
    ETAT.mkdir(exist_ok=True)
    return valeurs


def dossier_pg(conf):
    return Path(
        conf.get("LOCAL_PG_DATA")
        or Path(os.environ["LOCALAPPDATA"]) / "tdb-ministre" / "pgdata"
    )


def binaires_pg(conf):
    donnees = dossier_pg(conf)
    version = (
        (donnees / "PG_VERSION").read_text().strip()
        if (donnees / "PG_VERSION").exists()
        else None
    )
    base = Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "PostgreSQL"
    versions = sorted(
        (p for p in base.glob("*") if p.name.isdigit()),
        key=lambda p: int(p.name),
        reverse=True,
    )
    candidats = [base / version] if version else versions
    for candidat in candidats:
        if (candidat / "bin/pg_ctl.exe").is_file():
            return candidat / "bin"
    raise RuntimeError(
        "PostgreSQL natif est requis. Installer PostgreSQL avant Installer.cmd."
    )


def commande(arguments, **options):
    return subprocess.run(
        [str(a) for a in arguments], check=True, creationflags=MASQUE_FENETRE, **options
    )


def assurer_base(conf):
    import psycopg
    from psycopg import sql

    donnees, binaires = dossier_pg(conf), binaires_pg(conf)
    if not (donnees / "PG_VERSION").exists():
        donnees.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, encoding="utf-8"
        ) as fichier:
            fichier.write(conf["POSTGRES_PASSWORD"])
            mot_de_passe = Path(fichier.name)
        try:
            commande(
                [
                    binaires / "initdb.exe",
                    "-D",
                    donnees,
                    "-U",
                    conf["POSTGRES_USER"],
                    "--pwfile",
                    mot_de_passe,
                    "--encoding=UTF8",
                    "--locale=C",
                    "--auth=scram-sha-256",
                ],
                stdout=subprocess.DEVNULL,
            )
        finally:
            mot_de_passe.unlink(missing_ok=True)
        print("Instance PostgreSQL locale creee dans le profil Windows.")
    statut = subprocess.run(
        [str(binaires / "pg_ctl.exe"), "status", "-D", str(donnees)],
        capture_output=True,
        creationflags=MASQUE_FENETRE,
        check=False,
    )
    if statut.returncode:
        (ETAT / "logs").mkdir(exist_ok=True)
        commande(
            [
                binaires / "pg_ctl.exe",
                "start",
                "-D",
                donnees,
                "-l",
                ETAT / "logs/postgres.log",
                "-o",
                f"-h {conf['POSTGRES_HOST']} -p {int(conf['POSTGRES_PORT'])}",
                "-w",
            ],
            stdout=subprocess.DEVNULL,
        )
    connexion = {
        "host": conf["POSTGRES_HOST"],
        "port": conf["POSTGRES_PORT"],
        "user": conf["POSTGRES_USER"],
        "password": conf["POSTGRES_PASSWORD"],
        "connect_timeout": 5,
    }
    try:
        with psycopg.connect(dbname="postgres", autocommit=True, **connexion) as cnx:
            existe = cnx.execute(
                "SELECT 1 FROM pg_database WHERE datname=%s", [conf["POSTGRES_DB"]]
            ).fetchone()
            if not existe:
                cnx.execute(
                    sql.SQL("CREATE DATABASE {} OWNER {}").format(
                        sql.Identifier(conf["POSTGRES_DB"]),
                        sql.Identifier(conf["POSTGRES_USER"]),
                    )
                )
                print("Base centrale creee.")
        with psycopg.connect(dbname=conf["POSTGRES_DB"], **connexion) as cnx:
            cnx.execute("SELECT 1")
    except psycopg.Error:
        raise RuntimeError(
            "Connexion a la base locale impossible. Verifier backend/.env et le journal PostgreSQL."
        ) from None
    print(
        f"PostgreSQL local : {conf['POSTGRES_DB']} ({conf['POSTGRES_HOST']}:{conf['POSTGRES_PORT']})."
    )


def django():
    sys.path.insert(0, str(BACKEND))
    import django as moteur

    moteur.setup()


def preparer(conf):
    assurer_base(conf)
    django()
    from apps.core.models import Domaine, Role, Utilisateur
    from django.core.management import call_command

    call_command("migrate", interactive=False, verbosity=0)
    call_command("initialiser", verbosity=0)
    if not Utilisateur.objects.exists():
        secret = secrets.token_urlsafe(18)
        Utilisateur.objects.create_superuser(
            "admin-local",
            password=secret,
            role=Role.DNSI_ADMIN,
            domaines=list(Domaine.values),
        )
        (ETAT / "identifiants-initiaux.txt").write_text(
            f"Identifiant : admin-local\nMot de passe initial : {secret}\n"
            "La double authentification se configure a la premiere connexion.\n",
            encoding="utf-8",
        )
        print("Compte initial cree : backend/.local/identifiants-initiaux.txt")
    else:
        print("Comptes, sources et donnees existants conserves.")


def sante():
    try:
        with urllib.request.urlopen(URL + "/sante/", timeout=2) as reponse:
            resultat = json.load(reponse)
        return resultat if resultat.get("application") == "dashboard-mefb" else None
    except (OSError, ValueError):
        return None


def lancer(conf, navigateur):
    preparer(conf)
    actif = sante()
    if not actif:
        (ETAT / "logs").mkdir(exist_ok=True)
        with (ETAT / "logs/application.log").open("ab") as journal:
            processus = subprocess.Popen(
                [
                    sys.executable,
                    str(MANAGE),
                    "runserver",
                    f"127.0.0.1:{PORT_HTTP}",
                    "--noreload",
                ],
                cwd=BACKEND,
                stdout=journal,
                stderr=journal,
                creationflags=MASQUE_FENETRE,
            )
        for _ in range(30):
            actif = sante()
            if actif:
                break
            if processus.poll() is not None:
                raise RuntimeError(
                    "Demarrage impossible. Voir backend/.local/logs/application.log."
                )
            time.sleep(0.5)
        if not actif:
            raise RuntimeError(
                "Le serveur local ne repond pas. Verifier le port 8000 et le journal."
            )
    (ETAT / "services.json").write_text(
        json.dumps({"pid": actif.get("pid"), "url": URL}), encoding="utf-8"
    )
    lancer_planificateur()
    print(
        f"Application prete : {URL}\nAucun serveur Docker, Redis ou Node n'est requis pendant l'utilisation."
    )
    if navigateur:
        webbrowser.open(URL)


def lancer_planificateur():
    """Chargements programmes (Administration > Flux ETL) : un seul planificateur par base."""
    from etl.planificateur import planificateur_actif

    if planificateur_actif():
        print("Planificateur des chargements deja actif.")
        return
    (ETAT / "logs").mkdir(exist_ok=True)
    with (ETAT / "logs/planificateur.log").open("ab") as journal:
        processus = subprocess.Popen(
            [sys.executable, str(MANAGE), "planificateur"],
            cwd=BACKEND,
            stdout=journal,
            stderr=journal,
            creationflags=MASQUE_FENETRE,
        )
    (ETAT / "planificateur.pid").write_text(str(processus.pid), encoding="utf-8")
    print(
        "Planificateur des chargements demarre (journal : backend/.local/logs/planificateur.log)."
    )


def ligne_de_commande(pid):
    requete = (
        f"Get-CimInstance Win32_Process -Filter 'ProcessId = {int(pid)}' | "
        "Select-Object CommandLine | ConvertTo-Json -Compress"
    )
    resultat = subprocess.run(
        [
            str(WINDOWS / "WindowsPowerShell/v1.0/powershell.exe"),
            "-NoProfile",
            "-Command",
            requete,
        ],
        capture_output=True,
        text=True,
        creationflags=MASQUE_FENETRE,
        check=True,
    )
    return (json.loads(resultat.stdout or "null") or {}).get("CommandLine") or ""


def arreter_planificateur():
    fichier = ETAT / "planificateur.pid"
    if not fichier.exists():
        return
    pid = fichier.read_text(encoding="utf-8").strip()
    # Un identifiant recycle par Windows ne doit jamais faire arreter un autre programme.
    if pid.isdigit():
        commande_lancee = ligne_de_commande(pid)
        if (
            str(BACKEND).lower() in commande_lancee.lower()
            and "planificateur" in commande_lancee
        ):
            commande(
                [WINDOWS / "taskkill.exe", "/PID", pid, "/T", "/F"],
                stdout=subprocess.DEVNULL,
            )
    fichier.unlink(missing_ok=True)


def sauvegarder(conf):
    assurer_base(conf)
    destination = RACINE / "sauvegardes"
    destination.mkdir(exist_ok=True)
    instant = datetime.now(tz=timezone.utc).astimezone()
    fichier = destination / f"{conf['POSTGRES_DB']}-{instant:%Y%m%d-%H%M%S}.dump"
    environnement = {**os.environ, "PGPASSWORD": conf["POSTGRES_PASSWORD"]}
    binaires = binaires_pg(conf)
    commande(
        [
            binaires / "pg_dump.exe",
            "-h",
            conf["POSTGRES_HOST"],
            "-p",
            conf["POSTGRES_PORT"],
            "-U",
            conf["POSTGRES_USER"],
            "-d",
            conf["POSTGRES_DB"],
            "-F",
            "c",
            "-f",
            fichier,
        ],
        env=environnement,
    )
    commande(
        [binaires / "pg_restore.exe", "--list", fichier], stdout=subprocess.DEVNULL
    )
    print(f"Sauvegarde verifiee : {fichier}")


def arreter(conf):
    arreter_planificateur()
    actif = sante()
    if actif and actif.get("mode") == "local" and actif.get("pid"):
        pid = int(actif["pid"])
        commande_serveur = ligne_de_commande(pid)
        if (
            str(BACKEND).lower() in commande_serveur.lower()
            and "runserver" in commande_serveur
        ):
            commande(
                [WINDOWS / "taskkill.exe", "/PID", str(pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
            )
        else:
            raise RuntimeError(
                "Le processus du port 8000 n'a pas ete reconnu comme celui de ce projet."
            )
    donnees = dossier_pg(conf)
    if (donnees / "PG_VERSION").exists():
        statut = subprocess.run(
            [str(binaires_pg(conf) / "pg_ctl.exe"), "status", "-D", str(donnees)],
            capture_output=True,
            creationflags=MASQUE_FENETRE,
            check=False,
        )
        if statut.returncode == 0:
            commande(
                [
                    binaires_pg(conf) / "pg_ctl.exe",
                    "stop",
                    "-D",
                    donnees,
                    "-m",
                    "fast",
                    "-w",
                ],
                stdout=subprocess.DEVNULL,
            )
    (ETAT / "services.json").unlink(missing_ok=True)
    print(
        "Application et instance PostgreSQL du projet arretees. Les donnees sont conservees."
    )


def main():
    parseur = argparse.ArgumentParser()
    parseur.add_argument(
        "action",
        choices=["installer", "lancer", "arreter", "sauvegarder", "diagnostic"],
    )
    parseur.add_argument("--sans-navigateur", action="store_true")
    args = parseur.parse_args()
    conf = configurer()
    if args.action == "lancer":
        lancer(conf, not args.sans_navigateur)
    elif args.action == "installer":
        preparer(conf)
        print("Installation terminee. Double-cliquez sur Lancer.cmd.")
    elif args.action == "arreter":
        arreter(conf)
    elif args.action == "sauvegarder":
        sauvegarder(conf)
    else:
        assurer_base(conf)
        print(f"Interface compilee : {(RACINE / 'frontend/dist/index.html').is_file()}")
        print(f"Application demarree : {bool(sante())}")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as erreur:
        print(f"Erreur : {erreur}", file=sys.stderr)
        sys.exit(1)
    # Ne pas afficher les exceptions des pilotes : elles peuvent contenir des secrets.
    except Exception as erreur:  # noqa: BLE001
        print(
            f"Operation impossible ({type(erreur).__name__}). Verifier les journaux locaux.",
            file=sys.stderr,
        )
        sys.exit(1)
