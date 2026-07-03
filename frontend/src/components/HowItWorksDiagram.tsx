import { motion } from 'motion/react';
import {
  ArrowRight,
  BarChart3,
  BookOpen,
  Code2,
  ListChecks,
  Network,
  ShieldCheck,
  Zap,
} from 'lucide-react';

const COLORS = {
  background: '#0a0a0a',
  accent: '#2dd4bf',
  textPrimary: '#ffffff',
  textSecondary: '#9ca3af',
  textLabel: '#6b7280',
  cardBg: '#1a1a1a',
  borderDashed: '#2dd4bf',
} as const;

const AGENT_NODES = [
  { label: 'Difficulty', icon: BarChart3 },
  { label: 'Explanation', icon: BookOpen },
  { label: 'Plan', icon: ListChecks },
  { label: 'Diagram', icon: Network },
  { label: 'Security', icon: ShieldCheck },
  { label: 'Caching', icon: Zap },
];

function IntegrationNode({
  icon: Icon,
  label,
  className = '',
  delay = 0,
}: {
  icon: typeof BarChart3;
  label: string;
  className?: string;
  delay?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.8 }}
      whileInView={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5, delay }}
      viewport={{ once: true }}
      className={`relative flex w-20 flex-col items-center justify-center gap-2 rounded-lg border border-gray-700 bg-[#1a1a1a] py-4 ${className}`}
    >
      <Icon className="h-6 w-6" style={{ color: COLORS.accent }} />
      <span className="text-[10px] font-medium text-gray-400">{label}</span>
      <div className="absolute -top-1 -left-1 h-2 w-2 rounded-sm bg-[#2dd4bf]" />
      <div className="absolute -top-1 -right-1 h-2 w-2 rounded-sm bg-[#2dd4bf]" />
      <div className="absolute -bottom-1 -left-1 h-2 w-2 rounded-sm bg-[#2dd4bf]" />
      <div className="absolute -bottom-1 -right-1 h-2 w-2 rounded-sm bg-[#2dd4bf]" />
    </motion.div>
  );
}

export function HowItWorksDiagram({ onCtaClick }: { onCtaClick?: () => void }) {
  return (
    <section
      className="relative w-full overflow-hidden py-20 md:py-28"
      style={{ backgroundColor: COLORS.background }}
    >
      <div
        className="absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage: `repeating-linear-gradient(
            45deg,
            transparent,
            transparent 10px,
            rgba(255,255,255,0.1) 10px,
            rgba(255,255,255,0.1) 11px
          )`,
        }}
      />

      <div className="relative z-10 mx-auto max-w-7xl px-6 md:px-12">
        <div className="mb-16 flex flex-col gap-8 md:mb-24 md:flex-row md:items-start md:justify-between">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            viewport={{ once: true }}
            className="flex-1"
          >
            <span
              className="mb-4 block text-xs font-medium tracking-widest uppercase"
              style={{ color: COLORS.textLabel }}
            >
              HOW IT WORKS
            </span>
            <h2
              className="text-4xl leading-tight md:text-5xl lg:text-6xl"
              style={{ color: COLORS.textPrimary, fontFamily: "'Instrument Serif', serif" }}
            >
              One Submission.
              <br />
              Five AI Agents.
            </h2>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            viewport={{ once: true }}
            className="max-w-md flex-1"
          >
            <p className="mb-6 text-base leading-relaxed md:text-lg" style={{ color: COLORS.textSecondary }}>
              Submit a local directory or GitHub URL and CodeBase runs it through five
              specialised AI agents, caching identical repos so re-analysis is instant.
            </p>
            <button
              onClick={onCtaClick}
              className="inline-flex items-center gap-2 rounded-full border px-5 py-2.5 transition-all duration-300 hover:bg-white/5"
              style={{ borderColor: COLORS.textSecondary, color: COLORS.textPrimary }}
            >
              Get Started
              <ArrowRight className="h-4 w-4" />
            </button>
          </motion.div>
        </div>

        <div className="relative flex flex-col items-center">
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            whileInView={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            viewport={{ once: true }}
            className="relative mb-4 flex h-24 w-24 items-center justify-center rounded-lg border-2 border-dashed"
            style={{ borderColor: COLORS.borderDashed, backgroundColor: COLORS.cardBg }}
          >
            <Code2 className="h-10 w-10" style={{ color: COLORS.accent }} />
          </motion.div>

          <svg
            className="h-48 w-full max-w-5xl md:h-64"
            viewBox="0 0 800 200"
            fill="none"
            preserveAspectRatio="xMidYMin meet"
          >
            <motion.path
              d="M400 0 L400 40"
              stroke={COLORS.accent}
              strokeWidth="2"
              initial={{ pathLength: 0 }}
              whileInView={{ pathLength: 1 }}
              transition={{ duration: 0.5, delay: 0.4 }}
              viewport={{ once: true }}
            />

            <motion.path
              d="M80 40 L720 40"
              stroke={COLORS.accent}
              strokeWidth="2"
              initial={{ pathLength: 0 }}
              whileInView={{ pathLength: 1 }}
              transition={{ duration: 0.8, delay: 0.5 }}
              viewport={{ once: true }}
            />

            {[80, 200, 320, 480, 600, 720].map((x, i) => (
              <motion.path
                key={x}
                d={`M${x} 40 L${x} ${i % 2 === 0 ? 160 : 120}`}
                stroke={COLORS.accent}
                strokeWidth="2"
                initial={{ pathLength: 0 }}
                whileInView={{ pathLength: 1 }}
                transition={{ duration: 0.4, delay: 0.7 + i * 0.1 }}
                viewport={{ once: true }}
              />
            ))}

            {[80, 200, 320, 400, 480, 600, 720].map((x, i) => (
              <motion.rect
                key={x}
                x={x - 4}
                y={36}
                width="8"
                height="8"
                fill={COLORS.accent}
                rx="1"
                initial={{ opacity: 0, scale: 0 }}
                whileInView={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.3, delay: 0.6 + i * 0.05 }}
                viewport={{ once: true }}
              />
            ))}
          </svg>

          <div className="-mt-16 flex flex-wrap items-end justify-center gap-6 md:-mt-20 md:gap-12 lg:gap-16">
            {AGENT_NODES.map((node, i) => (
              <IntegrationNode
                key={node.label}
                icon={node.icon}
                label={node.label}
                className={i % 2 === 0 ? '' : 'mb-8 md:mb-12'}
                delay={0.9 + i * 0.1}
              />
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
