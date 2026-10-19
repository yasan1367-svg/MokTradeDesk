const fs=require('node:fs');
const crypto=require('node:crypto');
const assert=require('node:assert/strict');
const {JSDOM,VirtualConsole}=require('../frontend/node_modules/jsdom');
const protectedPaths=['frontend/src/components/ui/KpiCard.tsx','frontend/src/index.css','frontend/src/pages/DashboardPage.tsx'];
const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const before=protectedPaths.map(hash);
const path='tmp/dashboard-light-preview.fragment.html';
let source=fs.readFileSync(path,'utf8');
const oldScale='max=Math.ceil(Math.max(...points)/5000)*5000,min=0';
const newScale='peak=Math.max(...points),scale=10**Math.floor(Math.log10(Math.max(peak,1))),max=Math.ceil(peak/scale)*scale,min=0';
assert.ok(source.includes(oldScale));source=source.replace(oldScale,newScale);
const dom=new JSDOM(source);const d=dom.window.document;const main=d.querySelector('main');
const prop=d.getElementById('prop');const backtest=d.getElementById('backtest');
const oldBacktestParent=backtest.parentElement;
const pair=d.createElement('section');pair.className='grid paired-cards';pair.setAttribute('aria-label','وضعیت پراپ و عملکرد بک‌تست');
pair.append(prop,backtest);main.querySelector('.overview').after(pair);
oldBacktestParent.className='goal-detail';
const summary=d.querySelector('#analysis-details .disclosure-label');summary.querySelector('strong').textContent='تحلیل تکمیلی';summary.querySelector('span').textContent='برد و باخت، توزیع سود و زیان و اهداف';

const style=d.createElement('style');style.textContent=`
#mok-preview{--muted:#60718a}
#mok-preview .sidebar{background:linear-gradient(160deg,#0c1933 0%,#081329 55%,#050d1e 100%);border-left-color:#203454;box-shadow:-7px 0 22px #06112720;scrollbar-color:#304664 #081329}
#mok-preview .sidebar .nav-item{color:#b5c7e2}
#mok-preview .sidebar .nav-item:hover{background:#142440;color:#fff}
#mok-preview .sidebar .nav-item.active{background:#182e51;color:#f3f7ff;border:1px solid #2b4771;box-shadow:inset 3px 0 0 #6095e6,0 4px 10px #00000020}
#mok-preview .sidebar .nav-dot{background:#78a8ef}
#mok-preview .sidebar .brand small,#mok-preview .sidebar-foot small{color:#93a9c9}
#mok-preview .sidebar .brand-mark{background:#152c50;border-color:#2c4770;color:#97bcf8}
#mok-preview .nav-more>summary{color:#9eb4d3}
#mok-preview .overview{grid-template-columns:minmax(0,1.5fr) minmax(0,1fr)}
#mok-preview .equity-focus{grid-row:auto;justify-content:center}
#mok-preview .equity-focus .chart-svg{min-height:0}
#mok-preview .paired-cards{grid-template-columns:repeat(2,minmax(0,1fr));align-items:stretch;margin-top:24px}
#mok-preview .paired-cards>.surface{height:100%;padding:22px 24px}
#mok-preview .paired-cards .panel-head{margin-bottom:17px;min-height:30px}
#mok-preview #backtest .backtest-stats{margin-top:20px;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}
#mok-preview #backtest .stat-number{font-size:22px}
#mok-preview #backtest .footnote{margin-top:20px}
#mok-preview .goal-detail{margin-top:23px}
#mok-preview .goal-detail>.surface{padding:21px 23px}
#mok-preview .label,#mok-preview .sub,#mok-preview .metric-note,#mok-preview .footnote{font-size:11px}
#mok-preview td{font-size:12px}
#mok-preview .metric-head{font-size:12px}
#mok-preview .value{letter-spacing:-.5px}
#mok-preview .surface,#mok-preview .disclosure{scroll-margin-top:20px}
#mok-preview .table-sort{padding:3px 0}
#mok-preview .metric .value small{display:inline-block}
@media(max-width:1250px){#mok-preview #backtest .backtest-stats{grid-template-columns:repeat(2,minmax(0,1fr))}#mok-preview .paired-cards .prop-grid{grid-template-columns:1fr}#mok-preview .paired-cards .prop-summary{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;border:0;border-top:1px solid var(--line);padding:12px 0 0}#mok-preview .paired-cards .prop-summary .stat-number{margin:0;font-size:19px}}
@media(max-width:950px){#mok-preview .overview{grid-template-columns:1fr}#mok-preview .paired-cards>.surface{padding:19px 18px}#mok-preview .paired-cards .panel-head{align-items:flex-start}#mok-preview .paired-cards .panel-head h3{font-size:12px}#mok-preview .paired-cards .prop-grid>div>div:first-child{flex-wrap:wrap}}
@media(max-width:700px){#mok-preview .paired-cards{grid-template-columns:1fr}#mok-preview #backtest .backtest-stats{grid-template-columns:repeat(2,minmax(0,1fr))}#mok-preview .metric-head{font-size:11px}}
@media(max-width:540px){#mok-preview .sidebar .nav-item.active{border-color:#2b4771}#mok-preview .paired-cards>.surface{padding:19px 16px}#mok-preview .goal-detail>.surface{padding:18px 15px}#mok-preview .today-compact .today-detail{font-size:11px}#mok-preview .period .amount small{font-size:9px}}
`;
d.head.append(style);
const script=d.createElement('script');script.textContent=`
(() => {
 const root=document.getElementById('mok-preview');
 root.querySelectorAll('a[href^="#"]').forEach(a=>a.addEventListener('click',()=>{
   const nav=root.querySelector('.sidebar nav');
   const selected=Array.from(nav.querySelectorAll('a')).find(link=>link.hash===a.hash);
   if(!selected)return;
   nav.querySelectorAll('a').forEach(link=>{link.classList.remove('active');link.removeAttribute('aria-current')});
   selected.classList.add('active');selected.setAttribute('aria-current','location');
 }));
})();`;
d.body.append(script);
const output=d.head.innerHTML+'\n'+d.body.innerHTML;
fs.writeFileSync(path,output,'utf8');dom.window.close();

const errors=[];const vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e.message));
const check=new JSDOM(output,{runScripts:'dangerously',virtualConsole:vc,url:'https://preview.local/'});const doc=check.window.document;
assert.deepEqual(errors,[]);
assert.equal(doc.getElementById('prop').parentElement,doc.getElementById('backtest').parentElement);
assert.ok(!doc.getElementById('backtest').closest('details'));
assert.equal(doc.querySelectorAll('main article.surface').length,25);
assert.equal(doc.querySelector('.overview').children.length,2);
const strategy=doc.getElementById('strategy-select');strategy.value='2';strategy.dispatchEvent(new check.window.Event('change'));assert.equal(doc.querySelector('[data-bt="pnl"]').textContent,'+3,140');
doc.querySelector('[data-range="today"]').click();assert.match(doc.getElementById('kpi-pnl').textContent,/180/);
doc.querySelector('.sidebar a[href="#finance"]').click();assert.ok(doc.getElementById('finance').open);assert.equal(doc.querySelector('.sidebar a.active').hash,'#finance');
const ids=Array.from(doc.querySelectorAll('[id]')).map(n=>n.id);assert.equal(ids.length,new Set(ids).size);
for(const a of doc.querySelectorAll('a[href^="#"]'))assert.ok(doc.getElementById(a.hash.slice(1)),a.hash);
assert.deepEqual(protectedPaths.map(hash),before);
check.window.close();
console.log('PASS: adjacent prop/backtest cards, preserved content, strategy/filter/navigation interactions, unique IDs and unchanged application files.');
