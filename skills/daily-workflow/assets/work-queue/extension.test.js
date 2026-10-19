import {afterEach, describe, expect, it, vi} from 'vitest';
import {activate} from './extension.js';

const response = data => ({ok:true,json:async()=>data});
const item = n => ({number:n,title:`New request ${n}`,html_url:`https://github.com/example/project/pull/${n}`,state:'open',draft:false,user:{login:'author'}});
function mount(snapshot={githubUser:'example-user',linear:[],review:[],align:[],slack:[],actions:[]}){
  let page;
  const unregister=vi.fn();
  const host={apiVersion:'1',registerPage:vi.fn((id,fn)=>{page=fn;return unregister;})};
  expect(activate(host,snapshot)).toBe(unregister);
  const container=document.createElement('div');
  const cleanup=page({container,path:''});
  return {container,cleanup};
}
async function settle(){for(let i=0;i<12;i++) await new Promise(resolve=>setTimeout(resolve,0));}
afterEach(()=>vi.unstubAllGlobals());

describe('independent GitHub review discovery',()=>{
  it('shows a spinner instead of snapshot rows, discovers new requests and refreshes',async()=>{
    let finish;
    const fetcher=vi.fn(()=>new Promise(resolve=>{finish=resolve;}));vi.stubGlobal('fetch',fetcher);
    const {container,cleanup}=mount();
    expect(container.querySelector('[role="status"]').textContent).toContain('Loading');
    expect(container.querySelector('.spinner')).not.toBeNull();
    expect(container.querySelector('[aria-busy="true"]')).not.toBeNull();
    expect(container.querySelector('table').textContent).not.toContain('18311');
    finish(response({items:[item(999)],total_count:1,incomplete_results:false}));await settle();
    expect(container.querySelector('table').textContent).toContain('New request 999');
    expect(container.querySelector('.summary').textContent).toContain('1 awaiting review');
    expect(container.querySelector('.spinner')).toBeNull();
    expect(fetcher.mock.calls[0][0]).toContain('/search/issues?');
    expect(decodeURIComponent(fetcher.mock.calls[0][0])).toContain('review-requested:example-user');
    expect(fetcher.mock.calls[0][1].cache).toBe('no-store');
    container.querySelector('button[aria-label="Refresh review requests"]').click();
    expect(container.querySelector('.spinner')).not.toBeNull();
    finish(response({items:[],total_count:0,incomplete_results:false}));await settle();
    expect(container.querySelector('table').textContent).toContain('No public PRs');cleanup();
  });
  it('loads every page and excludes drafts and closed PRs',async()=>{
    vi.stubGlobal('fetch',vi.fn(async url=>response(String(url).includes('page=2')?{items:[item(101)],total_count:101,incomplete_results:false}:{items:[...Array.from({length:98},(_,n)=>item(n+1)),{...item(99),draft:true},{...item(100),state:'closed'}],total_count:101,incomplete_results:false})));
    const {container,cleanup}=mount();await settle();
    expect(fetch).toHaveBeenCalledTimes(2);
    expect(container.querySelector('table').textContent).toContain('New request 101');
    expect(container.querySelector('table tbody').children.length).toBe(99);cleanup();
  });
  it.each(['failure','incomplete','malformed','cap'])('labels snapshot fallback on %s, never claiming complete discovery',async kind=>{
    vi.stubGlobal('fetch',vi.fn(async()=>kind==='failure'?{ok:false,status:403}:response(kind==='incomplete'?{items:[],total_count:0,incomplete_results:true}:kind==='cap'?{items:[],total_count:1001,incomplete_results:false}:{})));
    const {container,cleanup}=mount();await settle();
    expect(container.querySelector('[role="status"]').textContent).toContain('Snapshot fallback');
    expect(container.querySelector('.summary').textContent).toContain('snapshot');
    expect(container.querySelector('button[aria-label="Refresh review requests"]').disabled).toBe(false);cleanup();
  });
  it('aborts pending requests on disposal and removes style and DOM',async()=>{
    let finish,signal;vi.stubGlobal('fetch',vi.fn((url,opts)=>{signal=opts.signal;return new Promise(resolve=>{finish=resolve;});}));
    const {container,cleanup}=mount();cleanup();expect(signal.aborted).toBe(true);
    finish(response({items:[item(999)],total_count:1,incomplete_results:false}));await settle();expect(container.childElementCount).toBe(0);
  });
  it('keeps Linear filtering functional',()=>{
    vi.stubGlobal('fetch',vi.fn(()=>new Promise(()=>{})));
    const {container,cleanup}=mount();const search=container.querySelector('input');search.value='unmatched';search.dispatchEvent(new Event('input'));expect(container.textContent).toContain('0 / 0 tickets');cleanup();
  });
  it('rejects unsupported host API',()=>{expect(()=>activate({apiVersion:'2'})).toThrow(/host API 1/);});
});

 describe('optional agent recommendations',()=>{
  const url='https://github.com/example/project/pull/999';
  const snapshot={githubUser:'example-user',align:[{pr:{label:'PR 999',url},issue:{label:'None confirmed',url:null},assigned:'N/A',linear:{label:'Unknown',url:null},action:'Confirm tracking'}]};
  it('renders no agent UI when no recommendation exists',()=>{
    vi.stubGlobal('fetch',vi.fn(()=>new Promise(()=>{})));
    const {container,cleanup}=mount(snapshot);expect(container.querySelector('.recommendation')).toBeNull();cleanup();
  });
  it('keeps deterministic rows and safely displays explicit recommendations',async()=>{
    vi.stubGlobal('fetch',vi.fn(async()=>response({items:[item(999)],total_count:1,incomplete_results:false})));
    const rec={summary:'Reuse tracker <img src=x onerror=alert(1)>',rationale:'Intentional umbrella',assessedAt:'2026-10-16T10:00:00Z',headSha:'abc123',links:[{label:'Canonical issue',url:'https://github.com/example/project/issues/1'}]};
    const {container,cleanup}=mount({...snapshot,recommendations:{[url]:rec}});await settle();
    expect(container.querySelectorAll('.recommendation')).toHaveLength(2);
    const block=container.querySelector('.recommendation');expect(block.textContent).toContain('Agent recommendation');expect(block.textContent).toContain(rec.summary);expect(block.textContent).toContain(rec.assessedAt);expect(block.textContent).toContain('abc123');expect(block.querySelector('img')).toBeNull();expect(block.querySelector('a').href).toBe(rec.links[0].url);
    expect(container.textContent).toContain('Confirm tracking');expect(container.textContent).toContain('New request 999');cleanup();
  });
 });

describe('canonical issue alignment',()=>{
  const row=(number,issue,linear)=>({pr:{label:`PR ${number}`,url:`https://github.com/example/project/pull/${number}`},issue,linear,assigned:'N/A',action:'Check tracking'});
  it('omits canonical Linear and GitHub trackers but keeps unverified candidates actionable',()=>{
    vi.stubGlobal('fetch',vi.fn(()=>new Promise(()=>{})));
    const none={label:'None confirmed',url:null};
    const {container,cleanup}=mount({githubUser:'example-user',align:[
      row(1,none,{label:'EX-1 — Canonical umbrella',url:'https://linear.app/example/issue/EX-1/canonical-umbrella'}),
      row(2,{label:'Umbrella',url:'https://github.com/example/project/issues/10'},none),
      row(3,none,{label:'Possible EX-2 — Needs verification',url:null}),
      row(4,none,{label:'Related web page',url:'https://example.com/issue/EX-2'}),
      row(5,none,{label:'Not verified',url:'https://linear.app/example/issue/EX-3/possible'})
    ]});
    const card=[...container.querySelectorAll('.card')].find(x=>x.textContent.includes('PRs needing issue alignment'));
    expect(card).toBeDefined();
    expect([...card.querySelectorAll('tbody tr')].map(x=>x.querySelector('a').textContent)).toEqual(['PR 3','PR 4','PR 5']);
    expect(container.querySelector('.summary').textContent).toContain('3 need tracking');cleanup();
  });
});

describe('Linear approval boundary',()=>{
  it('fails closed without executing commands or retrieving secrets',async()=>{
    const {discoverLinear}=await import('./extension.js');
    const request=vi.fn();
    await expect(discoverLinear({agentServer:{request}})).rejects.toThrow(/approved managed backend/);
    expect(request).not.toHaveBeenCalled();
  });
});


describe('Linear triage ordering',()=>{
  it('puts unprioritized tickets first, then priority and earliest due date, without mutating input',()=>{
    vi.stubGlobal('fetch',vi.fn(()=>new Promise(()=>{})));
    const row=(id,priorityNum,due)=>({id,title:id,url:'https://linear.app/example/issue/'+id,priorityNum,priority:['No priority','Urgent','High','Medium','Low'][priorityNum],due,workspace:'Example',pr:{label:'No',url:null},ci:'unknown',review:'unknown',evidence:'unknown',context:''});
    const linear=[row('HIGH',2),row('NONE-LATE',0,'2026-10-22'),row('URGENT',1),row('NONE-UNDATED',0),row('NONE-EARLY',0,'2026-10-01'),row('LOW',4),row('MEDIUM',3)];
    const original=[...linear];
    const {container,cleanup}=mount({linear,review:[],align:[],slack:[],actions:[]});
    const card=[...container.querySelectorAll('.card')].find(x=>x.textContent.includes('Linear priority walkthrough'));
    const ids=()=>[...card.querySelectorAll('tbody tr td:first-child a')].map(x=>x.textContent.split(' — ')[0]);
    expect(ids()).toEqual(['NONE-EARLY','NONE-LATE','NONE-UNDATED','URGENT','HIGH','MEDIUM','LOW']);
    expect(linear).toEqual(original);
    const filter=container.querySelector('select[aria-label="Filter by priority"]');filter.value='No priority';filter.dispatchEvent(new Event('input'));
    expect(ids()).toEqual(['NONE-EARLY','NONE-LATE','NONE-UNDATED']);cleanup();
  });
});
