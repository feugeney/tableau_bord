import { Link } from "react-router-dom";

export default function PageIntrouvable() {
  return (
    <div className="carte px-6 py-8">
      <h1 className="text-lg font-bold text-ink">Page introuvable</h1>
      <p className="text-base text-ink-2">
        Cette adresse ne correspond à aucune page, ou la page n'est pas dans votre périmètre.{" "}
        <Link to="/synthese" className="font-bold text-ink underline">
          Revenir à la synthèse
        </Link>
      </p>
    </div>
  );
}
