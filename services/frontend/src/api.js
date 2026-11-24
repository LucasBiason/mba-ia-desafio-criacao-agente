import { useEffect, useState } from "react";

export class ApiError extends Error {
  constructor(status, detail) {
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((item) => item.msg).join(" · ")
          : detail?.message;
    super(
      message ||
        (status >= 500
          ? "Serviço temporariamente indisponível."
          : "A operação não pôde ser concluída."),
    );
    this.status = status;
    this.code = detail?.code;
  }
}

export async function request(
  path,
  { body, token, method = "GET", signal } = {},
) {
  const headers = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (token) headers.Authorization = "Bearer " + token;
  let response;
  try {
    response = await fetch(path, {
      method,
      headers,
      signal,
      cache: "no-store",
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (error) {
    if (error.name === "AbortError") throw error;
    throw new Error(
      "Não foi possível conectar. Verifique a conexão e tente de novo.",
      { cause: error },
    );
  }
  const data = response.headers.get("content-type")?.includes("json")
    ? await response.json()
    : null;
  if (!response.ok) throw new ApiError(response.status, data?.detail);
  return data;
}

export function useQuery(api, path) {
  const [state, setState] = useState({});
  const [revision, setRevision] = useState(0);

  useEffect(() => {
    if (!path) return;
    const controller = new AbortController();
    api(path, { signal: controller.signal })
      .then((data) => {
        if (!controller.signal.aborted) setState({ path, revision, data });
      })
      .catch((error) => {
        if (!controller.signal.aborted) setState({ path, revision, error });
      });
    return () => controller.abort();
  }, [api, path, revision]);

  const current = state.path === path ? state : {};
  return {
    ...current,
    loading: Boolean(path) && current.revision !== revision,
    refresh: () => setRevision((value) => value + 1),
  };
}

export const scoped = (path, apartment) =>
  apartment ? path + "?apartment=" + encodeURIComponent(apartment) : null;
