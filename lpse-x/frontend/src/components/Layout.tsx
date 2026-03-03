import React from 'react'
import { Link, Outlet, useLocation } from 'react-router-dom'
import { 
  LayoutDashboard, 
  Network, 
  Map as RiskMapIcon, 
  FileText, 
  Settings, 
  Shield 
} from 'lucide-react'

export function Layout(): React.ReactElement {
  const location = useLocation()

  const navLinks = [
    { name: 'Dashboard', path: '/' },
    { name: 'Cartel Graph', path: '/cartel' },
    { name: 'Risk Map', path: '/map' },
    { name: 'Reports', path: '/reports' },
    { name: 'Config Panel', path: '/config' },
  ]

  const getIconForPath = (path: string) => {
    switch (path) {
      case '/': return LayoutDashboard
      case '/cartel': return Network
      case '/map': return RiskMapIcon
      case '/reports': return FileText
      case '/config': return Settings
      default: return FileText
    }
  }

  const activeLink = navLinks.find(
    l => location.pathname === l.path || (l.path !== '/' && location.pathname.startsWith(l.path))
  )
  
  const currentPageName = activeLink?.name || 'Tender Details'
  const CurrentIcon = activeLink ? getIconForPath(activeLink.path) : FileText

  return (
    <div className="flex h-screen bg-[#020617] font-sans overflow-hidden">
      {/* Glassmorphism sidebar */}
      <aside className="w-64 bg-white/5 backdrop-blur-xl border-r border-white/10 flex flex-col flex-shrink-0">
        {/* Logo */}
        <div className="p-5 border-b border-white/10">
          <div className="flex items-center gap-2.5 mb-1">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-cyan-500 flex items-center justify-center shadow-[0_0_12px_rgba(6,182,212,0.4)]">
              <Shield className="w-4 h-4 text-white" />
            </div>
            <span className="text-xl font-bold tracking-wide bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
              LPSE-X
            </span>
          </div>
          <p className="text-xs text-slate-500 pl-10">Explainable AI Procurement Forensics</p>
        </div>

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto py-4">
          <p className="px-4 py-2 text-xs font-semibold text-slate-600 uppercase tracking-widest">Navigation</p>
          <ul className="space-y-0.5 px-2">
            {navLinks.map((link) => {
              const isActive = location.pathname === link.path || 
                               (link.path !== '/' && location.pathname.startsWith(link.path))
              const Icon = getIconForPath(link.path)

              return (
                <li key={link.path}>
                  <Link
                    to={link.path}
                    className={`flex items-center gap-3 px-3 py-2.5 text-sm font-medium rounded-lg border-l-2 motion-safe:transition-all motion-safe:duration-200 ${
                      isActive 
                        ? 'bg-white/10 text-cyan-400 border-cyan-400 shadow-[0_0_20px_rgba(6,182,212,0.2)]' 
                        : 'text-slate-400 hover:bg-white/5 hover:text-white border-transparent'
                    }`}
                  >
                    <Icon className={`w-4 h-4 flex-shrink-0 ${isActive ? 'text-cyan-400' : ''}`} />
                    {link.name}
                  </Link>
                </li>
              )
            })}
          </ul>
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-white/10 bg-white/5">
          <p className="text-xs text-slate-600 text-center">v1.0.0 · Find IT! 2026</p>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Glass header */}
        <header className="h-14 bg-white/5 backdrop-blur-md border-b border-white/10 flex items-center px-6 gap-3 flex-shrink-0">
          <CurrentIcon className="w-4 h-4 text-cyan-400" />
          <h2 className="text-sm font-semibold bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
            {currentPageName}
          </h2>
        </header>
        {/* Scrollable page area with mesh background */}
        <div className="flex-1 overflow-auto p-6 bg-[#020617] bg-mesh">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
