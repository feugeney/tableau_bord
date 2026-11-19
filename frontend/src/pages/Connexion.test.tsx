import { act, fireEvent, screen, waitFor } from "@testing-library/react";

import { api, ErreurApi } from "@/api/client";
import * as auth from "@/hooks/useAuth";
import { rendre } from "@/test/rendu";

import { Activer2FA, Connexion } from "./Connexion";

function preparer() {
  const connecter = vi.fn().mockResolvedValue(undefined);
  const appliquerConnexion = vi.fn();
  vi.spyOn(auth, "useAuth").mockReturnValue({
    utilisateur: null,
    chargement: false,
    connecter,
    appliquerConnexion,
    deconnecter: vi.fn(),
  });
  return { connecter, appliquerConnexion };
}

function identifiants() {
  fireEvent.change(screen.getByLabelText("Identifiant"), { target: { value: " agent.test " } });
  fireEvent.change(screen.getByLabelText("Mot de passe"), { target: { value: " Mot de passe ! " } });
}

describe("connexion institutionnelle", () => {
  it("permet de voir le mot de passe sans changer sa valeur et transmet les identifiants", async () => {
    const { connecter } = preparer();
    rendre(<Connexion />);
    identifiants();
    const motDePasse = screen.getByLabelText("Mot de passe");
    expect(motDePasse).toHaveAttribute("type", "password");
    fireEvent.click(screen.getByRole("button", { name: "Afficher le mot de passe" }));
    expect(motDePasse).toHaveAttribute("type", "text");
    expect(motDePasse).toHaveValue(" Mot de passe ! ");
    fireEvent.click(screen.getByRole("button", { name: "Masquer le mot de passe" }));
    fireEvent.click(screen.getByRole("button", { name: "Se connecter" }));
    await waitFor(() => expect(connecter).toHaveBeenCalledWith("agent.test", " Mot de passe ! ", undefined));
  });

  it("présente et focalise l'étape OTP uniquement lorsque le serveur la demande", async () => {
    const { connecter } = preparer();
    connecter.mockRejectedValueOnce(new ErreurApi(401, { code: "otp_requis" }));
    rendre(<Connexion />);
    identifiants();
    fireEvent.click(screen.getByRole("button", { name: "Se connecter" }));
    const code = await screen.findByLabelText("Code de vérification");
    expect(code).toHaveFocus();
    expect(screen.queryByLabelText("Mot de passe")).not.toBeInTheDocument();
    fireEvent.change(code, { target: { value: "12 34a56" } });
    expect(code).toHaveValue("123456");
    fireEvent.click(screen.getByRole("button", { name: "Vérifier et se connecter" }));
    await waitFor(() =>
      expect(connecter).toHaveBeenLastCalledWith("agent.test", " Mot de passe ! ", "123456"),
    );
  });

  it("différencie un code OTP refusé d'un mot de passe incorrect", async () => {
    const { connecter } = preparer();
    connecter
      .mockRejectedValueOnce(new ErreurApi(401, { code: "otp_requis" }))
      .mockRejectedValueOnce(new ErreurApi(401, { code: "otp_invalide" }));
    rendre(<Connexion />);
    identifiants();
    fireEvent.click(screen.getByRole("button", { name: "Se connecter" }));
    fireEvent.change(await screen.findByLabelText("Code de vérification"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "Vérifier et se connecter" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Ce code est incorrect ou a expiré");
    expect(screen.getByLabelText("Code de vérification")).toHaveFocus();
    expect(screen.getByLabelText("Code de vérification")).toHaveValue("");
    expect(screen.getByLabelText("Code de vérification")).toHaveAttribute("aria-invalid", "true");
  });

  it("signale la limitation des tentatives et réactive le formulaire", async () => {
    const { connecter } = preparer();
    connecter.mockRejectedValue(new ErreurApi(429));
    rendre(<Connexion />);
    identifiants();
    fireEvent.click(screen.getByRole("button", { name: "Se connecter" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Trop de tentatives");
    expect(screen.getByRole("button", { name: "Se connecter" })).not.toBeDisabled();
  });

  it("évite les doubles soumissions pendant la connexion", async () => {
    const { connecter } = preparer();
    let terminer: () => void = () => {};
    connecter.mockImplementation(
      () =>
        new Promise<void>((resolve) => {
          terminer = resolve;
        }),
    );
    rendre(<Connexion />);
    identifiants();
    fireEvent.click(screen.getByRole("button", { name: "Se connecter" }));
    expect(screen.getByRole("button", { name: "Connexion en cours…" })).toBeDisabled();
    expect(screen.getByLabelText("Identifiant")).toBeDisabled();
    expect(connecter).toHaveBeenCalledTimes(1);
    await act(async () => terminer());
  });

  it("permet de modifier le compte après la demande OTP en effaçant le mot de passe", async () => {
    const { connecter } = preparer();
    connecter.mockRejectedValueOnce(new ErreurApi(401, { code: "otp_requis" }));
    rendre(<Connexion />);
    identifiants();
    fireEvent.click(screen.getByRole("button", { name: "Se connecter" }));
    await screen.findByLabelText("Code de vérification");
    fireEvent.click(screen.getByRole("button", { name: "Modifier" }));
    expect(screen.getByLabelText("Mot de passe")).toHaveValue("");
    expect(screen.getByLabelText("Identifiant")).toHaveValue(" agent.test ");
  });

  it("gère un échec de démarrage de la double authentification sans bloquer l'écran", async () => {
    preparer();
    vi.spyOn(api, "post").mockRejectedValue(new Error("réseau"));
    rendre(<Activer2FA />);
    fireEvent.click(screen.getByRole("button", { name: "Configurer la vérification" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("L’activation n’a pas pu démarrer");
    expect(screen.getByRole("button", { name: "Configurer la vérification" })).not.toBeDisabled();
  });

  it("confirme l'association 2FA avec le code de l'application", async () => {
    const { appliquerConnexion } = preparer();
    const resultat = { access: "jeton-test", refresh: "refresh-test", utilisateur: { a_2fa: true } };
    const post = vi
      .spyOn(api, "post")
      .mockResolvedValueOnce({ otpauth_url: "otpauth://totp/Essai?secret=JBSWY3DPEHPK3PXP&issuer=Essai" })
      .mockResolvedValueOnce(resultat);
    rendre(<Activer2FA />);
    fireEvent.click(screen.getByRole("button", { name: "Configurer la vérification" }));
    const code = await screen.findByLabelText("Code à 6 chiffres");
    expect(code).toHaveFocus();
    fireEvent.change(code, { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "Activer et accéder à mon espace" }));
    await waitFor(() =>
      expect(post).toHaveBeenLastCalledWith("/auth/2fa/confirmer/", { code_otp: "123456" }),
    );
    expect(appliquerConnexion).toHaveBeenCalledWith(resultat);
  });
});
