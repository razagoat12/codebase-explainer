import { Suspense, lazy, useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api, ApiError, getToken, setToken } from '@/lib/api';
import { Turnstile } from '@/components/Turnstile';

const DotGridBackground = lazy(() =>
  import('@/components/DotGridBackground').then((m) => ({ default: m.DotGridBackground }))
);

const GoogleIcon = (
  <svg viewBox="0 0 24 24" className="h-4 w-4 shrink-0">
    <path
      fill="#4285F4"
      d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
    />
    <path
      fill="#34A853"
      d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
    />
    <path
      fill="#FBBC05"
      d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
    />
    <path
      fill="#EA4335"
      d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
    />
  </svg>
);

const GitHubIcon = (
  <svg viewBox="0 0 24 24" fill="currentColor" className="h-4 w-4 shrink-0">
    <path d="M12 2C6.477 2 2 6.477 2 12c0 4.42 2.865 8.166 6.839 9.489.5.092.682-.217.682-.482 0-.237-.008-.866-.013-1.699-2.782.603-3.369-1.34-3.369-1.34-.454-1.156-1.11-1.462-1.11-1.462-.908-.62.069-.608.069-.608 1.003.07 1.531 1.03 1.531 1.03.892 1.529 2.341 1.087 2.91.831.092-.646.35-1.086.636-1.336-2.22-.253-4.555-1.11-4.555-4.943 0-1.091.39-1.984 1.029-2.683-.103-.253-.446-1.27.098-2.647 0 0 .84-.269 2.75 1.025A9.578 9.578 0 0112 6.836c.85.004 1.705.114 2.504.336 1.909-1.294 2.747-1.025 2.747-1.025.546 1.379.203 2.394.1 2.647.64.699 1.028 1.592 1.028 2.683 0 3.842-2.339 4.687-4.566 4.935.359.309.678.919.678 1.852 0 1.336-.012 2.415-.012 2.743 0 .267.18.577.688.48C19.138 20.161 22 16.416 22 12c0-5.523-4.477-10-10-10z" />
  </svg>
);

const AppleIcon = (
  <svg viewBox="0 0 24 24" fill="currentColor" className="h-4 w-4 shrink-0">
    <path d="M17.05 20.28c-.98.95-2.05.8-3.08.35-1.09-.46-2.09-.48-3.24 0-1.44.62-2.2.44-3.06-.35C2.79 15.25 3.51 7.59 9.05 7.31c1.35.07 2.29.74 3.08.8 1.18-.04 2.26-.79 3.59-.76 1.56.04 2.88.75 3.65 1.89-3.08 1.75-2.58 5.61.35 6.75-1.01 2.37-2.39 4.39-4.29 4.29zM12.03 7.25c-.15-2.23 1.66-4.07 3.72-4.25.36 2.38-1.92 4.34-3.72 4.25z" />
  </svg>
);

const socialBtnClass =
  'mb-1.5 flex w-full cursor-not-allowed items-center justify-center gap-2 rounded-md border border-neutral-800 bg-transparent py-2.5 text-sm font-medium text-neutral-500 opacity-60';

const darkInputClass =
  'w-full rounded-md border border-neutral-700 bg-black px-3.5 py-2.5 text-sm text-white outline-none focus:border-neutral-500';

export function LoginPage() {
  const navigate = useNavigate();
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [authMsg, setAuthMsg] = useState<{ text: string; ok: boolean } | null>(null);
  const [authSubmitting, setAuthSubmitting] = useState(false);
  const [turnstileToken, setTurnstileToken] = useState<string | undefined>(undefined);
  const isLogin = authMode === 'login';
  const turnstileConfigured = Boolean(import.meta.env.VITE_TURNSTILE_SITE_KEY);

  useEffect(() => {
    if (getToken()) navigate('/');
  }, [navigate]);

  async function handleAuthSubmit(e: React.FormEvent) {
    e.preventDefault();
    setAuthMsg(null);
    setAuthSubmitting(true);
    try {
      if (authMode === 'register') {
        await api.register(email, password, turnstileToken);
        setAuthMsg({ text: 'Registered! Logging you in…', ok: true });
        const tok = await api.login(email, password);
        setToken(tok.access_token);
      } else {
        const tok = await api.login(email, password);
        setToken(tok.access_token);
      }
      navigate('/');
    } catch (err) {
      const message = err instanceof ApiError ? err.message : 'Something went wrong';
      setAuthMsg({ text: message, ok: false });
    } finally {
      setAuthSubmitting(false);
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-black p-6">
      <Suspense fallback={null}>
        <DotGridBackground />
      </Suspense>
      <div
        className="pointer-events-none absolute inset-0 z-[1]"
        style={{
          background:
            'radial-gradient(circle at center, rgba(0,0,0,0.75) 0%, rgba(0,0,0,0) 100%)',
        }}
      />

      <div className="relative z-10 flex w-full max-w-[400px] flex-col items-center rounded-xl border border-neutral-800 bg-[#121212] p-8 text-center shadow-2xl">
        <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-full border border-neutral-700 bg-neutral-900 text-base font-bold text-white">
          CB
        </div>

        <h1 className="mb-1 text-xl font-semibold tracking-tight text-white">
          {isLogin ? 'Sign in to Codebase Explainer' : 'Sign up for Codebase Explainer'}
        </h1>
        <p className="mb-4 text-sm text-neutral-400">
          {isLogin
            ? 'Understand any codebase in plain language.'
            : 'Create an account to start analysing your code.'}
        </p>

        {authMsg && (
          <div
            className={`mb-4 w-full rounded-md p-3 text-sm ${
              authMsg.ok ? 'bg-green-950 text-green-400' : 'bg-red-950 text-red-400'
            }`}
          >
            {authMsg.text}
          </div>
        )}

        <form onSubmit={handleAuthSubmit} className="flex w-full flex-col gap-2.5">
          <input
            type="email"
            required
            placeholder="name@work-email.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className={darkInputClass}
          />
          <input
            type="password"
            required
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className={darkInputClass}
          />
          {!isLogin && (
            <Turnstile
              onVerify={setTurnstileToken}
              onExpire={() => setTurnstileToken(undefined)}
            />
          )}
          <button
            type="submit"
            disabled={
              authSubmitting || (!isLogin && turnstileConfigured && !turnstileToken)
            }
            className="w-full cursor-pointer rounded-md bg-[#ededed] py-2.5 text-sm font-medium text-black transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-60"
          >
            {authSubmitting
              ? 'Please wait…'
              : isLogin
                ? 'Continue with Email'
                : 'Sign Up with Email'}
          </button>
        </form>

        <div className="my-3.5 h-px w-full bg-neutral-800" />

        <p className="mb-2 text-xs text-neutral-600">Social sign-in — coming soon</p>
        <button type="button" disabled title="Coming soon" className={socialBtnClass}>
          {GoogleIcon}
          {isLogin ? 'Continue with Google' : 'Sign up with Google'}
        </button>
        <button type="button" disabled title="Coming soon" className={socialBtnClass}>
          {GitHubIcon}
          {isLogin ? 'Continue with GitHub' : 'Sign up with GitHub'}
        </button>
        <button type="button" disabled title="Coming soon" className={`${socialBtnClass} mb-0`}>
          {AppleIcon}
          {isLogin ? 'Continue with Apple' : 'Sign up with Apple'}
        </button>

        <div className="mt-5 text-sm text-neutral-400">
          {isLogin ? "Don't have an account? " : 'Already have an account? '}
          <button
            type="button"
            onClick={() => {
              setAuthMode(isLogin ? 'register' : 'login');
              setAuthMsg(null);
            }}
            className="cursor-pointer bg-transparent p-0 font-medium text-white hover:underline"
          >
            {isLogin ? 'Sign Up' : 'Sign In'}
          </button>
        </div>

        <div className="mt-3.5 text-xs leading-relaxed text-neutral-500">
          By proceeding, you agree to creating a CodeBase account
          <br />
          subject to our{' '}
          <Link to="/terms" className="text-neutral-300 hover:underline">
            Terms of Service
          </Link>{' '}
          and{' '}
          <Link to="/privacy" className="text-neutral-300 hover:underline">
            Privacy Policy
          </Link>
          .
        </div>
      </div>
    </div>
  );
}
