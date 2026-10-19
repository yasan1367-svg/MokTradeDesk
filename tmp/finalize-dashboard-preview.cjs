const fs=require('node:fs');const crypto=require('node:crypto');const assert=require('node:assert/strict');
const {JSDOM,VirtualConsole}=require('../frontend/node_modules/jsdom');
const protectedPaths=['frontend/src/components/ui/KpiCard.tsx','frontend/src/index.css','frontend/src/pages/DashboardPage.tsx'];
const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');const before=protectedPaths.map(hash);
const file='tmp/dashboard-light-preview.fragment.html';const dom=new JSDOM(fs.readFileSync(file,'utf8'));const d=dom.window.document;const root=d.getElementById('mok-preview');const main=root.querySelector('main');
const oldReal=d.getElementById('real-details');const realGrid=oldReal.querySelector('.realgrid');const yesterday=oldReal.querySelector('.disclosure-body>article');
const real=d.createElement('section');real.id='real-details';real.className='real-performance';real.setAttribute('aria-labelledby','real-title');
const heading=d.createElement('div');heading.className='section-title';
const title=d.createElement('h2');title.id='real-title';title.textContent='عملکرد پول واقعی';
const context=d.createElement('span');context.textContent='مرحله ۳ پراپ + بروکر شخصی';heading.append(title,context);real.append(heading,realGrid);
oldReal.remove();main.querySelector('.paired-cards').after(real);
// Keep yesterday available without repeating another metric row on the main surface.
const yesterdayDetails=d.createElement('details');yesterdayDetails.className='yesterday-detail';
const yesterdaySummary=d.createElement('summary');yesterdaySummary.textContent='مقایسه با روز گذشته';yesterdayDetails.append(yesterdaySummary,yesterday);d.querySelector('#analysis-details .disclosure-body').append(yesterdayDetails);

// Both trade tables form the final content section, immediately above the footer.
const tables=d.getElementById('trades');tables.removeAttribute('id');
const open=tables.querySelector('article:last-child');tables.prepend(open);
const tradeSection=d.createElement('section');tradeSection.id='trades';tradeSection.className='trade-section';tradeSection.setAttribute('aria-labelledby','trades-title');
const tradeHeading=d.createElement('div');tradeHeading.className='section-title';const tradeTitle=d.createElement('h2');tradeTitle.id='trades-title';tradeTitle.textContent='معاملات';const tradeSub=d.createElement('span');tradeSub.textContent='معاملات باز و آخرین معاملات بسته‌شده';tradeHeading.append(tradeTitle,tradeSub);tradeSection.append(tradeHeading,tables);main.querySelector('footer').before(tradeSection);

// Make scope and units explicit, so summaries from different sources remain easy to interpret.
root.querySelectorAll('.tables th').forEach(th=>{if(th.textContent.includes('سود / زیان')){const unit=d.createElement('small');unit.className='table-unit';unit.textContent='USDT';th.append(unit)}});
const filterNote=d.createElement('p');filterNote.className='filter-note';filterNote.textContent='فیلترهای بالا برای شاخص‌های اصلی و منحنی سرمایه هستند.';main.querySelector('.filterbar').after(filterNote);
const btNote=d.querySelector('#backtest .footnote');btNote.textContent='نسخهٔ انتخاب‌شده · مستقل از فیلتر معاملات · نمونه';
const style=d.createElement('style');style.textContent=`
#mok-preview .filterbar{margin-bottom:8px}
#mok-preview .filter-note{font-size:11px;color:var(--muted);margin:0 3px 19px}
#mok-preview .section-title{margin:27px 0 15px;gap:12px;flex-wrap:wrap}
#mok-preview .section-title h2{font-size:14px}
#mok-preview .section-title>span{font-size:11px}
#mok-preview .real-performance{margin-top:27px;scroll-margin-top:20px}
#mok-preview .real-performance .real-card{padding:19px 20px}
#mok-preview .real-performance .real-card .mini{width:58px;height:51px}
#mok-preview .real-performance .real-card .value{font-size:23px;font-variant-numeric:tabular-nums}
#mok-preview .trade-section{margin-top:31px;scroll-margin-top:20px}
#mok-preview .trade-section .tables{margin-top:0;grid-template-columns:minmax(0,1fr) minmax(0,1.3fr)}
#mok-preview .tables .panel-head{margin-bottom:15px}
#mok-preview .table-unit{display:block;color:var(--muted);font-size:9px;font-weight:400;direction:ltr;text-align:right}
#mok-preview .tables td.positive,#mok-preview .tables td.negative{font-weight:600}
#mok-preview .tables .numeric{font-variant-numeric:tabular-nums}
#mok-preview .yesterday-detail{margin-top:20px;border-top:1px solid #dde6f3;padding-top:14px}
#mok-preview .yesterday-detail>summary{font-size:12px;color:var(--muted);padding:6px 0;cursor:pointer}
#mok-preview .yesterday-detail>article{margin-top:14px}
#mok-preview .disclosure-summary:hover{background:#f0f5fd;border-radius:12px}
#mok-preview .disclosure-summary:focus-visible,#mok-preview .yesterday-detail>summary:focus-visible{outline:3px solid #88b6ff;outline-offset:3px}
#mok-preview .footer{border-top:1px solid #dbe4f1;padding-top:18px;margin-top:30px}
@media(max-width:1200px){#mok-preview .trade-section .tables{grid-template-columns:1fr}}
@media(max-width:540px){#mok-preview .real-performance .real-card{padding:18px 15px}#mok-preview .real-performance .real-card .value{font-size:21px}#mok-preview .real-performance .real-card .mini{width:51px}#mok-preview .section-title h2{font-size:13px}#mok-preview .section-title>span{font-size:10px}#mok-preview .filter-note{font-size:10px}}
`;
d.head.append(style);
const output=d.head.innerHTML+'\n'+d.body.innerHTML;fs.writeFileSync(file,output,'utf8');dom.window.close();
const errors=[];const vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e.message));const test=new JSDOM(output,{runScripts:'dangerously',virtualConsole:vc,url:'https://preview.local/'});const doc=test.window.document;
assert.deepEqual(errors,[]);assert.equal(doc.querySelectorAll('main article.surface').length,25);
const mainChildren=Array.from(doc.querySelector('main').children);const realIndex=mainChildren.indexOf(doc.getElementById('real-details'));const tradeIndex=mainChildren.indexOf(doc.getElementById('trades'));
assert.ok(realIndex<tradeIndex);assert.ok(!doc.getElementById('real-details').closest('details'));assert.equal(mainChildren[mainChildren.length-2].id,'trades');assert.equal(mainChildren.at(-1).tagName,'FOOTER');
assert.equal(doc.getElementById('prop').parentElement,doc.getElementById('backtest').parentElement);
doc.querySelector('[data-range="month"]').click();assert.match(doc.getElementById('kpi-pnl').textContent,/1,240/);
const version=doc.getElementById('strategy-select');version.value='2';version.dispatchEvent(new test.window.Event('change'));assert.equal(doc.querySelector('[data-bt="pnl"]').textContent,'+3,140');
doc.querySelector('.sidebar a[href="#finance"]').click();assert.ok(doc.getElementById('finance').open);
doc.getElementById('sort-pnl').click();assert.equal(doc.querySelector('#recent-rows tr').children[4].textContent,'+410.00');
const ids=Array.from(doc.querySelectorAll('[id]')).map(n=>n.id);assert.equal(ids.length,new Set(ids).size);for(const a of doc.querySelectorAll('a[href^="#"]'))assert.ok(doc.getElementById(a.hash.slice(1)),a.hash);
assert.deepEqual(protectedPaths.map(hash),before);test.window.close();console.log('PASS: real performance visible above trades; trade tables last; prop/backtest adjacent; 25 cards retained; filters, strategy, sorting and navigation work; application files unchanged.');
