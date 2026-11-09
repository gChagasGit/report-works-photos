import { useDebouncedValue } from "@mantine/hooks";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { validateReport } from "../api/endpoints";
import { draftHasErrors, toConfig, type ReportDraft } from "../domain/report";

const DEBOUNCE_MS = 400;

/**
 * Validação em tempo real: reconfere template, pastas e contagens sempre que o rascunho muda
 * (com espera de 400 ms) ou quando novas fotos chegam (`refreshKey`).
 */
export function useValidation(
  workspaceId: string | null,
  draft: ReportDraft,
  enabled: boolean,
  refreshKey: number,
) {
  const config = useMemo(() => toConfig(draft), [draft]);
  const [debounced] = useDebouncedValue(config, DEBOUNCE_MS);
  const ready = enabled && workspaceId !== null && !draftHasErrors(draft);

  return useQuery({
    queryKey: ["validate", workspaceId, debounced, refreshKey],
    queryFn: () => validateReport(workspaceId ?? "", debounced),
    enabled: ready,
    retry: false,
    placeholderData: keepPreviousData,
  });
}
