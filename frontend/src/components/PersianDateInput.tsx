import { useState, useEffect } from 'react';

interface PersianDateInputProps {
  value: string; // ISO format (YYYY-MM-DD)
  onChange: (isoDate: string) => void;
  label?: string;
  placeholder?: string;
  className?: string;
}

export default function PersianDateInput({
  value,
  onChange,
  label,
  placeholder = 'مثلاً 1405/05/25',
  className = '',
}: PersianDateInputProps) {
  const [text, setText] = useState('');

  // تبدیل ISO به شمسی وقتی مقدار تغییر می‌کند
  useEffect(() => {
    if (value) {
      try {
        const date = new Date(value);
        // تبدیل دقیق‌تر
        const persian = gregorianToJalali(
          date.getFullYear(),
          date.getMonth() + 1,
          date.getDate()
        );
        setText(persian);
      } catch (e) {
        setText('');
      }
    } else {
      setText('');
    }
  }, [value]);

  // وقتی کاربر تایپ می‌کند
  const handleChange = (input: string) => {
    setText(input);

    // بررسی فرمت 1405/05/25
    const match = input.match(/^(\d{4})\/(\d{1,2})\/(\d{1,2})$/);
    if (match) {
      const jy = parseInt(match[1]);
      const jm = parseInt(match[2]);
      const jd = parseInt(match[3]);

      if (jm >= 1 && jm <= 12 && jd >= 1 && jd <= 31 && jy >= 1300 && jy <= 1500) {
        try {
          const gregorian = jalaliToGregorian(jy, jm, jd);
          onChange(gregorian);
        } catch (e) {
          // تاریخ نامعتبر
        }
      }
    }
  };

  return (
    <div className={className}>
      {label && (
        <label className="text-[var(--text-secondary)] text-xs block mb-1">{label}</label>
      )}
      <input
        type="text"
        value={text}
        onChange={(e) => handleChange(e.target.value)}
        placeholder={placeholder}
        dir="ltr"
        className="w-full bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl px-4 py-2 text-[var(--text-primary)] text-center focus:border-[var(--accent)] focus:outline-none font-mono"
      />
    </div>
  );
}

// ─────────────────────────────────────────────
// تبدیل شمسی به میلادی
// ─────────────────────────────────────────────
function jalaliToGregorian(jy: number, jm: number, jd: number): string {
  let gy, gm, gd;
  
  jy += 1595;
  let days = -355668 + (365 * jy) + (Math.floor(jy / 33) * 8) + Math.floor(((jy % 33) + 3) / 4) + jd;
  
  if (jm < 7) {
    days += (jm - 1) * 31;
  } else {
    days += ((jm - 7) * 30) + 186;
  }
  
  gy = 400 * Math.floor(days / 146097);
  days %= 146097;
  
  if (days > 36524) {
    gy += 100 * Math.floor(--days / 36524);
    days %= 36524;
    if (days >= 365) days++;
  }
  
  gy += 4 * Math.floor(days / 1461);
  days %= 1461;
  
  if (days > 365) {
    gy += Math.floor((days - 1) / 365);
    days = (days - 1) % 365;
  }
  
  gd = days + 1;
  const sal_a = [0, 31, (gy % 4 === 0 && gy % 100 !== 0) || gy % 400 === 0 ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  
  for (gm = 0; gm < 13; gm++) {
    const v = sal_a[gm];
    if (gd <= v) break;
    gd -= v;
  }
  
  return `${gy}-${String(gm).padStart(2, '0')}-${String(gd).padStart(2, '0')}`;
}

// ─────────────────────────────────────────────
// تبدیل میلادی به شمسی
// ─────────────────────────────────────────────
function gregorianToJalali(gy: number, gm: number, gd: number): string {
  const g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334];
  let jy = (gy <= 1600) ? 0 : 979;
  gy -= (gy <= 1600) ? 621 : 1600;
  const gy2 = (gm > 2) ? (gy + 1) : gy;
  let days = (365 * gy) + Math.floor((gy2 + 3) / 4) - Math.floor((gy2 + 99) / 100) + Math.floor((gy2 + 399) / 400) - 80 + gd + g_d_m[gm - 1];
  jy += 33 * Math.floor(days / 12053);
  days %= 12053;
  jy += 4 * Math.floor(days / 1461);
  days %= 1461;
  if (days > 365) {
    jy += Math.floor((days - 1) / 365);
    days = (days - 1) % 365;
  }
  const jm = (days < 186) ? 1 + Math.floor(days / 31) : 7 + Math.floor((days - 186) / 30);
  const jd = 1 + ((days < 186) ? (days % 31) : ((days - 186) % 30));
  return `${jy}/${String(jm).padStart(2, '0')}/${String(jd).padStart(2, '0')}`;
}