import React, { useState, useEffect } from 'react';

interface Strategy {
  id: number;
  name: string;
  description?: string;
}

interface Trade {
  id: number;
  symbol: string;
  trade_type: string;
  quantity: number;
  entry_price: number;
  exit_price?: number;
  stop_loss?: number;
  take_profit?: number;
  commission: number;
  swap: number;
  profit?: number;
  pips?: number;
  status: string;
  strategy_id?: number;
  open_time: string;
  close_time?: string;
}

const inputStyle = {
  padding: '8px 12px',
  borderRadius: '6px',
  border: '1px solid #cbd5e1',
  fontSize: '14px',
  outline: 'none',
};

function App() {
  // 🟢 ۱. تمام useState ها در بالاترین سطح کامپوننت
  const [trades, setTrades] = useState<Trade[]>([]);
  const [strategies, setStrategies] = useState<Strategy[]>([]);

  // استیک آپلود فایل
  const [selectedStrategyForImport, setSelectedStrategyForImport] = useState<string>('');

  // استیت فرم استراتژی جدید
  const [newStratName, setNewStratName] = useState('');
  const [newStratDesc, setNewStratDesc] = useState('');

  // استیت فرم معامله جدید
  const [symbol, setSymbol] = useState('XAUUSD');
  const [tradeType, setTradeType] = useState('BUY');
  const [quantity, setQuantity] = useState('0.01');
  const [entryPrice, setEntryPrice] = useState('');
  const [stopLoss, setStopLoss] = useState('');
  const [takeProfit, setTakeProfit] = useState('');
  const [selectedStrategyId, setSelectedStrategyId] = useState('');

  // استیت فرم بستن معامله
  const [closingTrade, setClosingTrade] = useState<Trade | null>(null);
  const [exitPrice, setExitPrice] = useState('');
  const [commission, setCommission] = useState('0');
  const [swap, setSwap] = useState('0');
  const [manualProfit, setManualProfit] = useState('');

  // 🟢 ۲. توابع دریافت اطلاعات از بک‌اند
  const fetchTrades = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/trades/');
      const data = await res.json();
      setTrades(data);
    } catch (err) {
      console.error("خطا در دریافت معاملات:", err);
    }
  };

  const fetchStrategies = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/strategies/');
      const data = await res.json();
      setStrategies(data);
    } catch (err) {
      console.error("خطا در دریافت استراتژی‌ها:", err);
    }
  };

  useEffect(() => {
    fetchTrades();
    fetchStrategies();
  }, []);

  // 🟢 ۳. هندلرهای عملیات
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    let url = 'http://127.0.0.1:8000/api/trades/import-csv';
    if (selectedStrategyForImport) {
      url += `?strategy_id=${selectedStrategyForImport}`;
    }

    try {
      const res = await fetch(url, {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (res.ok) {
        alert(`تعداد ${data.imported_trades} معامله با موفقیت وارد شد.`);
        fetchTrades();
        e.target.value = '';
      } else {
        alert("خطا در پردازش فایل");
      }
    } catch (err) {
      console.error("خطا در آپلود فایل:", err);
    }
  };

  const handleCreateStrategy = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newStratName) return;
    try {
      const res = await fetch('http://127.0.0.1:8000/api/strategies/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newStratName, description: newStratDesc }),
      });
      if (res.ok) {
        setNewStratName('');
        setNewStratDesc('');
        fetchStrategies();
      } else {
        const err = await res.json();
        alert(err.detail || "خطا در ثبت استراتژی");
      }
    } catch (err) {
      console.error("خطا:", err);
    }
  };

  const handleCreateTrade = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const bodyData = {
        symbol,
        trade_type: tradeType,
        quantity: parseFloat(quantity),
        entry_price: parseFloat(entryPrice),
        stop_loss: stopLoss ? parseFloat(stopLoss) : null,
        take_profit: takeProfit ? parseFloat(takeProfit) : null,
        strategy_id: selectedStrategyId ? parseInt(selectedStrategyId) : null,
      };

      const res = await fetch('http://127.0.0.1:8000/api/trades/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(bodyData),
      });

      if (res.ok) {
        setEntryPrice('');
        setStopLoss('');
        setTakeProfit('');
        fetchTrades();
      }
    } catch (err) {
      console.error("خطا در ثبت معامله:", err);
    }
  };

  const handleCloseTradeSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!closingTrade) return;

    try {
      const bodyData = {
        exit_price: parseFloat(exitPrice),
        commission: parseFloat(commission || '0'),
        swap: parseFloat(swap || '0'),
        profit: manualProfit ? parseFloat(manualProfit) : null,
      };

      const res = await fetch(`http://127.0.0.1:8000/api/trades/${closingTrade.id}/close`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(bodyData),
      });

      if (res.ok) {
        setClosingTrade(null);
        setExitPrice('');
        setCommission('0');
        setSwap('0');
        setManualProfit('');
        fetchTrades();
      }
    } catch (err) {
      console.error("خطا در بستن معامله:", err);
    }
  };

  const handleDeleteTrade = async (id: number) => {
    if (!window.confirm("آیا از حذف این معامله اطمینان دارید؟")) return;
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/trades/${id}`, {
        method: 'DELETE',
      });
      if (res.ok) fetchTrades();
    } catch (err) {
      console.error("خطا در حذف معامله:", err);
    }
  };

  // 🟢 ۴. بخش UI (رندر)
  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '20px', fontFamily: 'IRANSans, Tahoma, sans-serif', direction: 'rtl' }}>
      <h1 style={{ color: '#1e293b', textAlign: 'center', marginBottom: '30px' }}>📊 MokTradeDesk - ژورنال معاملاتی</h1>

      {/* 📥 کادر ورود خودکار از Soft4FX / متاتریدر */}
      <div style={{ background: '#eff6ff', padding: '15px 20px', borderRadius: '8px', marginBottom: '25px', border: '1px solid #bfdbfe' }}>
        <h3 style={{ marginTop: 0, color: '#1e40af' }}>📥 ورود خودکار معاملات از Soft4FX / متاتریدر</h3>
        <div style={{ display: 'flex', gap: '15px', alignItems: 'center', flexWrap: 'wrap' }}>
          <select style={inputStyle} value={selectedStrategyForImport} onChange={e => setSelectedStrategyForImport(e.target.value)}>
            <option value="">-- اختصاص به استراتژی (اختیاری) --</option>
            {strategies.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
          <input type="file" accept=".csv, .txt" onChange={handleFileUpload} style={{ fontSize: '14px' }} />
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '30px' }}>
        {/* 🎯 کادر تعریف استراتژی */}
        <div style={{ background: '#f8fafc', padding: '20px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
          <h3 style={{ marginTop: 0, color: '#334155' }}>➕ تعریف استراتژی جدید</h3>
          <form onSubmit={handleCreateStrategy} style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <input style={inputStyle} placeholder="نام استراتژی (مثلاً Breakout)" value={newStratName} onChange={e => setNewStratName(e.target.value)} required />
            <input style={inputStyle} placeholder="توضیحات (اختیاری)" value={newStratDesc} onChange={e => setNewStratDesc(e.target.value)} />
            <button type="submit" style={{ padding: '8px 15px', background: '#3b82f6', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer' }}>ثبت استراتژی</button>
          </form>
        </div>

        {/* 📝 کادر ثبت پوزیشن جدید */}
        <div style={{ background: '#f8fafc', padding: '20px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
          <h3 style={{ marginTop: 0, color: '#334155' }}>➕ ثبت معامله دستی</h3>
          <form onSubmit={handleCreateTrade} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
            <input style={inputStyle} placeholder="نماد (XAUUSD)" value={symbol} onChange={e => setSymbol(e.target.value)} required />
            <select style={inputStyle} value={tradeType} onChange={e => setTradeType(e.target.value)}>
              <option value="BUY">BUY</option>
              <option value="SELL">SELL</option>
            </select>
            <input style={inputStyle} type="number" step="0.01" placeholder="حجم (لات)" value={quantity} onChange={e => setQuantity(e.target.value)} required />
            <input style={inputStyle} type="number" step="any" placeholder="قیمت ورود" value={entryPrice} onChange={e => setEntryPrice(e.target.value)} required />
            <input style={inputStyle} type="number" step="any" placeholder="حد ضرر (SL)" value={stopLoss} onChange={e => setStopLoss(e.target.value)} />
            <input style={inputStyle} type="number" step="any" placeholder="حد سود (TP)" value={takeProfit} onChange={e => setTakeProfit(e.target.value)} />
            <select style={{ ...inputStyle, gridColumn: 'span 2' }} value={selectedStrategyId} onChange={e => setSelectedStrategyId(e.target.value)}>
              <option value="">-- انتخاب استراتژی --</option>
              {strategies.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
            <button type="submit" style={{ gridColumn: 'span 2', padding: '10px', background: '#10b981', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold' }}>ثبت معامله</button>
          </form>
        </div>
      </div>

      {/* ✖️ کادر بستن معامله */}
      {closingTrade && (
        <div style={{ background: '#fffbe3', padding: '20px', borderRadius: '8px', border: '1px solid #fde047', marginBottom: '25px' }}>
          <h3 style={{ marginTop: 0, color: '#854d0e' }}>بستن معامله #{closingTrade.id} ({closingTrade.symbol} - {closingTrade.trade_type})</h3>
          <form onSubmit={handleCloseTradeSubmit} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '10px' }}>
            <div>
              <label style={{ fontSize: '12px' }}>قیمت خروج:</label>
              <input style={inputStyle} type="number" step="any" value={exitPrice} onChange={e => setExitPrice(e.target.value)} required />
            </div>
            <div>
              <label style={{ fontSize: '12px' }}>کمیسیون ($):</label>
              <input style={inputStyle} type="number" step="any" value={commission} onChange={e => setCommission(e.target.value)} />
            </div>
            <div>
              <label style={{ fontSize: '12px' }}>سواپ ($):</label>
              <input style={inputStyle} type="number" step="any" value={swap} onChange={e => setSwap(e.target.value)} />
            </div>
            <div>
              <label style={{ fontSize: '12px' }}>سود دستی (اختیاری):</label>
              <input style={inputStyle} type="number" step="any" placeholder="محاسبه خودکار" value={manualProfit} onChange={e => setManualProfit(e.target.value)} />
            </div>
            <div style={{ gridColumn: 'span 4', display: 'flex', gap: '10px', marginTop: '10px' }}>
              <button type="submit" style={{ padding: '8px 20px', background: '#eab308', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold' }}>بستن پوزیشن</button>
              <button type="button" onClick={() => setClosingTrade(null)} style={{ padding: '8px 20px', background: '#94a3b8', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer' }}>انصراف</button>
            </div>
          </form>
        </div>
      )}

      {/* 📋 جدول معاملات */}
      <h2 style={{ color: '#334155' }}>لیست معاملات</h2>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', background: '#fff', boxShadow: '0 1px 3px rgba(0,0,0,0.1)', borderRadius: '8px', overflow: 'hidden' }}>
          <thead>
            <tr style={{ background: '#f1f5f9', textAlign: 'right', borderBottom: '2px solid #e2e8f0' }}>
              <th style={{ padding: '12px' }}>شناسه</th>
              <th style={{ padding: '12px' }}>نماد</th>
              <th style={{ padding: '12px' }}>نوع</th>
              <th style={{ padding: '12px' }}>حجم</th>
              <th style={{ padding: '12px' }}>ورود</th>
              <th style={{ padding: '12px' }}>خروج</th>
              <th style={{ padding: '12px' }}>پیپ</th>
              <th style={{ padding: '12px' }}>سود ($)</th>
              <th style={{ padding: '12px' }}>وضعیت</th>
              <th style={{ padding: '12px' }}>عملیات</th>
            </tr>
          </thead>
          <tbody>
            {trades.length === 0 ? (
              <tr>
                <td colSpan={10} style={{ textAlign: 'center', padding: '20px', color: '#94a3b8' }}>هیچ معامله‌ای ثبت نشده است</td>
              </tr>
            ) : (
              trades.map(t => (
                <tr key={t.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                  <td style={{ padding: '12px' }}>#{t.id}</td>
                  <td style={{ padding: '12px', fontWeight: 'bold' }}>{t.symbol}</td>
                  <td style={{ padding: '12px', color: t.trade_type === 'BUY' ? '#16a34a' : '#dc2626', fontWeight: 'bold' }}>{t.trade_type}</td>
                  <td style={{ padding: '12px' }}>{t.quantity}</td>
                  <td style={{ padding: '12px' }}>{t.entry_price}</td>
                  <td style={{ padding: '12px' }}>{t.exit_price ?? '-'}</td>
                  <td style={{ padding: '12px' }}>{t.pips ?? '-'}</td>
                  <td style={{ padding: '12px', fontWeight: 'bold', color: (t.profit ?? 0) >= 0 ? '#16a34a' : '#dc2626' }}>
                    {t.profit !== null && t.profit !== undefined ? `${t.profit} $` : '-'}
                  </td>
                  <td style={{ padding: '12px' }}>
                    <span style={{ padding: '4px 8px', borderRadius: '4px', fontSize: '12px', background: t.status === 'OPEN' ? '#dcfce7' : '#f1f5f9', color: t.status === 'OPEN' ? '#15803d' : '#64748b' }}>
                      {t.status === 'OPEN' ? 'باز' : 'بسته شده'}
                    </span>
                  </td>
                  <td style={{ padding: '12px', display: 'flex', gap: '8px' }}>
                    {t.status === 'OPEN' && (
                      <button onClick={() => { setClosingTrade(t); setExitPrice(t.entry_price.toString()); }} style={{ padding: '4px 8px', background: '#eab308', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '12px' }}>
                        بستن
                      </button>
                    )}
                    <button onClick={() => handleDeleteTrade(t.id)} style={{ padding: '4px 8px', background: '#ef4444', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '12px' }}>
                      حذف
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default App;