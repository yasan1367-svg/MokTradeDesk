from pathlib import Path

root = Path(__file__).resolve().parent.parent
p = root / 'frontend/src/pages/PayoutHistoryPage.tsx'
s = p.read_bytes().decode('utf-8')


def replace(old, new):
    global s
    if old not in s:
        old = old.replace('\n', '\r\n')
        new = new.replace('\n', '\r\n')
    assert s.count(old) == 1, (old, s.count(old))
    s = s.replace(old, new, 1)


replace('  createPropPayout,\n', '  createPropPayout,\n  updatePropPayout,\n')
replace('  const [editingBrokerId, setEditingBrokerId] = useState<number | null>(null);\n', '  const [editingBrokerId, setEditingBrokerId] = useState<number | null>(null);\n  const [editingPropId, setEditingPropId] = useState<number | null>(null);\n')
start = s.index('  const handleSubmit = async () => {')
end = s.index('  const handleDelete = ', start)
s = s[:start] + '''  const handleSubmit = async () => {
    if (!form.prop_stage_id || !form.amount || !form.destination_account_id) {
      toast.warning('مرحله، مبلغ و حساب مقصد الزامی است');
      return;
    }
    const amount = Number(form.amount);
    if (!Number.isFinite(amount) || amount <= 0) {
      toast.warning('مبلغ باید عددی مثبت باشد');
      return;
    }
    setSaving(true);
    try {
      const payload = {
        amount,
        destination_account_id: Number(form.destination_account_id),
        currency: destAccounts.find((account: any) => String(account.id) === form.destination_account_id)?.currency,
        withdrawal_date: form.withdrawal_date || undefined,
        note: form.note,
      };
      if (editingPropId !== null) {
        await updatePropPayout(editingPropId, payload);
      } else {
        await createPropPayout({ ...payload, prop_stage_id: Number(form.prop_stage_id) });
      }
      toast.success(editingPropId !== null ? 'برداشت و اثر مالی آن اصلاح شد' : 'برداشت با موفقیت ثبت شد');
      setShowForm(false);
      setEditingPropId(null);
      setForm({ prop_stage_id: '', amount: '', destination_account_id: '', withdrawal_date: '', note: '' });
      load();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'خطا در ذخیره برداشت');
    } finally {
      setSaving(false);
    }
  };

  const openPropEdit = (row: any) => {
    setEditingPropId(row.id);
    setForm({
      prop_stage_id: String(row.prop_stage_id),
      amount: String(row.amount),
      destination_account_id: String(row.destination_account_id),
      withdrawal_date: row.withdrawal_date || '',
      note: row.note || '',
    });
    setShowForm(true);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

''' + s[end:]
replace('            setEditingBrokerId(null);\n            setBrokerForm', '            setEditingBrokerId(null);\n            setEditingPropId(null);\n            setForm({ prop_stage_id: \'\', amount: \'\', destination_account_id: \'\', withdrawal_date: \'\', note: \'\' });\n            setBrokerForm')
replace('setShowForm((value) => editingBrokerId !== null || !value);', 'setShowForm((value) => editingBrokerId !== null || editingPropId !== null || !value);')
replace('setTab(k); setShowForm(false); setEditingBrokerId(null);', 'setTab(k); setShowForm(false); setEditingBrokerId(null); setEditingPropId(null);')
replace('>ثبت برداشت جدید</h3>', ">{editingPropId !== null ? 'ویرایش برداشت پراپ' : 'ثبت برداشت جدید'}</h3>")
replace('وضعیت اولیه: «درخواست‌شده» — با دکمه‌های جدول → تأیید → پردازش → دریافت', "{editingPropId !== null ? 'اصلاح برداشت دریافت‌شده، موجودی مقصد و گزارش درآمد را هم اصلاح می‌کند.' : 'وضعیت اولیه: «درخواست‌شده» — تأیید → پردازش → دریافت'}")
replace('<select className={inputCls} value={form.prop_stage_id}', '<select className={inputCls} value={form.prop_stage_id} disabled={editingPropId !== null}')
s = s.replace('💵 مبلغ</label>', '💵 مبلغ واقعی دریافتی</label>', 1)
replace('type="number" className={inputCls} value={form.amount}', 'type="number" min="0.01" step="any" className={inputCls} value={form.amount}')
replace("{saving ? '⏳ در حال ثبت…' : '💾 ثبت برداشت'}", "{saving ? '⏳ در حال ذخیره…' : editingPropId !== null ? 'ذخیرهٔ اصلاحات' : '💾 ثبت برداشت'}")
replace('onClick={() => openBrokerEdit(r)}', 'onClick={() => isProp ? openPropEdit(r) : openBrokerEdit(r)}')
replace("{!isProp && (\n                                <button\n                                  onClick={() => isProp ? openPropEdit(r) : openBrokerEdit(r)}", "{(\n                                <button\n                                  onClick={() => isProp ? openPropEdit(r) : openBrokerEdit(r)}")
p.write_bytes(s.encode('utf-8'))

p = root / 'backend/app/api/prop.py'
s = p.read_bytes().decode('utf-8')
start = s.index('    def reject_empty_required_fields(self):')
end = s.index('        return self', start)
block = s[start:end]
line_start = block.index('                raise ValueError(')
block = block[:line_start] + '                raise ValueError("مبلغ، حساب مقصد و ارز برداشت نمی‌توانند خالی باشند")\n'
s = s[:start] + block + s[end:]
p.write_bytes(s.encode('utf-8'))
