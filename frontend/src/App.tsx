import React, { useState, useEffect } from 'react';

interface Trade {
  id: number;
  symbol: string;
  trade_type: string;
  entry_price: number;
  quantity: number;
  stop_loss?: number;
  take_profit?: number;
  exit_price?: number;
  status: string;
  notes?: string;
  created_at: string;
}

export default function App() {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [form, setForm] = useState({
    symbol: '',
    trade_type: 'BUY',
    entry_price: '',
    quantity: '',
    stop_loss: '',
    take_profit: '',
    notes: ''
  });

  const fetchTrades = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/trades/');
      const data = await res.json();
      setTrades(data);
    } catch (err) {
      console.error("خطا در دریافت لیست معاملات:", err);
    }
  };

  useEffect(() => {
    fetchTrades();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const payload = {
      symbol: form.symbol.toUpperCase(),
      trade_type: form.trade_type,
      entry_price: parseFloat(form.entry_price),
      quantity: parseFloat(form.quantity),
      stop_loss: form.stop_loss ? parseFloat(form.stop_loss) : null,
      take_profit: form.take_profit ? parseFloat(form.take_profit) : null,
      notes: form.notes || null,
      status: 'OPEN'
    };

    try {
      const res = await fetch('http://127.0.0.1:8000/api/trades/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        setForm({ symbol: '', trade_type: 'BUY', entry_price: '', quantity: '', stop_loss: '', take_profit: '', notes: '' });
        fetchTrades();
      }
    } catch (err) {
      console.error("خطا در ثبت معامله:", err);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await fetch(`http://127.0.0.1:8000/api/trades/${id}`, { method: 'DELETE' });
      fetchTrades();
    } catch (err) {
      console.error("خطا در حذف معامله:", err);
    }
  };

  const inputStyle: React.CSSProperties = {
    padding: '8px 12px',
    borderRadius: '6px',
    border: '1px solid #d1d5db',
    backgroundColor: '#ffffff',
    color: '#000000',
    fontSize: '14px',
    outline: 'none'
  };

  return (
    <div style={{ padding: '20px', fontFamily: 'sans-serif', maxWidth: '900px', margin: '0 auto', direction: 'rtl', color: '#18181b' }}>
      <h1>📊 MokTradeDesk - ژورنال معاملات</h1>

      {/* فرم ثبت معامله */}
      <form onSubmit={handleSubmit} style={{ background: '#f4f4f5', padding: '20px', borderRadius: '8px', marginBottom: '20px', border: '1px solid #e4e4e7' }}>
        <h3 style={{ marginTop: 0 }}>ثبت معامله جدید</h3>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '10px', marginBottom: '10px' }}>
          <input style={inputStyle} placeholder="نماد (مثلاً XAUUSD)" value={form.symbol} onChange={e => setForm({...form, symbol: e.target.value})} required />
          <select style={inputStyle} value={form.trade_type} onChange={e => setForm({...form, trade_type: e.target.value})}>
            <option value="BUY">خرید (BUY)</option>
            <option value="SELL">فروش (SELL)</option>
          </select>
          <input style={inputStyle} type="number" step="any" placeholder="قیمت ورود" value={form.entry_price} onChange={e => setForm({...form, entry_price: e.target.value})} required />
          <input style={inputStyle} type="number" step="any" placeholder="حجم (Quantity)" value={form.quantity} onChange={e => setForm({...form, quantity: e.target.value})} required />
          <input style={inputStyle} type="number" step="any" placeholder="حد ضرر (SL)" value={form.stop_loss} onChange={e => setForm({...form, stop_loss: e.target.value})} />
          <input style={inputStyle} type="number" step="any" placeholder="حد سود (TP)" value={form.take_profit} onChange={e => setForm({...form, take_profit: e.target.value})} />
        </div>
        <input style={{ ...inputStyle, width: '100%', marginBottom: '10px', boxSizing: 'border-box' }} placeholder="یادداشت / استراتژی" value={form.notes} onChange={e => setForm({...form, notes: e.target.value})} />
        <button type="submit" style={{ padding: '10px 20px', backgroundColor: '#10b981', color: '#ffffff', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold' }}>ثبت پوزیشن</button>
      </form>

      {/* جدول معاملات */}
      <h3>لیست معاملات ثبت‌شده</h3>
      <table border={1} cellPadding={10} style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'center', borderColor: '#e4e4e7' }}>
        <thead>
          <tr style={{ background: '#e4e4e7', color: '#000000' }}>
            <th>ID</th>
            <th>نماد</th>
            <th>نوع</th>
            <th>ورود</th>
            <th>حجم</th>
            <th>SL</th>
            <th>TP</th>
            <th>وضعیت</th>
            <th>عملیات</th>
          </tr>
        </thead>
        <tbody>
          {trades.map(t => (
            <tr key={t.id} style={{ backgroundColor: '#ffffff', color: '#000000' }}>
              <td>{t.id}</td>
              <td><strong>{t.symbol}</strong></td>
              <td style={{ color: t.trade_type === 'BUY' ? '#16a34a' : '#dc2626', fontWeight: 'bold' }}>{t.trade_type}</td>
              <td>{t.entry_price}</td>
              <td>{t.quantity}</td>
              <td>{t.stop_loss || '-'}</td>
              <td>{t.take_profit || '-'}</td>
              <td>{t.status}</td>
              <td>
                <button onClick={() => handleDelete(t.id)} style={{ color: '#dc2626', border: 'none', background: 'none', cursor: 'pointer', fontWeight: 'bold' }}>حذف</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}