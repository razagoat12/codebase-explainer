import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'motion/react';
import {
  ArrowUpRight,
  CheckCircle2,
  Clock,
  Folder,
  GitBranch,
  Loader2,
  XCircle,
} from 'lucide-react';
import { api, getToken, type AnalysisSummary } from '@/lib/api';
import { HalftoneTrail } from '@/components/HalftoneTrail';

const STATUS_META: Record<
  string,
  { label: string; badge: string; icon: typeof CheckCircle2 }
> = {
  done: {
    label: 'done',
    badge: 'border-emerald-900 bg-emerald-950/60 text-emerald-400',
    icon: CheckCircle2,
  },
  processing: {
    label: 'processing',
    badge: 'border-blue-900 bg-blue-950/60 text-blue-400',
    icon: Loader2,
  },
  pending: {
    label: 'pending',
    badge: 'border-yellow-900 bg-yellow-950/60 text-yellow-400',
    icon: Clock,
  },
  error: {
    label: 'error',
    badge: 'border-red-900 bg-red-950/60 text-red-400',
    icon: XCircle,
  },
};

type Filter = 'all' | 'done' | 'processing' | 'pending' | 'error';
const FILTERS: Filter[] = ['all', 'done', 'processing', 'pending', 'error'];

function truncate(path: string) {
  return path.length > 55 ? '…' + path.slice(-52) : path;
}

export function DashboardPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [items, setItems] = useState<AnalysisSummary[]>([]);
  const [filter, setFilter] = useState<Filter>('all');

  useEffect(() => {
    if (!getToken()) {
      navigate('/login');
      return;
    }
    api
      .history()
      .then(setItems)
      .catch(() => navigate('/login'))
      .finally(() => setLoading(false));
  }, [navigate]);

  const counts = useMemo(() => {
    const c: Record<string, number> = { all: items.length };
    for (const item of items) c[item.status] = (c[item.status] ?? 0) + 1;
    return c;
  }, [items]);

  const visible = useMemo(
    () => (filter === 'all' ? items : items.filter((i) => i.status === filter)),
    [items, filter]
  );

  return (
    <div className="relative min-h-screen overflow-hidden bg-neutral-950 p-6">
      <HalftoneTrail color="#ffffff" />
      <div className="relative z-10 mx-auto max-w-2xl">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="mb-8"
        >
          <Link
            to="/"
            className="mb-1 block font-mono text-sm text-neutral-500 transition hover:text-neutral-300"
          >
            ← Back
          </Link>
          <h1 className="font-mono text-2xl font-bold tracking-tight text-white">
            &gt; My Analyses
          </h1>
          <p className="mt-1 text-sm text-neutral-500">
            Every codebase you have explained, planned, and audited.
          </p>
        </motion.div>

        {!loading && items.length > 0 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.4, delay: 0.1 }}
            className="mb-5 flex flex-wrap gap-2"
          >
            {FILTERS.map((f) => (
              <button
                key={f}
                type="button"
                onClick={() => setFilter(f)}
                className={`cursor-pointer rounded-full border px-3 py-1 font-mono text-xs transition ${
                  filter === f
                    ? 'border-white bg-white text-black'
                    : 'border-neutral-800 bg-white/5 text-neutral-400 hover:bg-white/10 hover:text-neutral-200'
                }`}
              >
                {f} ({counts[f] ?? 0})
              </button>
            ))}
          </motion.div>
        )}

        {loading && (
          <div className="space-y-3">
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className="h-20 animate-pulse rounded-xl border border-neutral-900 bg-white/5"
              />
            ))}
          </div>
        )}

        {!loading && items.length === 0 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="rounded-2xl border border-neutral-800 bg-white/5 py-16 text-center"
          >
            <p className="font-mono text-neutral-400">No analyses yet.</p>
            <Link
              to="/"
              className="mt-3 inline-flex items-center gap-1 rounded-full bg-white px-4 py-2 text-sm font-medium text-black transition hover:bg-white/90"
            >
              Start one <ArrowUpRight className="h-4 w-4" />
            </Link>
          </motion.div>
        )}

        {!loading && visible.length === 0 && items.length > 0 && (
          <div className="rounded-2xl border border-neutral-800 bg-white/5 py-12 text-center font-mono text-sm text-neutral-500">
            Nothing with status “{filter}”.
          </div>
        )}

        {!loading && visible.length > 0 && (
          <div className="space-y-3">
            {visible.map((item, idx) => {
              const SourceIcon = item.source_type === 'github' ? GitBranch : Folder;
              const meta = STATUS_META[item.status] ?? STATUS_META.pending;
              const StatusIcon = meta.icon;
              return (
                <motion.div
                  key={item.id}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3, delay: Math.min(idx * 0.05, 0.4) }}
                >
                  <Link
                    to={`/result/${item.id}`}
                    className="group block cursor-pointer rounded-xl border border-neutral-800 bg-white/5 p-5 backdrop-blur transition hover:border-neutral-600 hover:bg-white/10"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex min-w-0 items-center gap-3">
                        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-neutral-800 bg-black/40">
                          <SourceIcon className="h-4 w-4 text-neutral-400" />
                        </div>
                        <div className="min-w-0">
                          <p className="truncate font-mono text-sm font-medium text-neutral-200 transition group-hover:text-white">
                            {truncate(item.directory_path)}
                          </p>
                          <p className="mt-1 text-xs text-neutral-500">
                            {new Date(item.created_at).toLocaleString()}
                          </p>
                        </div>
                      </div>
                      <div className="flex shrink-0 items-center gap-2">
                        <span
                          className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 font-mono text-xs font-medium ${meta.badge}`}
                        >
                          <StatusIcon
                            className={`h-3 w-3 ${
                              item.status === 'processing' ? 'animate-spin' : ''
                            }`}
                          />
                          {meta.label}
                        </span>
                        <ArrowUpRight className="h-4 w-4 text-neutral-600 opacity-0 transition group-hover:translate-x-0.5 group-hover:opacity-100" />
                      </div>
                    </div>
                  </Link>
                </motion.div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
