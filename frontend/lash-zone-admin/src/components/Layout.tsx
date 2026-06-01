import { useState } from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import {
  Phone, PhoneCall, Calendar, AlertTriangle, Settings, FileText,
  Menu, X, Home, ChevronRight
} from 'lucide-react';

const navigation = [
  { name: 'Dashboard', href: '/', icon: Home },
  { name: 'Calls', href: '/calls', icon: Phone },
  { name: 'Appointments', href: '/appointments', icon: Calendar },
  { name: 'Escalations', href: '/escalations', icon: AlertTriangle },
  { name: 'FAQs', href: '/faqs', icon: FileText },
  { name: 'Settings', href: '/settings', icon: Settings },
];

export function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Mobile sidebar */}
      <div className={`fixed inset-0 z-50 lg:hidden ${sidebarOpen ? 'block' : 'hidden'}`}>
        <div className="fixed inset-0 bg-gray-900/80" onClick={() => setSidebarOpen(false)} />
        <div className="fixed inset-y-0 left-0 w-64 bg-white shadow-xl">
          <div className="flex h-16 items-center justify-between px-6 border-b">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-gradient-to-br from-pink-500 to-purple-600 rounded-lg flex items-center justify-center">
                <Phone className="w-5 h-5 text-white" />
              </div>
              <span className="font-bold text-gray-900">Lash Zone AI</span>
            </div>
            <button onClick={() => setSidebarOpen(false)} className="p-2 text-gray-400 hover:text-gray-500">
              <X className="w-5 h-5" />
            </button>
          </div>
          <nav className="mt-6 px-3 space-y-1">
            {navigation.map((item) => {
              const isActive = location.pathname === item.href;
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-pink-50 text-pink-700'
                      : 'text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  <item.icon className="w-5 h-5" />
                  {item.name}
                </Link>
              );
            })}
          </nav>
        </div>
      </div>

      {/* Desktop sidebar */}
      <div className="hidden lg:fixed lg:inset-y-0 lg:flex lg:w-64 lg:flex-col">
        <div className="flex flex-col flex-1 bg-white border-r border-gray-200">
          <div className="flex h-16 items-center gap-2 px-6 border-b">
            <div className="w-8 h-8 bg-gradient-to-br from-pink-500 to-purple-600 rounded-lg flex items-center justify-center">
              <Phone className="w-5 h-5 text-white" />
            </div>
            <div>
              <span className="font-bold text-gray-900">Lash Zone AI</span>
              <p className="text-xs text-gray-500">Receptionist</p>
            </div>
          </div>
          <nav className="flex-1 mt-6 px-3 space-y-1">
            {navigation.map((item) => {
              const isActive = location.pathname === item.href;
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-pink-50 text-pink-700'
                      : 'text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  <item.icon className="w-5 h-5" />
                  {item.name}
                </Link>
              );
            })}
          </nav>
          <div className="p-4 m-4 bg-green-50 rounded-lg border border-green-200">
            <div className="flex items-center gap-2 text-green-800">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              <span className="text-sm font-medium">AI Active 24/7</span>
            </div>
            <p className="mt-1 text-xs text-green-600">Luna is ready to answer calls</p>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="lg:pl-64">
        {/* Mobile header */}
        <div className="sticky top-0 z-40 flex h-16 items-center gap-4 bg-white border-b px-4 shadow-sm lg:hidden">
          <button onClick={() => setSidebarOpen(true)} className="p-2 text-gray-400 hover:text-gray-500">
            <Menu className="w-6 h-6" />
          </button>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-gradient-to-br from-pink-500 to-purple-600 rounded-lg flex items-center justify-center">
              <Phone className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-gray-900">Lash Zone AI</span>
          </div>
        </div>

        {/* Page content */}
        <main className="py-6 px-4 sm:px-6 lg:px-8">
          {/* Breadcrumbs */}
          <nav className="mb-4 flex items-center gap-2 text-sm text-gray-500">
            <Link to="/" className="hover:text-gray-700">Dashboard</Link>
            {location.pathname !== '/' && (
              <>
                <ChevronRight className="w-4 h-4" />
                <span className="text-gray-900 capitalize">{location.pathname.slice(1)}</span>
              </>
            )}
          </nav>

          <Outlet />
        </main>
      </div>
    </div>
  );
}
