/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // رنگ‌های اصلی (کلاس‌های قدیمی که صفحات استفاده می‌کنند)
        'card': '#FFFFFF',
        'card-border': '#E5EBF3',
        'text-primary': '#1A2B47',
        'text-secondary': '#6B7A94',
        'text-muted': '#9AA8BF',
        'accent': '#3F7CFF',
        'profit': '#13AE81',
        'loss': '#E45D72',
        'warning': '#D99B25',
        'purple': '#7959D6',
        'background': '#EEF2F9',
        'bg-base': '#EEF2F9',
        'bg-input': '#F8FAFF',
        'bg-elevated': '#F5F7FB',
        'bg-sidebar': '#152238',
      },
      fontFamily: {
        sans: ['Vazirmatn', 'sans-serif'],
      },
      boxShadow: {
        'xs': '0 1px 2px rgba(25, 50, 85, 0.04)',
        'sm': '0 2px 6px rgba(25, 50, 85, 0.06), 0 1px 2px rgba(25, 50, 85, 0.04)',
        'md': '0 6px 16px rgba(25, 50, 85, 0.08), 0 2px 4px rgba(25, 50, 85, 0.04)',
        'lg': '0 14px 32px rgba(25, 50, 85, 0.1), 0 4px 8px rgba(25, 50, 85, 0.05)',
        'hover': '0 20px 40px rgba(63, 124, 255, 0.15), 0 8px 16px rgba(25, 50, 85, 0.08)',
      },
    },
  },
  plugins: [],
}