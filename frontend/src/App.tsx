import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { MotionConfig } from 'motion/react';
import { Layout } from '@/components/Layout';
import { HomePage } from '@/pages/HomePage';
import { DashboardPage } from '@/pages/DashboardPage';

const ResultPage = lazy(() =>
  import('@/pages/ResultPage').then((m) => ({ default: m.ResultPage }))
);
const LoginPage = lazy(() =>
  import('@/pages/LoginPage').then((m) => ({ default: m.LoginPage }))
);
const InfoPage = lazy(() =>
  import('@/pages/InfoPage').then((m) => ({ default: m.InfoPage }))
);
const PrivacyPage = lazy(() =>
  import('@/pages/PrivacyPage').then((m) => ({ default: m.PrivacyPage }))
);
const TermsPage = lazy(() =>
  import('@/pages/TermsPage').then((m) => ({ default: m.TermsPage }))
);

const INFO_SLUGS = ['product', 'docs', 'customers', 'resources', 'partners', 'pricing'];

const lazyFallback = (
  <div className="flex min-h-screen items-center justify-center bg-black text-gray-400">
    Loading…
  </div>
);

function App() {
  return (
    <MotionConfig reducedMotion="user">
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<HomePage />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route
              path="/login"
              element={
                <Suspense fallback={lazyFallback}>
                  <LoginPage />
                </Suspense>
              }
            />
            <Route
              path="/result/:id"
              element={
                <Suspense fallback={lazyFallback}>
                  <ResultPage />
                </Suspense>
              }
            />
            {INFO_SLUGS.map((slug) => (
              <Route
                key={slug}
                path={`/${slug}`}
                element={
                  <Suspense fallback={lazyFallback}>
                    <InfoPage />
                  </Suspense>
                }
              />
            ))}
            <Route
              path="/privacy"
              element={
                <Suspense fallback={lazyFallback}>
                  <PrivacyPage />
                </Suspense>
              }
            />
            <Route
              path="/terms"
              element={
                <Suspense fallback={lazyFallback}>
                  <TermsPage />
                </Suspense>
              }
            />
          </Route>
        </Routes>
      </BrowserRouter>
    </MotionConfig>
  );
}

export default App;
