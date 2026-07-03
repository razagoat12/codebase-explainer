export type AuthResponse = { user_id: string; email: string };
export type TokenResponse = { access_token: string; token_type: string };
export type MeResponse = {
  user_id: string;
  email: string;
  plan_tier: string;
  monthly_usage: number;
  monthly_quota: number;
};

export type AnalysisSummary = {
  id: string;
  status: 'pending' | 'processing' | 'done' | 'error';
  directory_path: string;
  source_type: 'local' | 'github';
  created_at: string;
};

export type SecurityFinding = {
  severity: string;
  category: string;
  file: string;
  issue: string;
  fix: string;
};

export type SecurityReport = {
  summary: string;
  risk_level: string;
  findings: SecurityFinding[];
};

export type AnalysisResult = AnalysisSummary & {
  difficulty: string | null;
  difficulty_reason: string | null;
  primary_language: string | null;
  frameworks: string[] | null;
  explanation: string | null;
  plan: string | null;
  diagram: string | null;
  security: SecurityReport | null;
  served_from_cache: boolean;
  error_message: string | null;
  completed_at: string | null;
};

class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

const AUTH_CHANGED_EVENT = 'auth-changed';

export function getToken(): string | null {
  return localStorage.getItem('token');
}

export function setToken(token: string): void {
  localStorage.setItem('token', token);
  window.dispatchEvent(new Event(AUTH_CHANGED_EVENT));
}

export function clearToken(): void {
  localStorage.removeItem('token');
  window.dispatchEvent(new Event(AUTH_CHANGED_EVENT));
}

/** Reactive login state — updates immediately on setToken/clearToken, even
 * when React Router doesn't remount the component (e.g. same-route nav). */
export function subscribeAuthChanged(callback: () => void): () => void {
  window.addEventListener(AUTH_CHANGED_EVENT, callback);
  return () => window.removeEventListener(AUTH_CHANGED_EVENT, callback);
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers as Record<string, string> | undefined),
  };

  const res = await fetch(path, { ...options, headers });
  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    throw new ApiError(data.detail || 'Something went wrong', res.status);
  }

  return data as T;
}

export const api = {
  register: (email: string, password: string) =>
    request<AuthResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  login: (email: string, password: string) =>
    request<TokenResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  me: () => request<MeResponse>('/auth/me'),

  analyzeLocal: (directoryPath: string) =>
    request<AnalysisSummary>('/analyze/local', {
      method: 'POST',
      body: JSON.stringify({ directory_path: directoryPath }),
    }),

  analyzeGithub: (repoUrl: string) =>
    request<AnalysisSummary>('/analyze/github', {
      method: 'POST',
      body: JSON.stringify({ repo_url: repoUrl }),
    }),

  history: () => request<AnalysisSummary[]>('/analyze/history'),

  getAnalysis: (id: string) => request<AnalysisResult>(`/analyze/${id}`),
};

export { ApiError };
