const fs = require('node:fs');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const { JSDOM, VirtualConsole } = require('../frontend/node_modules/jsdom');

const protectedPaths = ['frontend/src/components/ui/KpiCard.tsx', 'frontend/src/index.css', 'frontend/src/pages/DashboardPage.tsx'];
const hash = path => crypto.createHash('sha256').update(fs.readFileSync(path)).digest('hex');
const before = protectedPaths.map(hash);
const path = 'tmp/dashboard-light-preview.fragment.html';
const source = fs.readFileSync(path, 'utf8');
const dom = new JSDOM(source);
const d = dom.window.document;
const root = d.getElementById('mok-preview');
const main = root.querySelector('main');
const el = (tag, className) => { const node = d.createElement(tag); node.className = className; return node; };
const header = main.querySelector('.header');
const filters = main.querySelector('.filterbar');
const kpis = main.querySelector('.kpis');
const today = main.querySelector('.today');
const prop = d.getElementById('prop');
const yesterday = main.querySelector('.two > article:first-child');
const equity = d.getElementById('equity-chart').closest('article');
const donut = d.getElementById('donut-rate').closest('article');
const distribution = d.getElementById('distribution-chart').closest('article');
const real = main.querySelector('.realgrid');
const financial = main.querySelector('.finance');
const trend = main.querySelector('.trend-row');
const backtest = d.getElementById('backtest').parentElement;
const tables = d.getElementById('trades');
const analyticsTitle = d.getElementById('analytics');
const footer = main.querySelector('footer');

const names = ['سود و زیان خالص','نرخ برد','فاکتور سود','افت سرمایه','معاملات بسته'];
kpis.querySelectorAll('.metric-head > span:first-child').forEach((n,i) => { n.textContent=names[i];n.removeAttribute('dir'); });
kpis.querySelector('.metric-note').textContent='در بازه و دامنهٔ انتخاب‌شده';
header.querySelector('.eyebrow').textContent='داشبورد معاملاتی';
header.querySelector('h1').textContent='عملکردت در یک نگاه';
analyticsTitle.querySelector('h2').lastChild.textContent=' روند سرمایه و وضعیت امروز';

const overview = el('div','grid overview');
equity.classList.add('equity-focus');
today.classList.add('today-compact');
prop.classList.add('prop-compact');
overview.append(equity, today, prop);

function disclosure(id, title, description, content) {
 const section = el('details','disclosure'); section.id=id;
 const summary = el('summary','disclosure-summary');
 const label = el('span','disclosure-label');
 const strong = d.createElement('strong');strong.textContent=title;
 const sub=d.createElement('span');sub.textContent=description;
 label.append(strong,sub);const chevron=el('span','disclosure-chevron');chevron.textContent='⌄';chevron.setAttribute('aria-hidden','true');
 summary.append(label,chevron);const body=el('div','disclosure-body');body.append(...content);section.append(summary,body);return section;
}
const realDetails=disclosure('real-details','عملکرد پول واقعی','مرحله ۳ پراپ، بروکر شخصی و روز گذشته',[real,yesterday]);
const analyticalCharts=el('div','grid analytical-charts');analyticalCharts.append(donut,distribution);
const analysisDetails=disclosure('analysis-details','تحلیل و بک‌تست','برد و باخت، توزیع سود و زیان و پیشرفت اهداف',[analyticalCharts,backtest]);
const financeDetails=disclosure('finance','جزئیات مالی','موجودی حساب‌ها، جریان نقدی و دارایی شخصی',[financial,trend]);
const detailHeading=el('div','section-title');const detailTitle=d.createElement('h2');detailTitle.textContent='جزئیات بیشتر';detailHeading.append(detailTitle);
main.replaceChildren(header,filters,kpis,analyticsTitle,overview,tables,detailHeading,realDetails,analysisDetails,financeDetails,footer);

// Keep four frequent time ranges visible; retain the remaining ranges in a native disclosure.
const ranges=d.getElementById('range-controls');
const more=el('details','filter-more');const moreSummary=d.createElement('summary');moreSummary.textContent='بازه‌های بیشتر';const moreBody=el('div','filter-more-body');
['yesterday','quarter','year'].forEach(key=>moreBody.append(ranges.querySelector(`[data-range="${key}"]`)));
more.append(moreSummary,moreBody);ranges.append(more);

// Keep the blue vertical sidebar, with secondary destinations available under one disclosure.
const nav=root.querySelector('.sidebar nav');
const allLinks=Array.from(nav.querySelectorAll('a'));
const keep=['داشبورد','معاملات','تحلیل','مالی','پراپ'];
const primary=keep.map(label=>allLinks.find(a=>a.textContent.trim()===label));
const secondary=allLinks.filter(a=>!primary.includes(a));
allLinks.forEach(a=>a.setAttribute('aria-label',a.textContent.trim()));
primary[2].href='#analysis-details';
const navMore=el('details','nav-more');const navSummary=d.createElement('summary');navSummary.textContent='سایر بخش‌ها';navSummary.setAttribute('aria-label','سایر بخش‌ها');navMore.append(navSummary,...secondary);
nav.replaceChildren(...primary,navMore);

const css=el('style','');css.textContent=`
#mok-preview .header{margin-bottom:23px}
#mok-preview .overview{grid-template-columns:minmax(0,1.65fr) minmax(0,1fr);align-items:stretch;margin-top:0}
#mok-preview .equity-focus{grid-row:span 2;display:flex;flex-direction:column;justify-content:space-between}
#mok-preview .equity-focus #equity-chart{margin:auto 0}
#mok-preview .equity-focus .chart-svg{min-height:230px}
#mok-preview .today-compact{margin:0;display:block;padding:22px 24px}
#mok-preview .today-compact .value{font-size:30px;margin:8px 0}
#mok-preview .today-compact .today-detail{gap:9px 18px;font-size:10px}
#mok-preview .today-compact .periods{border:0;border-top:1px solid #dfe8f6;margin-top:17px;padding:12px 0 0;gap:8px}
#mok-preview .today-compact .periods .period{background:transparent;border:0;box-shadow:none;padding:0}
#mok-preview .today-compact .period .amount{font-size:14px}
#mok-preview .prop-compact{padding:20px 24px}
#mok-preview .prop-compact .panel-head{margin-bottom:12px}
#mok-preview .prop-compact .prop-grid{gap:16px}
#mok-preview .prop-compact .progress-info{margin-top:10px}
#mok-preview .prop-compact .prop-summary{padding-right:15px}
#mok-preview .metric{border-top-width:2px;background:linear-gradient(150deg,#fff 65%,var(--tint))}
#mok-preview .tables{margin-top:25px}
#mok-preview .disclosure{margin:12px 0;border:1px solid #dce5f2;border-radius:12px;background:#ffffff85}
#mok-preview .disclosure-summary{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:17px 20px;cursor:pointer;list-style:none}
#mok-preview .disclosure-summary::-webkit-details-marker{display:none}
#mok-preview .disclosure-label{display:flex;align-items:center;gap:17px;flex-wrap:wrap}
#mok-preview .disclosure-label strong{font-size:12px;font-weight:600}
#mok-preview .disclosure-label>span{font-size:10px;color:var(--muted)}
#mok-preview .disclosure-chevron{font-size:18px;color:#6b83a5;transition:transform .15s}
#mok-preview .disclosure[open] .disclosure-chevron{transform:rotate(180deg)}
#mok-preview .disclosure[open]{background:#f7f9fd}
#mok-preview .disclosure-body{padding:8px 20px 22px}
#mok-preview .disclosure-body>.surface{margin-top:20px}
#mok-preview .analytical-charts{grid-template-columns:repeat(2,minmax(0,1fr))}
#mok-preview .analytical-charts .donut-wrap{max-width:130px}
#mok-preview .filter-more{font-size:11px;color:var(--muted)}
#mok-preview .filter-more>summary{cursor:pointer;padding:5px 10px;border-radius:7px}
#mok-preview .filter-more[open]{flex-basis:100%}
#mok-preview .filter-more-body{display:flex;gap:4px;flex-wrap:wrap;padding-top:7px}
#mok-preview .nav-more{margin-top:19px;border-top:1px solid #ffffff20;padding-top:13px}
#mok-preview .nav-more>summary{font-size:11px;padding:10px 15px;cursor:pointer;color:#c1d3f0}
#mok-preview .sidebar .nav-more .nav-item{font-size:12px}
#mok-preview summary:focus-visible{outline:3px solid #88b6ff;outline-offset:3px;border-radius:8px}
@media(max-width:1100px){#mok-preview .overview{grid-template-columns:1fr}#mok-preview .equity-focus{grid-row:auto}#mok-preview .equity-focus .chart-svg{min-height:0}#mok-preview .today-compact .periods{border-top:1px solid #dfe8f6}}
@media(max-width:650px){#mok-preview .analytical-charts{grid-template-columns:1fr}#mok-preview .disclosure-summary{padding:15px}#mok-preview .disclosure-label{gap:4px;display:grid}#mok-preview .disclosure-body{padding:6px 12px 17px}#mok-preview .today-compact,#mok-preview .prop-compact{padding:19px 16px}#mok-preview .today-compact .period .amount{font-size:12px}}
@media(max-width:540px){#mok-preview .nav-more>summary{font-size:0;padding:10px 0;text-align:center;list-style:none}#mok-preview .nav-more>summary:after{content:'···';font-size:21px}#mok-preview .sidebar .nav-more .nav-item{font-size:0}#mok-preview .overview{gap:20px}}
@media(prefers-reduced-motion:reduce){#mok-preview *{transition:none!important}}
`;
d.head.append(css);
const navigation=d.createElement('script');navigation.textContent=`
(() => {
 const root=document.getElementById('mok-preview');
 function reveal(hash){if(!hash||hash.length<2)return;const target=document.getElementById(hash.slice(1));if(!target)return;let node=target;while(node&&node!==root){if(node.tagName==='DETAILS')node.open=true;node=node.parentElement;}}
 root.querySelectorAll('a[href^="#"]').forEach(a=>a.addEventListener('click',()=>reveal(a.hash)));
 reveal(window.location.hash);
})();`;
d.body.append(navigation);
const output=d.head.innerHTML+'\n'+d.body.innerHTML;
fs.writeFileSync(path,output,'utf8');dom.window.close();

const errors=[];const vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e.message));
const check=new JSDOM(output,{runScripts:'dangerously',virtualConsole:vc,url:'https://preview.local/'});
const doc=check.window.document;
assert.deepEqual(errors,[]);
assert.equal(doc.querySelectorAll('main article.surface').length,25);
assert.equal(doc.querySelectorAll('main>.disclosure:not([open])').length,3);
assert.equal(doc.querySelectorAll('.sidebar nav>a').length,5);
assert.equal(doc.querySelector('.overview').children.length,3);
assert.equal(doc.querySelectorAll('[data-range]').length,7);
doc.querySelector('[data-range="month"]').click();assert.match(doc.getElementById('kpi-pnl').textContent,/1,240/);
doc.querySelector('.sidebar a[href="#finance"]').click();assert.ok(doc.getElementById('finance').open);
doc.querySelector('.sidebar a[href="#analysis-details"]').click();assert.ok(doc.getElementById('analysis-details').open);
doc.getElementById('sort-pnl').click();assert.equal(doc.querySelector('#recent-rows tr').children[4].textContent,'+410.00');
for(const a of doc.querySelectorAll('a[href^="#"]'))assert.ok(doc.getElementById(a.hash.slice(1)),a.hash);
assert.deepEqual(protectedPaths.map(hash),before);
check.window.close();
console.log('PASS: all existing cards preserved, three collapsed detail sections, five primary sidebar links, working filters, navigation reveal and sorting. Application files unchanged.');
