import { useEffect, useState } from "react";
import { createWorkspace, getPhotoCounts } from "../api/endpoints";
import { strings } from "../strings/pt-BR";

const STORAGE_KEY = "report-works.workspace";

function readStored(): string | null {
  try {
    return window.localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

function writeStored(id: string): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, id);
  } catch {
    // Armazenamento indisponível (modo privado): a área vale só para esta sessão.
  }
}

/** Reaproveita a área de trabalho da sessão anterior ou cria uma nova. */
export function useWorkspace(): { workspaceId: string | null; error: string | null } {
  const [workspaceId, setWorkspaceId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const stored = readStored();
        if (stored) {
          try {
            await getPhotoCounts(stored);
            if (!cancelled) setWorkspaceId(stored);
            return;
          } catch {
            // Área expirada ou removida: cai para a criação de uma nova.
          }
        }
        const created = await createWorkspace();
        writeStored(created.id);
        if (!cancelled) setWorkspaceId(created.id);
      } catch {
        if (!cancelled) setError(strings.server.offline);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return { workspaceId, error };
}
