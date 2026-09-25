# 📊 تحلیل بخش استراتژی‌ها و پراپ — MokTradeDesk

**تاریخ:** ۱۴۰۴/۰۷/۰۳
**روش:** بررسی کد واقعی (backend models, APIs, services, frontend pages)

---

## ۱. بخش استراتژی‌ها (Strategies)

### مدل‌های موجود ✅
| مدل | جدول | فیلدهای اصلی | وضعیت |
|:---|:---|:---|:---:|
| `Strategy` | `strategies` | id, name, description, created_at | ✅ |
| `StrategyVersion` | `strategy_versions` | id, strategy_id, version_name, rules_note, status, **forked_from_version_id** | ✅ |
| `AnalysisResult` | `analysis_results` | version_id, ۲۰+ متریک | ✅ |
| `AnalysisRun` | `analysis_runs` | version_id, ۱۴ متریک + full_metrics JSON | ✅ |
| `CustomTimeInterval` | `custom_time_intervals` | name, symbol, start_hour, start_minute, end_hour, end_minute, label, priority | ✅ |
| `TimePoint` | `time_points` | symbol, hour, minute, label | ✅ |
| `SymbolMapping` | `symbol_mappings` | original_symbol, canonical_symbol | ✅ |

### APIهای موجود ✅
| Method | Path | عملکرد | وضعیت |
|:---|:---|:---|:---:|
| GET/POST | `/api/strategies/` | لیست/ایجاد استراتژی | ✅ |
| GET/PATCH/DELETE | `/api/strategies/{id}` | جزئیات/ویرایش/حذف استراتژی | ✅ |
| GET | `/api/strategies/versions/all` | لیست همه نسخه‌ها | ✅ |
| GET/POST | `/api/strategies/{id}/versions` | لیست/ایجاد نسخه | ✅ |
| PATCH/DELETE | `/api/strategies/versions/{id}` | ویرایش/حذف نسخه | ✅ |
| GET | `/api/strategies/versions/{id}/trades` | معاملات نسخه | ✅ |

### صفحه Frontend ✅
- **StrategyPage.tsx** (۵۷۸ خط) — کامل با لیست، جستجو، CRUD، ۱۰ وضعیت رنگی، نمایش تعداد معاملات

### قابلیت‌های ناقص ⚠️
| # | قابلیت | وضعیت | توضیح |
|:---|:---|:---:|:---|
| ۱ | **Fork نسخه** | ⚠️ ستون هست، دکمه نیست | `forked_from_version_id` در مدل هست ولی دکمه/API ندارد |
| ۲ | **Rules Builder** | ❌ وجود ندارد | `rules_note` فقط textarea ساده |
| ۳ | **مقایسه گرافیکی استراتژی‌ها** | ❌ وجود ندارد | فقط ComparisonPage برای نسخه‌ها |

---

## ۲. بخش پراپ (Prop)

### مدل‌های موجود ✅
| مدل | جدول | فیلدهای اصلی | وضعیت |
|:---|:---|:---|:---:|
| `PropFirm` | `prop_firms` | id, name, default_profit_share, website, notes | ✅ |
| `PropFirmDefaultRules` | `prop_firm_default_rules` | prop_firm_id, stage_type, profit_target, max_daily_dd, max_total_dd, min_trading_days | ✅ |
| `PropAccount` | `prop_accounts` | id, prop_firm_id, account_label, currency, is_active | ✅ |
| `PropStage` | `prop_stages` | stage_type, status, profit_target, max_daily_dd, max_total_dd, min_trading_days, initial_balance, ... | ✅ |
| `PropWithdrawal` | `prop_withdrawals` | prop_stage_id, amount, withdrawal_date, note | ✅ |
| `PropCost` | `prop_costs` | prop_account_id, cost_type, amount, is_refunded | ✅ |
| `PropAlert` | `prop_alerts` | prop_stage_id, message, is_read | ✅ |

### Service ✅
- **PropRuleEngine** — کامل با `evaluate_stage()` و `validate_withdrawal()`

### APIهای موجود ✅
۱۴ API شامل: CRUD شرکت/حساب/مرحله، Check Pass, Pass/Fail, Withdraw, Costs, Analytics

### صفحه Frontend ✅
- **PropPage.tsx** (۱۳۲۱ خط) — تحلیل، شرکت‌ها، حساب‌ها، Check/Pass/Fail/Edit/Withdraw با درصد↔دلار

### قابلیت‌های ناقص ⚠️
| # | قابلیت | وضعیت | توضیح |
|:---|:---|:---:|:---|
| ۱ | **PropFirmDefaultRules** | ⚠️ مدل هست، استفاده نمی‌شود | هنگام Create Account قوانین پیش‌فرض خوانده نمی‌شود |
| ۲ | **PropAlert** | ❌ مدل هست، UI ندارد | هشدارهای خودکار فعال نیست |
| ۳ | **Multi-Account Dashboard** | ❌ | مقایسه چند حساب پراپ وجود ندارد |

---

## ۳. اولویت‌بندی قابلیت‌های جدید

| اولویت | قابلیت | بخش | تخمین |
|:---:|:---|:---|:---:|
| 🟡 P1 | Fork Version | Strategy | ۱-۲ ساعت |
| 🟡 P1 | PropFirmDefaultRules | Prop | ۳۰ دقیقه |
| 🟢 P2 | PropAlert | Prop | ۱-۲ ساعت |
| 🟢 P2 | Multi-Account Prop View | Prop | ۳-۴ ساعت |
| 🟢 P2 | Rules Builder | Strategy | ۴-۶ ساعت |
| 🟢 P3 | مقایسه گرافیکی استراتژی‌ها | Strategy | ۲-۳ ساعت |

---

*این سند بر اساس بررسی مستقیم کد واقعی در تاریخ ۱۴۰۴/۰۷/۰۳ تهیه شده است.*