import "@fontsource/source-serif-4/latin-600.css";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import { App } from "./App";
import { TooltipProvider } from "./components/ui/primitives";
import { AuthProvider } from "./hooks/useAuth";
import { PresentationProvider } from "./hooks/usePresentation";
import "./theme/tokens.css";
import "./theme/base.css";
import "./theme/signature.css";
import "./theme/print.css";
import { ThemeProvider } from "./theme/ThemeProvider";

const client = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      retry: (n, e) => n < 1 && !(e && "statut" in e && Number(e.statut) < 500),
      refetchOnWindowFocus: false,
    },
  },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={client}>
      <ThemeProvider>
        <PresentationProvider>
          <TooltipProvider>
            <BrowserRouter>
              <AuthProvider>
                <App />
              </AuthProvider>
            </BrowserRouter>
          </TooltipProvider>
        </PresentationProvider>
      </ThemeProvider>
    </QueryClientProvider>
  </StrictMode>,
);
