import { Link } from 'react-router-dom'

const features = [
  {
    icon: '🎥',
    title: 'HD Video Calls',
    desc: 'Crystal-clear 1080p video with adaptive bitrate for any connection.',
  },
  {
    icon: '🔒',
    title: 'Enterprise Security',
    desc: 'End-to-end encryption, waiting rooms, and granular host controls.',
  },
  {
    icon: '💬',
    title: 'Real-time Chat',
    desc: 'In-meeting chat with file sharing, reactions, and threaded replies.',
  },
  {
    icon: '🖥️',
    title: 'Screen Sharing',
    desc: 'Share your entire screen, a window, or just a browser tab.',
  },
  {
    icon: '⏺️',
    title: 'Cloud Recording',
    desc: 'Record meetings and store them securely in object storage.',
  },
  {
    icon: '🌐',
    title: 'Global TURN/STUN',
    desc: 'Reliable WebRTC connections via self-hosted Coturn relay servers.',
  },
]

export default function LandingPage() {
  return (
    <div className="min-h-screen" style={{ background: 'var(--bg-primary)' }}>
      {/* Navigation */}
      <nav className="fixed top-0 inset-x-0 z-50 flex items-center justify-between px-8 py-4"
        style={{ background: 'rgba(10,10,15,0.8)', backdropFilter: 'blur(20px)', borderBottom: '1px solid var(--border)' }}>
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center"
            style={{ background: 'linear-gradient(135deg, #6366f1, #4f46e5)' }}>
            <span className="text-white text-sm font-bold">M</span>
          </div>
          <span className="text-lg font-bold gradient-text">EnterpriseMeet</span>
        </div>
        <div className="flex items-center gap-3">
          <Link to="/login" className="btn-ghost btn text-sm">Sign In</Link>
          <Link to="/register" className="btn-primary btn text-sm">Get Started Free</Link>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative pt-32 pb-24 px-6 text-center overflow-hidden">
        {/* Background glows */}
        <div className="absolute inset-0 pointer-events-none overflow-hidden">
          <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[600px] h-[600px] rounded-full"
            style={{ background: 'radial-gradient(circle, rgba(99,102,241,0.15) 0%, transparent 70%)' }} />
          <div className="absolute top-1/3 left-1/4 w-64 h-64 rounded-full"
            style={{ background: 'radial-gradient(circle, rgba(168,139,250,0.08) 0%, transparent 70%)' }} />
          <div className="absolute top-1/3 right-1/4 w-64 h-64 rounded-full"
            style={{ background: 'radial-gradient(circle, rgba(59,130,246,0.08) 0%, transparent 70%)' }} />
        </div>

        <div className="relative max-w-4xl mx-auto animate-fade-in">
          <div className="badge-accent mb-6 mx-auto w-fit">
            <span>✨</span>
            <span>Enterprise-grade video conferencing</span>
          </div>

          <h1 className="text-5xl sm:text-7xl font-extrabold mb-6 leading-tight">
            <span style={{ color: 'var(--text-primary)' }}>Meet smarter,</span>
            <br />
            <span className="gradient-text">collaborate better</span>
          </h1>

          <p className="text-lg sm:text-xl max-w-2xl mx-auto mb-10"
            style={{ color: 'var(--text-secondary)', lineHeight: '1.8' }}>
            The open-source, self-hosted video conferencing platform built for teams who care about privacy, security, and performance.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link to="/register"
              className="btn-primary btn text-base px-8 py-3 animate-pulse-glow">
              Start a meeting free →
            </Link>
            <Link to="/login"
              className="btn-secondary btn text-base px-8 py-3">
              Sign in to your account
            </Link>
          </div>

          <div className="mt-6 flex items-center justify-center gap-6 text-sm"
            style={{ color: 'var(--text-muted)' }}>
            <span>✓ No credit card required</span>
            <span>✓ Self-hosted</span>
            <span>✓ Open source</span>
          </div>
        </div>
      </section>

      {/* Mock Meeting UI Preview */}
      <section className="px-6 pb-24 max-w-5xl mx-auto">
        <div className="glass p-6 animate-fade-in" style={{ borderColor: 'rgba(99,102,241,0.3)' }}>
          <div className="flex items-center gap-3 mb-4">
            <div className="flex gap-1.5">
              <div className="w-3 h-3 rounded-full" style={{ background: '#ef4444' }} />
              <div className="w-3 h-3 rounded-full" style={{ background: '#f59e0b' }} />
              <div className="w-3 h-3 rounded-full" style={{ background: '#10b981' }} />
            </div>
            <div className="flex-1 rounded-lg px-3 py-1 text-xs text-center"
              style={{ background: 'var(--bg-secondary)', color: 'var(--text-muted)' }}>
              enterprisemeet.local/room/XK9-B2P
            </div>
          </div>
          {/* Mock video grid */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {[
              { name: 'Sarah Chen', color: '#6366f1', emoji: '👩‍💼' },
              { name: 'James Park', color: '#10b981', emoji: '👨‍💻' },
              { name: 'Maria Garcia', color: '#f59e0b', emoji: '👩‍🎨' },
              { name: 'Alex Kumar', color: '#3b82f6', emoji: '👨‍🔬' },
              { name: 'Lisa Wang', color: '#ec4899', emoji: '👩‍🏫' },
              { name: 'You', color: '#8b5cf6', emoji: '🧑‍💻', isYou: true },
            ].map((p) => (
              <div key={p.name} className="video-tile group" style={{ minHeight: 100 }}>
                <div className="absolute inset-0 flex flex-col items-center justify-center gap-2"
                  style={{ background: `linear-gradient(135deg, ${p.color}22, ${p.color}11)` }}>
                  <span className="text-3xl">{p.emoji}</span>
                  <span className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>
                    {p.name}
                    {(p as { isYou?: boolean }).isYou && <span className="ml-1 badge-accent text-xs">(you)</span>}
                  </span>
                </div>
                <div className="absolute bottom-2 right-2 flex gap-1">
                  <div className="w-5 h-5 rounded flex items-center justify-center text-xs"
                    style={{ background: 'rgba(0,0,0,0.6)' }}>🎤</div>
                </div>
              </div>
            ))}
          </div>
          {/* Mock control bar */}
          <div className="mt-4 flex items-center justify-center gap-3">
            {['🎤', '🎥', '🖥️', '💬', '👥'].map((icon, i) => (
              <div key={i} className="btn-icon text-base" style={{ width: 44, height: 44 }}>{icon}</div>
            ))}
            <div className="btn-icon-danger btn-icon text-base ml-2" style={{ width: 44, height: 44 }}>📞</div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="px-6 pb-24 max-w-6xl mx-auto">
        <h2 className="text-3xl sm:text-4xl font-bold text-center mb-4">
          Everything your team needs
        </h2>
        <p className="text-center mb-12" style={{ color: 'var(--text-secondary)' }}>
          Built with modern open-source technologies for reliability at scale
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {features.map(f => (
            <div key={f.title} className="glass glass-hover p-6">
              <div className="text-3xl mb-4">{f.icon}</div>
              <h3 className="font-bold text-lg mb-2">{f.title}</h3>
              <p className="text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="px-6 pb-24 max-w-3xl mx-auto text-center">
        <div className="glass p-12" style={{ borderColor: 'rgba(99,102,241,0.3)' }}>
          <h2 className="text-3xl font-bold mb-4">Ready to get started?</h2>
          <p className="mb-8" style={{ color: 'var(--text-secondary)' }}>
            Create your account in seconds and host your first meeting today.
          </p>
          <Link to="/register" className="btn-primary btn text-base px-10 py-3">
            Create free account →
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t px-8 py-8 text-center text-sm"
        style={{ borderColor: 'var(--border)', color: 'var(--text-muted)' }}>
        © 2026 EnterpriseMeet. Open source, self-hosted video conferencing.
      </footer>
    </div>
  )
}
