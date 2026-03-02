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
    <div className="flex h-screen bg-surface-dark font-sans overflow-hidden">
      <aside className="w-64 bg-slate-900 flex flex-col">
        <div className="p-5 border-b border-slate-800">
          <div className="flex items-center gap-2.5 mb-1">
            <div className="w-7 h-7 rounded-lg bg-indigo-600 flex items-center justify-center">
              <Shield className="w-4 h-4 text-white" />
            </div>
            <span className="text-xl font-bold text-white tracking-wide">LPSE-X</span>
          </div>
          <p className="text-xs text-slate-500 pl-9.5">Explainable AI Procurement Forensics</p>
        </div>

        <nav className="flex-1 overflow-y-auto py-4">
          <p className="px-4 py-2 text-xs font-semibold text-slate-600 uppercase tracking-wider">Navigation</p>
          <ul className="space-y-1">
            {navLinks.map((link) => {
              const isActive = location.pathname === link.path || 
                               (link.path !== '/' && location.pathname.startsWith(link.path))
              const Icon = getIconForPath(link.path)

              return (
                <li key={link.path}>
                  <Link
                    to={link.path}
                    className={`flex items-center gap-3 px-4 py-2.5 text-sm font-medium motion-safe:transition-colors motion-safe:duration-150 ${
                      isActive 
                        ? 'bg-indigo-600/20 text-indigo-300 border-l-2 border-indigo-400' 
                        : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200 border-l-2 border-transparent'
                    }`}
                  >
                    <Icon className="w-4 h-4 flex-shrink-0" />
                    {link.name}
                  </Link>
                </li>
              )
            })}
          </ul>
        </nav>

        <div className="p-4 border-t border-slate-800">
          <p className="text-xs text-slate-600 text-center">v1.0.0 · Find IT! 2026</p>
        </div>
      </aside>

      <main className="flex-1 flex flex-col overflow-hidden">
        <header className="h-14 bg-slate-900 border-b border-slate-800 flex items-center px-6 gap-3">
          <CurrentIcon className="w-4 h-4 text-indigo-400" />
          <h2 className="text-sm font-semibold text-slate-200">{currentPageName}</h2>
        </header>
        <div className="flex-1 overflow-auto p-6 bg-surface-dark animate-fade-in">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
