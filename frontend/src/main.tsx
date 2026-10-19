import React, { Suspense } from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import ToastProvider from './components/ToastProvider'
import ErrorBoundary from './components/ErrorBoundary'
import './index.css'

// ── فاز ۱۵.۴: fallback سراسری آگاه از Dark Mode ──
function RootFallback() {
  return (
    <div className="flex items-center justify-center h-screen bg-[var(--bg-base)] text-[var(--text-secondary)]">
      <div className="flex flex-col items-center gap-3">
        <div className="w-9 h-9 rounded-full border-2 border-[var(--border-subtle)] border-t-[var(--accent)] animate-spin" />
        <span className="text-xs">در حال بارگذاری…</span>
      </div>
    </div>
  )
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ToastProvider>
      <ErrorBoundary fullScreen label="اپلیکیشن">
        <Suspense fallback={<RootFallback />}>
          <App />
        </Suspense>
      </ErrorBoundary>
    </ToastProvider>
  </React.StrictMode>,
)