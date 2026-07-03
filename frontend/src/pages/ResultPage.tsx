import { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { marked } from 'marked';
import mermaid from 'mermaid';
import { ShieldAlert } from 'lucide-react';
import { api, getToken, type AnalysisResult } from '@/lib/api';

mermaid.initialize({ startOnLoad: false, theme: 'neutral' });

const STATUS_BADGE: Record<string, string> = {
  done: 'bg-green-100 text-green-700',
  processing: 'bg-blue-100 text-blue-700',
  pending: 'bg-yellow-100 text-yellow-700',
  error: 'bg-red-100 text-red-600',
};

const RISK_BADGE: Record<string, string> = {
  Critical: 'bg-red-100 text-red-700',
  High: 'bg-orange-100 text-orange-700',
  Medium: 'bg-yellow-100 text-yellow-700',
  Low: 'bg-green-100 text-green-700',
};

const SEV_BORDER: Record<string, string> = {
  critical: 'border-red-300 bg-red-50',
  high: 'border-orange-300 bg-orange-50',
  medium: 'border-yellow-300 bg-yellow-50',
  low: 'border-gray-200 bg-gray-50',
};

const POLL_MESSAGES = [
  'Analysing your codebase…',
  'Running difficulty assessment…',
  'Generating explanation…',
  'Building your plan…',
  'Almost done…',
];

type TabName = 'explanation' | 'plan' | 'diagram' | 'security';

function DiagramView({ code }: { code: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setFailed(false);

    mermaid
      .render(`diagram-${Date.now()}`, code)
      .then(({ svg }) => {
        if (!cancelled && containerRef.current) {
          containerRef.current.innerHTML = svg;
        }
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });

    return () => {
      cancelled = true;
    };
  }, [code]);

  if (failed) {
    return (
      <pre className="mt-4 overflow-x-auto rounded-lg bg-gray-50 p-4 text-xs text-gray-500">
        {code}
      </pre>
    );
  }

  return <div ref={containerRef} className="overflow-x-auto" />;
}

export function ResultPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<AnalysisResult | null>(null);
  const [pollMsg, setPollMsg] = useState(POLL_MESSAGES[0]);
  const [activeTab, setActiveTab] = useState<TabName>('explanation');
  const [failedToLoad, setFailedToLoad] = useState(false);

  useEffect(() => {
    if (!id) {
      navigate('/');
      return;
    }
    if (!getToken()) {
      navigate('/login');
      return;
    }

    let cancelled = false;
    let attempts = 0;

    async function poll() {
      while (!cancelled) {
        try {
          const result = await api.getAnalysis(id!);
          if (cancelled) return;
          setData(result);

          if (result.status === 'done' || result.status === 'error') return;

          setPollMsg(POLL_MESSAGES[Math.min(attempts, POLL_MESSAGES.length - 1)]);
        } catch {
          if (!cancelled) setFailedToLoad(true);
          return;
        }

        attempts++;
        await new Promise((r) => setTimeout(r, attempts === 1 ? 2000 : 4000));
      }
    }

    poll();
    return () => {
      cancelled = true;
    };
  }, [id, navigate]);

  useEffect(() => {
    if (failedToLoad) navigate('/');
  }, [failedToLoad, navigate]);

  if (failedToLoad) return null;

  const isPolling = data && data.status !== 'done' && data.status !== 'error';
  const isDone = data?.status === 'done';
  const isError = data?.status === 'error';

  return (
    <div className="min-h-screen p-6">
      <div className="mx-auto max-w-3xl">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <button
              onClick={() => navigate('/dashboard')}
              className="mb-1 block cursor-pointer text-sm text-gray-400 hover:text-gray-600"
            >
              ← My Analyses
            </button>
            <h1 className="text-2xl font-bold text-gray-800">
              {data?.source_type === 'github' ? 'GitHub Analysis' : 'Local Analysis'}
            </h1>
          </div>
        </div>

        {data && (
          <div className="mb-6 rounded-2xl border border-gray-100 bg-white p-5 shadow-sm">
            <div className="flex flex-wrap items-center gap-3">
              <span
                className={`rounded-full px-3 py-1 text-xs font-semibold ${
                  STATUS_BADGE[data.status] || 'bg-gray-100 text-gray-600'
                }`}
              >
                {data.status}
              </span>
              {data.difficulty && (
                <span className="rounded-full bg-purple-100 px-3 py-1 text-xs font-semibold text-purple-700">
                  {data.difficulty}
                </span>
              )}
              {data.primary_language && (
                <span className="rounded-full bg-blue-100 px-3 py-1 text-xs font-semibold text-blue-700">
                  {data.primary_language}
                </span>
              )}
              {data.security && (
                <span
                  className={`flex items-center gap-1 rounded-full px-3 py-1 text-xs font-semibold ${
                    RISK_BADGE[data.security.risk_level] || 'bg-gray-100 text-gray-600'
                  }`}
                >
                  <ShieldAlert className="h-3 w-3" /> {data.security.risk_level} Risk
                </span>
              )}
              {data.served_from_cache && (
                <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-700">
                  ⚡ Cached
                </span>
              )}
            </div>
            <p className="mt-3 truncate text-sm text-gray-500">{data.directory_path}</p>
            {data.difficulty_reason && (
              <p className="mt-1 text-sm text-gray-500">{data.difficulty_reason}</p>
            )}
            {data.frameworks && data.frameworks.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-2">
                {data.frameworks.map((f) => (
                  <span
                    key={f}
                    className="rounded-full bg-gray-100 px-2.5 py-1 text-xs text-gray-600"
                  >
                    {f}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}

        {isPolling && (
          <div className="rounded-2xl border border-gray-100 bg-white p-10 text-center shadow-sm">
            <div className="mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-4 border-gray-200 border-t-gray-500" />
            <p className="font-medium text-gray-500">{pollMsg}</p>
            <p className="mt-1 text-sm text-gray-400">This takes about 30 seconds</p>
          </div>
        )}

        {isError && (
          <div className="rounded-2xl border border-red-200 bg-red-50 p-6">
            <p className="mb-1 font-semibold text-red-700">Analysis failed</p>
            <p className="text-sm text-red-600">{data?.error_message || 'Unknown error'}</p>
          </div>
        )}

        {isDone && data && (
          <div>
            <div className="mb-4 flex flex-wrap gap-2">
              {(['explanation', 'plan', 'diagram', 'security'] as TabName[])
                .filter((t) => t !== 'diagram' || data.diagram)
                .filter((t) => t !== 'security' || data.security)
                .map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    className={`cursor-pointer rounded-lg px-4 py-2 text-sm font-medium transition ${
                      activeTab === tab
                        ? 'bg-gray-800 text-white'
                        : 'bg-gray-100 text-gray-500'
                    }`}
                  >
                    {tab === 'security'
                      ? 'Security'
                      : tab.charAt(0).toUpperCase() + tab.slice(1)}
                  </button>
                ))}
            </div>

            {activeTab === 'explanation' && (
              <div
                className="prose max-w-none rounded-2xl border border-gray-100 bg-white p-7 shadow-sm"
                dangerouslySetInnerHTML={{ __html: marked.parse(data.explanation || '') as string }}
              />
            )}

            {activeTab === 'plan' && (
              <div
                className="prose max-w-none rounded-2xl border border-gray-100 bg-white p-7 shadow-sm"
                dangerouslySetInnerHTML={{ __html: marked.parse(data.plan || '') as string }}
              />
            )}

            {activeTab === 'diagram' && data.diagram && (
              <div className="rounded-2xl border border-gray-100 bg-white p-7 shadow-sm">
                <DiagramView code={data.diagram} />
              </div>
            )}

            {activeTab === 'security' && data.security && (
              <div className="rounded-2xl border border-gray-100 bg-white p-7 shadow-sm">
                <p className="mb-5 text-gray-700">{data.security.summary}</p>
                {data.security.findings.length === 0 ? (
                  <p className="font-medium text-green-700">
                    No critical security issues detected.
                  </p>
                ) : (
                  <div className="space-y-3">
                    {data.security.findings.map((f, i) => (
                      <div
                        key={i}
                        className={`rounded-r-lg border-l-4 p-4 ${
                          SEV_BORDER[f.severity] || 'border-gray-200 bg-gray-50'
                        }`}
                      >
                        <div className="mb-1 flex items-start justify-between">
                          <span className="text-xs font-semibold uppercase text-gray-600">
                            {f.severity} · {f.category}
                          </span>
                          <span className="font-mono text-xs text-gray-500">{f.file}</span>
                        </div>
                        <p className="mb-1 text-sm font-medium text-gray-800">{f.issue}</p>
                        <p className="text-sm text-gray-600">
                          <span className="font-semibold">Fix:</span> {f.fix}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
