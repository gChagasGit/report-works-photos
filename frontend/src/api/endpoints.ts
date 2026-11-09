import type { components } from "./schema";
import { requestJson } from "./client";

type Schemas = components["schemas"];

export type TemplateSummary = Schemas["TemplateSummary"];
export type ValidationOut = Schemas["ValidationOut"];
export type IssueOut = Schemas["IssueOut"];
export type JobOut = Schemas["JobOut"];
export type ZipOut = Schemas["ZipOut"];
export type UploadOut = Schemas["UploadOut"];
export type ReportConfig = Schemas["ReportConfig"];

const json = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

function upload(method: "PUT" | "POST", file: File | File[], field: string): RequestInit {
  const form = new FormData();
  for (const item of Array.isArray(file) ? file : [file]) form.append(field, item);
  return { method, body: form };
}

export const createWorkspace = () =>
  requestJson<Schemas["WorkspaceOut"]>("/api/workspaces", { method: "POST" });

export const uploadTemplate = (workspaceId: string, file: File, targetSheet: string | null) => {
  const query = targetSheet ? `?target_sheet=${encodeURIComponent(targetSheet)}` : "";
  return requestJson<TemplateSummary>(
    `/api/workspaces/${workspaceId}/template${query}`,
    upload("PUT", file, "file"),
  );
};

export const getTemplate = (workspaceId: string, targetSheet: string | null) => {
  const query = targetSheet ? `?target_sheet=${encodeURIComponent(targetSheet)}` : "";
  return requestJson<TemplateSummary>(`/api/workspaces/${workspaceId}/template${query}`);
};

export const uploadPhotosZip = (workspaceId: string, file: File) =>
  requestJson<ZipOut>(`/api/workspaces/${workspaceId}/photos/zip`, upload("POST", file, "file"));

export const uploadSectionPhotos = (workspaceId: string, sectionId: string, files: File[]) =>
  requestJson<UploadOut>(
    `/api/workspaces/${workspaceId}/photos/${encodeURIComponent(sectionId)}`,
    upload("POST", files, "files"),
  );

export const getPhotoCounts = (workspaceId: string) =>
  requestJson<Schemas["PhotoCountsOut"]>(`/api/workspaces/${workspaceId}/photos`);

export const validateReport = (workspaceId: string, config: ReportConfig) =>
  requestJson<ValidationOut>(`/api/workspaces/${workspaceId}/validate`, json(config));

export const createJob = (workspaceId: string, config: ReportConfig) =>
  requestJson<JobOut>("/api/jobs", json({ workspace_id: workspaceId, config }));

export const getJob = (jobId: string) => requestJson<JobOut>(`/api/jobs/${jobId}`);
