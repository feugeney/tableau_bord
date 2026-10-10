import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter } from "react-router-dom";

import { TooltipProvider } from "@/components/ui/primitives";

export function rendre(ui: ReactElement, route = "/") {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <TooltipProvider>
        <MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter>
      </TooltipProvider>
    </QueryClientProvider>,
  );
}

/** Remplace fetch : chaque chemin d'API renvoie le corps donné. */
export function simulerApi(reponses: Record<string, unknown>) {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (entree) => {
    const url = String(entree);
    const cle = Object.keys(reponses).find((k) => url.includes(k));
    const corps = cle ? reponses[cle] : { detail: "introuvable" };
    return new Response(JSON.stringify(corps), { status: cle ? 200 : 404 });
  });
}
