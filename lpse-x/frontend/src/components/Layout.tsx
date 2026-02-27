import React from 'react'
import { Link, Outlet, useLocation } from 'react-router-dom'

export function Layout(): React.ReactElement {
  const location = useLocation()

  const navLinks = [
    { name: 'Dashboard', path: '/' },
    { name: 'Cartel Graph', path: '/cartel' },
    { name: 'Risk Map', path: '/map' },
    { name: 'Reports', path: '/reports' },
    { name: 'Config Panel', path: '/config' },
  ]

  return (
    <div className="flex h-screen bg-gray-100 font-sans">
      <aside className="w-64 bg-slate-900 text-white flex flex-col">
        <div className="p-4 bg-slate-950">
          <h1 className="text-2xl font-bold text-white tracking-wide">LPSE-X</h1>
          <p className="text-xs text-slate-400 mt-1">Explainable AI Procurement Forensics</p>
        </div>
        <nav className="flex-1 overflow-y-auto py-4">
          <ul className="space-y-1">
            {navLinks.map((link) => {
              const isActive = location.pathname === link.path || 
                               (link.path !== '/' && location.pathname.startsWith(link.path))
              return (
                <li key={link.path}>
                  <Link
                    to={link.path}
                    className={`block px-4 py-2 text-sm transition-colors ${
                      isActive 
                        ? 'bg-blue-600 text-white font-medium border-l-4 border-blue-400' 
                        : 'text-slate-300 hover:bg-slate-800 hover:text-white border-l-4 border-transparent'
                    }`}
                  >
                    {link.name}
                  </Link>
                </li>
              )
            })}
          </ul>
        </nav>
      </aside>

      <main className="flex-1 flex flex-col overflow-hidden">
        <header className="bg-white shadow-sm h-16 flex items-center px-6 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-800">
            {navLinks.find(l => location.pathname === l.path || (l.path !== '/' && location.pathname.startsWith(l.path)))?.name || 'Tender Details'}
          </h2>
        </header>
        <div className="flex-1 overflow-auto p-6 bg-slate-50">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
