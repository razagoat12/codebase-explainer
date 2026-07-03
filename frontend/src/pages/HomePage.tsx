import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'motion/react';
import { ArrowRight, ChevronUp, Folder, Gauge, GitBranch } from 'lucide-react';
import {
  Accordion,
  AccordionItem,
  AccordionTrigger,
  AccordionContent,
} from '@/components/core/accordion';
import { Web3Hero } from '@/components/Web3Hero';
import { HowItWorksDiagram } from '@/components/HowItWorksDiagram';
import { FloatingPaths } from '@/components/FloatingPaths';
import { api, ApiError, type MeResponse } from '@/lib/api';
import { useAuthState } from '@/lib/useAuthState';

const TITLE = 'Codebase Explainer';

function useTilt() {
  const [tilt, setTilt] = useState({ x: 0, y: 0 });
  const reducedMotion =
    typeof window !== 'undefined' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function onMouseMove(e: React.MouseEvent<HTMLDivElement>) {
    if (reducedMotion) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const px = (e.clientX - rect.left) / rect.width - 0.5;
    const py = (e.clientY - rect.top) / rect.height - 0.5;
    setTilt({ x: py * -6, y: px * 6 });
  }
  function onMouseLeave() {
    setTilt({ x: 0, y: 0 });
  }

  return {
    onMouseMove,
    onMouseLeave,
    style: {
      transform: `perspective(1200px) rotateX(${tilt.x}deg) rotateY(${tilt.y}deg)`,
      transition: 'transform 200ms ease-out',
    },
  };
}

const FAQ_ITEMS = [
  {
    value: 'what-can-i-analyze',
    title: 'What can I analyze?',
    body: 'A local directory on your machine or any public GitHub repository. Just provide the path or the repo URL and we take it from there.',
  },
  {
    value: 'difficulty-assessment',
    title: 'How does difficulty assessment work?',
    body: "Our AI pipeline scans your codebase's structure, languages, and patterns to classify it as Beginner, Intermediate, or Advanced, then generates a plain-language explanation tailored to that level.",
  },
  {
    value: 'code-storage',
    title: 'Is my code stored?',
    body: 'Only metadata and the generated analysis (explanation, plan, diagrams) are stored — enough to power caching and your history. Raw file contents are processed in memory during analysis and are not persisted.',
  },
  {
    value: 'security-audit',
    title: "What's the security audit?",
    body: 'Every analysis includes an automated pass for hardcoded secrets, injection risks, exposed environment variables, and other common vulnerabilities, with a risk level and suggested fixes.',
  },
];

export function HomePage() {
  const navigate = useNavigate();
  const loggedIn = useAuthState();
  const tilt = useTilt();

  const [usage, setUsage] = useState<MeResponse | null>(null);

  const [source, setSource] = useState<'local' | 'github'>('local');
  const [sourceValue, setSourceValue] = useState('');
  const [submitError, setSubmitError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (loggedIn) {
      api.me().then(setUsage).catch(() => {});
    } else {
      setUsage(null);
    }
  }, [loggedIn]);

  async function handleAnalysisSubmit(e: React.FormEvent) {
    e.preventDefault();
    const val = sourceValue.trim();
    if (!val) return;

    setSubmitError('');
    setSubmitting(true);

    try {
      const result =
        source === 'github'
          ? await api.analyzeGithub(val)
          : await api.analyzeLocal(val);
      navigate(`/result/${result.id}`);
    } catch (err) {
      setSubmitError(
        err instanceof ApiError ? err.message : 'Error submitting analysis'
      );
    } finally {
      setSubmitting(false);
    }
  }

  if (!loggedIn) {
    return (
      <div className="bg-black">
        <Web3Hero onGetStarted={() => navigate('/login')} />

        <div id="how-it-works">
          <HowItWorksDiagram onCtaClick={() => navigate('/login')} />
        </div>

        <div id="faq" className="bg-black px-6 pb-10">
          <div className="mx-auto max-w-md rounded-2xl border border-neutral-800 bg-[#121212] p-6">
            <h2 className="mb-2 font-semibold text-white">FAQ</h2>
            <Accordion
              className="flex w-full flex-col divide-y divide-neutral-800"
              transition={{ duration: 0.2, ease: 'easeInOut' }}
            >
              {FAQ_ITEMS.map((item) => (
                <AccordionItem key={item.value} value={item.value} className="py-2">
                  <AccordionTrigger className="w-full cursor-pointer text-left text-white">
                    <div className="flex items-center justify-between">
                      <div className="text-sm font-medium">{item.title}</div>
                      <ChevronUp className="h-4 w-4 text-neutral-400 transition-transform duration-200 group-data-expanded:-rotate-180" />
                    </div>
                  </AccordionTrigger>
                  <AccordionContent>
                    <p className="pt-1 text-sm text-neutral-400">{item.body}</p>
                  </AccordionContent>
                </AccordionItem>
              ))}
            </Accordion>
          </div>
        </div>

        <footer className="border-t border-neutral-900 bg-black px-6 py-12">
          <div className="mx-auto grid max-w-5xl grid-cols-2 gap-8 sm:grid-cols-4">
            <div>
              <p className="mb-3 font-mono text-xs font-semibold uppercase tracking-wide text-neutral-600">
                Product
              </p>
              <ul className="space-y-2 text-sm text-neutral-400">
                <li>
                  <Link to="/product" className="transition hover:text-white">
                    Overview
                  </Link>
                </li>
                <li>
                  <Link to="/pricing" className="transition hover:text-white">
                    Pricing
                  </Link>
                </li>
                <li>
                  <Link to="/docs" className="transition hover:text-white">
                    Docs
                  </Link>
                </li>
              </ul>
            </div>
            <div>
              <p className="mb-3 font-mono text-xs font-semibold uppercase tracking-wide text-neutral-600">
                Company
              </p>
              <ul className="space-y-2 text-sm text-neutral-400">
                <li>
                  <Link to="/customers" className="transition hover:text-white">
                    Customers
                  </Link>
                </li>
                <li>
                  <Link to="/partners" className="transition hover:text-white">
                    Partners
                  </Link>
                </li>
              </ul>
            </div>
            <div>
              <p className="mb-3 font-mono text-xs font-semibold uppercase tracking-wide text-neutral-600">
                Learn
              </p>
              <ul className="space-y-2 text-sm text-neutral-400">
                <li>
                  <Link to="/resources" className="transition hover:text-white">
                    Resources
                  </Link>
                </li>
              </ul>
            </div>
            <div>
              <p className="mb-3 font-mono text-xs font-semibold uppercase tracking-wide text-neutral-600">
                Legal
              </p>
              <ul className="space-y-2 text-sm text-neutral-400">
                <li>
                  <Link to="/privacy" className="transition hover:text-white">
                    Privacy Policy
                  </Link>
                </li>
              </ul>
            </div>
          </div>
          <div className="mx-auto mt-10 flex max-w-5xl items-center justify-between border-t border-neutral-900 pt-6 text-xs text-neutral-600">
            <span>© {new Date().getFullYear()} Codebase Explainer</span>
            <span>Built on FastAPI, React &amp; NVIDIA</span>
          </div>
        </footer>
      </div>
    );
  }

  return (
    <div className="relative flex min-h-screen w-full flex-col items-center justify-center overflow-hidden bg-neutral-950 p-6">
      <div className="absolute inset-0">
        <FloatingPaths position={1} />
        <FloatingPaths position={-1} />
      </div>

      <div className="relative z-10 w-full max-w-md">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 1.2 }}
          className="mb-8 flex flex-col items-center gap-4 text-center"
        >
          <h1 className="font-mono text-3xl font-bold tracking-tighter text-white sm:text-4xl">
            {TITLE.split(' ').map((word, wi) => (
              <span key={wi} className="mr-3 inline-block last:mr-0">
                {word.split('').map((letter, li) => (
                  <motion.span
                    key={`${wi}-${li}`}
                    initial={{ y: 40, opacity: 0 }}
                    animate={{ y: 0, opacity: 1 }}
                    transition={{
                      delay: wi * 0.1 + li * 0.03,
                      type: 'spring',
                      stiffness: 150,
                      damping: 25,
                    }}
                    className="inline-block bg-gradient-to-r from-white to-white/80 bg-clip-text text-transparent"
                  >
                    {letter}
                  </motion.span>
                ))}
              </span>
            ))}
          </h1>

          {usage && (
            <span className="inline-flex items-center gap-2 rounded-full border border-neutral-800 px-3 py-1 font-mono text-xs text-neutral-400">
              <Gauge className="h-3.5 w-3.5" />
              {usage.plan_tier.toUpperCase()} · {usage.monthly_usage}/{usage.monthly_quota}
            </span>
          )}
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.3 }}
          onMouseMove={tilt.onMouseMove}
          onMouseLeave={tilt.onMouseLeave}
          style={tilt.style}
          className="group relative rounded-2xl bg-gradient-to-b from-white/10 to-black/10 p-px shadow-2xl backdrop-blur-lg"
        >
          <div className="rounded-[calc(1rem-1px)] bg-black/80 p-7 backdrop-blur-md">
            <h2 className="font-mono text-base font-semibold text-white">
              &gt; Understand your code
            </h2>
            <p className="mb-6 mt-1 text-xs text-neutral-500">
              Three steps from source to plain-language explanation.
            </p>

            <ol className="space-y-5">
              <li className="flex gap-3">
                <span
                  className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full border font-mono text-xs transition ${
                    source
                      ? 'border-white bg-white text-black'
                      : 'border-neutral-700 text-neutral-500'
                  }`}
                >
                  1
                </span>
                <div className="min-w-0 flex-1">
                  <p className="mb-2 font-mono text-xs font-medium text-neutral-300">
                    Choose a source
                  </p>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => setSource('local')}
                      className={`flex flex-1 cursor-pointer items-center justify-center gap-2 rounded-lg py-2 font-mono text-xs font-medium transition ${
                        source === 'local'
                          ? 'bg-white text-black'
                          : 'bg-white/5 text-neutral-400 hover:bg-white/10'
                      }`}
                    >
                      <Folder className="h-3.5 w-3.5" />
                      Local Path
                    </button>
                    <button
                      type="button"
                      onClick={() => setSource('github')}
                      className={`flex flex-1 cursor-pointer items-center justify-center gap-2 rounded-lg py-2 font-mono text-xs font-medium transition ${
                        source === 'github'
                          ? 'bg-white text-black'
                          : 'bg-white/5 text-neutral-400 hover:bg-white/10'
                      }`}
                    >
                      <GitBranch className="h-3.5 w-3.5" />
                      GitHub URL
                    </button>
                  </div>
                </div>
              </li>

              <li className="flex gap-3">
                <span
                  className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full border font-mono text-xs transition ${
                    sourceValue.trim()
                      ? 'border-white bg-white text-black'
                      : 'border-neutral-700 text-neutral-500'
                  }`}
                >
                  2
                </span>
                <div className="min-w-0 flex-1">
                  <p className="mb-2 font-mono text-xs font-medium text-neutral-300">
                    {source === 'local'
                      ? 'Point us at a directory'
                      : 'Paste a public repo URL'}
                  </p>
                  <form onSubmit={handleAnalysisSubmit}>
                    <input
                      type="text"
                      value={sourceValue}
                      onChange={(e) => setSourceValue(e.target.value)}
                      placeholder={
                        source === 'local'
                          ? '/Users/you/myproject'
                          : 'https://github.com/user/repo'
                      }
                      className="w-full rounded-lg border border-neutral-800 bg-black px-3.5 py-2.5 font-mono text-sm text-white outline-none placeholder:text-neutral-600 focus:border-neutral-500"
                    />
                  </form>
                </div>
              </li>

              <li className="flex gap-3">
                <span
                  className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full border font-mono text-xs transition ${
                    submitting
                      ? 'border-white bg-white text-black'
                      : 'border-neutral-700 text-neutral-500'
                  }`}
                >
                  3
                </span>
                <div className="min-w-0 flex-1">
                  <p className="mb-2 font-mono text-xs font-medium text-neutral-300">
                    Get the breakdown — difficulty, plan &amp; security
                  </p>
                  {submitError && (
                    <div className="mb-3 rounded-lg border border-red-900 bg-red-950/50 p-3 text-sm text-red-400">
                      {submitError}
                    </div>
                  )}
                  <button
                    type="button"
                    onClick={handleAnalysisSubmit}
                    disabled={submitting || !sourceValue.trim()}
                    className="flex w-full cursor-pointer items-center justify-center gap-2 rounded-lg bg-white py-2.5 text-sm font-medium text-black transition hover:bg-white/90 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    <span className="opacity-90 transition-opacity group-hover:opacity-100">
                      {submitting ? 'Analysing…' : 'Analyse'}
                    </span>
                    {!submitting && (
                      <ArrowRight className="h-4 w-4 opacity-70 transition-all duration-300 group-hover:translate-x-1 group-hover:opacity-100" />
                    )}
                  </button>
                </div>
              </li>
            </ol>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
