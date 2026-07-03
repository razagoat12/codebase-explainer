import { Link } from 'react-router-dom';

const SECTIONS = [
  {
    heading: '1. Information we collect',
    paragraphs: [
      'Account information. When you register we collect your email address and a password. Passwords are hashed with bcrypt before storage; we never store or see your plaintext password.',
      'Analysis metadata. For each analysis we store the directory path or repository URL you submitted, the analysis status, timestamps, a cryptographic hash of the analyzed content (used for caching), and the generated outputs: the difficulty assessment, explanation, phased plan, architecture diagram, and security findings.',
      'Usage data. We track how many analyses you run each month to enforce plan quotas, and we log IP addresses transiently for rate limiting and abuse prevention.',
    ],
  },
  {
    heading: '2. Your source code',
    paragraphs: [
      'Raw file contents are read into memory only for the duration of an analysis and are not written to our database or to disk. What persists is the generated report about your code and a one-way content hash — the hash cannot be reversed to reconstruct your code.',
      'To generate an analysis, selected file snippets (truncated and size-capped) are transmitted to our large-language-model inference provider over an encrypted connection. These sub-processors are contractually restricted from using API-submitted content to train their models, per their published API data-use policies.',
      'We recommend not submitting codebases containing production secrets. The built-in security audit is designed to help you find such secrets, but the safest secret is one that never leaves your machine.',
    ],
  },
  {
    heading: '3. How we use your information',
    paragraphs: [
      'We use your information solely to provide the service: authenticating you, running analyses you request, showing your history and results, enforcing quotas, preventing abuse, and communicating essential service updates. We do not sell your personal information, and we do not use your code or reports for advertising or model training.',
    ],
  },
  {
    heading: '4. Cookies and local storage',
    paragraphs: [
      'We do not use tracking cookies. After you sign in, a JSON Web Token is stored in your browser’s local storage to keep you authenticated; it is removed when you log out. Tokens expire automatically (24 hours by default).',
    ],
  },
  {
    heading: '5. Data sharing and sub-processors',
    paragraphs: [
      'We share data with third parties only as needed to operate the service: an LLM inference provider (receives code snippets during analysis), and hosting infrastructure (stores the database described above). If you analyze a public GitHub repository, we fetch its contents from GitHub on your behalf. We may also disclose information if required by law or to protect the rights, safety, or integrity of the service.',
    ],
  },
  {
    heading: '6. Data retention and deletion',
    paragraphs: [
      'Account data and analysis history are retained while your account is active. You may request deletion of your account at any time, which removes your account record and all associated analyses from the live database within 30 days. Backup copies, where they exist, are purged on their normal rotation cycle.',
    ],
  },
  {
    heading: '7. Security',
    paragraphs: [
      'We protect your data with industry-standard measures: bcrypt password hashing, short-lived signed JWTs, TLS encryption in transit, strict input validation, per-user access controls on every analysis record, and rate limiting. No method of transmission or storage is 100% secure, but we work to protect your information against unauthorized access, alteration, or destruction.',
    ],
  },
  {
    heading: '8. Your rights',
    paragraphs: [
      'Depending on where you live (including under the EU/UK GDPR and the California Consumer Privacy Act), you may have the right to access, correct, export, or delete your personal information, to object to or restrict certain processing, and to lodge a complaint with a supervisory authority. To exercise any of these rights, contact us using the details below; we will respond within 30 days.',
    ],
  },
  {
    heading: '9. Children’s privacy',
    paragraphs: [
      'The service is not directed to children under 13 (or the equivalent minimum age in your jurisdiction), and we do not knowingly collect personal information from them. If you believe a child has provided us personal information, contact us and we will delete it.',
    ],
  },
  {
    heading: '10. International transfers',
    paragraphs: [
      'Our infrastructure and sub-processors may be located in countries other than your own. Where data is transferred internationally, we rely on appropriate safeguards such as standard contractual clauses offered by our providers.',
    ],
  },
  {
    heading: '11. Changes to this policy',
    paragraphs: [
      'We may update this policy as the service evolves. Material changes will be announced on this page with an updated effective date, and where appropriate, by email. Continued use of the service after changes take effect constitutes acceptance of the revised policy.',
    ],
  },
  {
    heading: '12. Contact',
    paragraphs: [
      'For privacy questions, data requests, or complaints, contact the data controller at privacy@codebase-explainer.app.',
    ],
  },
];

export function PrivacyPage() {
  return (
    <div className="min-h-screen bg-neutral-950 px-6 py-16">
      <div className="mx-auto max-w-2xl">
        <Link
          to="/"
          className="mb-8 block font-mono text-sm text-neutral-500 transition hover:text-neutral-300"
        >
          ← Back
        </Link>

        <h1 className="font-mono text-3xl font-bold tracking-tight text-white">
          &gt; Privacy Policy
        </h1>
        <p className="mt-2 font-mono text-xs text-neutral-500">Effective date: July 3, 2026</p>
        <p className="mt-4 text-sm leading-relaxed text-neutral-400">
          Codebase Explainer (&ldquo;we&rdquo;, &ldquo;us&rdquo;, the &ldquo;service&rdquo;)
          analyzes source code you submit and returns AI-generated explanations, plans, diagrams,
          and security findings. This policy explains what we collect, why, and the choices you
          have. The short version: we keep as little as possible, your raw code is never stored,
          and we don&rsquo;t sell anything about you.
        </p>

        <div className="mt-10 space-y-8">
          {SECTIONS.map((s) => (
            <section key={s.heading}>
              <h2 className="mb-3 font-mono text-sm font-semibold text-white">{s.heading}</h2>
              <div className="space-y-3">
                {s.paragraphs.map((p, i) => (
                  <p key={i} className="text-sm leading-relaxed text-neutral-400">
                    {p}
                  </p>
                ))}
              </div>
            </section>
          ))}
        </div>
      </div>
    </div>
  );
}
