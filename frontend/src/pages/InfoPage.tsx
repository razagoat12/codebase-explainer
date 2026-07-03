import { Link, useLocation } from 'react-router-dom';

type Section = { heading: string; body: string };
type PageContent = { title: string; tagline: string; sections: Section[]; comingSoon?: boolean };

const PAGES: Record<string, PageContent> = {
  product: {
    title: 'Product',
    tagline: 'One pipeline, five agents, zero guesswork.',
    sections: [
      {
        heading: 'Difficulty assessment',
        body: 'Every analysis starts by classifying your codebase as Beginner, Intermediate, or Advanced, so the explanation is pitched at the right level instead of a one-size-fits-all summary.',
      },
      {
        heading: 'Plain-language explanation',
        body: 'A mentor-style walkthrough of what the code does, how the modules relate, and where the important decisions live — written for the difficulty level detected.',
      },
      {
        heading: 'Phased plan, diagram & security audit',
        body: 'You also get an MVP → Phase 1 → Phase 2 improvement plan, a Mermaid architecture diagram, and an automated scan for secrets, injection risks, and weak auth patterns.',
      },
    ],
  },
  docs: {
    title: 'Docs',
    tagline: 'Everything you need to run your first analysis.',
    sections: [
      {
        heading: 'Quick start',
        body: 'Create an account, sign in, choose Local Path or GitHub URL on the home page, and submit. Results appear on your dashboard within a minute for most repositories.',
      },
      {
        heading: 'API access',
        body: 'The same REST API that powers this site is fully documented via OpenAPI on the backend itself (the interactive schema lives at the API host’s own /docs route, separate from this marketing site). Authenticate with your JWT bearer token and call POST /analyze/local or POST /analyze/github directly.',
      },
      {
        heading: 'Limits',
        body: 'Free accounts include 10 analyses per month. Files over 500 KB are skipped and total ingested content is capped at 2 MB per analysis to keep results fast.',
      },
      {
        heading: 'Authentication',
        body: 'Register with an email and password (min. 8 characters, bcrypt-hashed). Log in to receive a JWT bearer token, valid for 24 hours. Send it as Authorization: Bearer <token> on every /analyze and /auth/me request — no cookies, no sessions to manage.',
      },
      {
        heading: 'Understanding your results',
        body: 'Each analysis returns: a difficulty level with a one-line reason, a plain-language explanation, a phased MVP → Phase 1 → Phase 2 plan, a Mermaid architecture diagram, and a security report with a risk_level and a findings[] list (severity, category, file, issue, and fix per finding).',
      },
    ],
  },
  customers: {
    title: 'Customers',
    tagline: 'Built for the moments code changes hands.',
    sections: [
      {
        heading: 'Onboarding engineers',
        body: 'New hires use the explanation and diagram to get productive in an unfamiliar repository in hours instead of weeks.',
      },
      {
        heading: 'Students & self-taught developers',
        body: 'Learners point it at open-source projects to understand real-world architecture at a level matched to their experience.',
      },
      {
        heading: 'Agencies & freelancers',
        body: 'Inherited a client codebase? Get a difficulty read, a security pass, and a phased improvement plan before you quote the work.',
      },
    ],
  },
  resources: {
    title: 'Resources',
    tagline: 'Learn more about how analyses work.',
    sections: [
      {
        heading: 'How the pipeline works',
        body: 'Five sequential agents — Difficulty Assessor, Explainer, Planner, Diagram, and Security Auditor — each receive your file tree and code snippets and produce one section of the final report.',
      },
      {
        heading: 'Caching',
        body: 'Identical code produces identical results, so repeated analyses of the same content are served instantly from cache and do not count differently against your quota.',
      },
      {
        heading: 'Privacy & data handling',
        body: 'Raw file contents are processed in memory and never persisted. See the Privacy Policy for the full details of what we store.',
      },
    ],
  },
  partners: {
    title: 'Partners',
    tagline: 'Powered by best-in-class infrastructure.',
    sections: [
      {
        heading: 'LLM inference',
        body: 'Analyses run on high-throughput LLM inference providers, keeping most reports under a minute end-to-end.',
      },
      {
        heading: 'Open standards',
        body: 'Diagrams are standard Mermaid, reports are plain Markdown, and the API is documented OpenAPI — nothing is locked in.',
      },
      {
        heading: 'Want to integrate?',
        body: 'If you would like to embed codebase explanations in your own product or workflow, reach out — the REST API is designed to be integrated.',
      },
    ],
  },
  pricing: {
    title: 'Pricing',
    tagline: 'Simple plans are on the way.',
    comingSoon: true,
    sections: [
      {
        heading: 'Free while in beta',
        body: 'Every account currently includes 10 analyses per month at no cost — the full pipeline: explanation, plan, diagram, and security audit.',
      },
      {
        heading: 'Paid tiers — coming soon',
        body: 'Higher quotas, private GitHub repositories, team workspaces, and priority processing are planned. Pricing will be announced here when they launch.',
      },
    ],
  },
};

export function InfoPage() {
  const slug = useLocation().pathname.replace(/^\//, '');
  const page = PAGES[slug] || PAGES.product;

  return (
    <div className="min-h-screen bg-neutral-950 px-6 py-16">
      <div className="mx-auto max-w-2xl">
        <Link
          to="/"
          className="mb-8 block font-mono text-sm text-neutral-500 transition hover:text-neutral-300"
        >
          ← Back
        </Link>

        <div className="mb-10">
          <h1 className="font-mono text-3xl font-bold tracking-tight text-white">
            &gt; {page.title}
          </h1>
          <p className="mt-2 text-neutral-400">{page.tagline}</p>
          {page.comingSoon && (
            <span className="mt-4 inline-flex items-center gap-2 rounded-full border border-yellow-900 bg-yellow-950/60 px-3 py-1 font-mono text-xs text-yellow-400">
              <span className="h-1.5 w-1.5 rounded-full bg-yellow-400" />
              Coming soon
            </span>
          )}
        </div>

        <div className="space-y-4">
          {page.sections.map((s) => (
            <div
              key={s.heading}
              className="rounded-xl border border-neutral-800 bg-white/5 p-6 transition hover:border-neutral-600"
            >
              <h2 className="mb-2 font-mono text-sm font-semibold text-white">{s.heading}</h2>
              <p className="text-sm leading-relaxed text-neutral-400">{s.body}</p>
            </div>
          ))}
        </div>

        <p className="mt-10 text-center text-xs text-neutral-600">
          Questions?{' '}
          <Link to="/privacy" className="underline transition hover:text-neutral-400">
            Read our Privacy Policy
          </Link>
        </p>
      </div>
    </div>
  );
}
