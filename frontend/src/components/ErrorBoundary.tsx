import { Component } from 'react';
import type { ErrorInfo, ReactNode } from 'react';

interface ErrorBoundaryProps {
  children: ReactNode;
  label?: string;
  fullScreen?: boolean;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/**
 * ErrorBoundary — مرز خطای سراسری با پیام کاربرپسند
 */
export default class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error(`[ErrorBoundary] ${this.props.label ?? ''}:`, error, errorInfo);
  }

  handleCopy = () => {
    const { error } = this.state;
    const body = `خطا${this.props.label ? ` در ${this.props.label}` : ''}\n\n${error?.name}: ${error?.message}\n\n${error?.stack ?? ''}`;
    navigator.clipboard
      ?.writeText(body)
      .then(() => alert('✅ اطلاعات خطا کپی شد. لطفاً به پشتیبان ارسال کنید.'))
      .catch(() => {});
  };

  handleReset = () => {
    this.setState({ hasError: false, error: null });
    window.location.reload();
  };

  render() {
    if (!this.state.hasError) return this.props.children;

    const content = (
      <div className="flex items-center justify-center py-20 px-4" dir="rtl">
        <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-[22px] p-8 max-w-lg w-full shadow-lg text-center">
          <div className="text-4xl mb-4">❌</div>
          <h2 className="text-lg font-extrabold text-[var(--text-primary)] mb-2">
            {this.props.label ? `خطا در بارگذاری ${this.props.label}` : 'خطایی رخ داد'}
          </h2>
          <p className="text-sm text-[#E45D72] mb-2 font-mono bg-[var(--bg-base)] rounded-lg p-3 text-left dir-ltr overflow-auto max-h-24">
            {this.state.error?.message || 'خطای ناشناخته'}
          </p>
          <div className="flex gap-3 justify-center mt-5">
            <button
              onClick={this.handleReset}
              className="bg-[#3F7CFF] hover:bg-[#3F7CFF]/80 text-white px-6 py-2.5 rounded-xl text-sm font-bold transition-all"
            >
              🔄 بارگذاری مجدد
            </button>
            <button
              onClick={this.handleCopy}
              className="bg-[var(--bg-base)] text-[var(--text-secondary)] border border-[var(--border-subtle)] px-6 py-2.5 rounded-xl text-sm font-bold transition-all hover:bg-[var(--accent-soft)]"
            >
              📋 کپی خطا
            </button>
          </div>
        </div>
      </div>
    );

    return this.props.fullScreen ? (
      <div className="min-h-screen flex items-center justify-center bg-[var(--bg-base)]">{content}</div>
    ) : (
      content
    );
  }
}
