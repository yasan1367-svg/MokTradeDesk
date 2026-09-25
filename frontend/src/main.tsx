import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import ToastProvider from './components/ToastProvider'
import ErrorBoundary from './components/ErrorBoundary'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ToastProvider>
      <ErrorBoundary fullScreen label="اپلیکیشن">
        <App />
      </ErrorBoundary>
    </ToastProvider>
  </React.StrictMode>,
)