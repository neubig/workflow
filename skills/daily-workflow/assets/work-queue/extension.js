const DATA = {
  "review": [],
  "align": [],
  "slack": [],
  "linear": [],
  "actions": [],
  "generated": "Not yet populated",
  "source": "Generic template; publish a local workflow snapshot",
  "today": "1970-01-01",
  "githubUser": "example-user",
  "displayName": "Work Queue"
};
const CSS = `
.gwq{color:var(--oh-foreground,#EEF2F7);font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;padding:10px 16px 28px;max-width:1180px;margin:0 auto}
.gwq *{box-sizing:border-box}
.gwq h1{color:var(--oh-contrast,#fff);font-size:18px;margin:0;line-height:1.2}
.gwq h2{color:var(--oh-contrast,#fff);font-size:15px;margin:0 0 4px}
.gwq p,.gwq td,.gwq th{font-size:13px}
.gwq .sub{color:var(--oh-muted,#A3B0C4);font-size:12px;margin:2px 0 0}
.gwq .head{display:flex;flex-wrap:wrap;align-items:baseline;gap:4px 12px}
.gwq .summary{display:flex;flex-wrap:wrap;gap:4px 16px;align-items:center;margin:8px 0 2px;padding:6px 0;border-top:1px solid var(--oh-border-subtle,#383F50);border-bottom:1px solid var(--oh-border-subtle,#383F50);font-size:12px;color:var(--oh-muted,#A3B0C4)}
.gwq .summary b{color:var(--oh-contrast,#fff);font-size:13px}
.gwq .summary .alert b{color:var(--oh-danger,#E76A5E)}
.gwq .card{background:var(--oh-color-base-secondary,#21252F);border:1px solid var(--oh-border-subtle,#383F50);border-radius:12px;padding:12px 14px;margin:10px 0}
.gwq .bar{display:flex;height:6px;border-radius:999px;overflow:hidden;border:1px solid var(--oh-border-subtle,#383F50);flex:1;min-width:120px}
.gwq .bar i{display:block;height:100%}
.gwq .barrow{display:flex;align-items:center;gap:10px;margin:6px 0 2px;color:var(--oh-muted,#A3B0C4);font-size:11px}
.gwq .toolbar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:8px 0}
.gwq input,.gwq select{height:34px;border-radius:8px;border:1px solid var(--oh-border,#4B5468);background:var(--oh-color-base-secondary,#21252F);color:var(--oh-contrast,#fff);padding:0 10px;font-size:13px}
.gwq input{min-width:220px;flex:1}
.gwq .pill{display:inline-block;border:1px solid var(--oh-border,#4B5468);border-radius:999px;padding:2px 8px;font-size:11px;white-space:nowrap}
.gwq .pill.high{border-color:#E76A5E;color:#ffb0a6}.gwq .pill.med{border-color:#C9B974;color:#E8DCA0}.gwq .pill.low{color:var(--oh-muted,#A3B0C4)}.gwq .pill.none{border-style:dashed;color:var(--oh-muted,#A3B0C4)}
.gwq .pill.pass{color:#A5E75E;border-color:#5c8a3a}.gwq .pill.fail{color:#ffb0a6;border-color:#E76A5E}.gwq .pill.unk{color:var(--oh-muted,#A3B0C4)}
.gwq table{border-collapse:collapse;width:100%}
.gwq th{text-align:left;color:var(--oh-muted,#A3B0C4);font-weight:600;padding:7px 6px;border-bottom:1px solid var(--oh-border-subtle,#383F50)}
.gwq td{padding:7px 6px;border-bottom:1px solid var(--oh-border-subtle,#383F50);vertical-align:top;overflow-wrap:anywhere}
.gwq a{color:var(--oh-color-primary,#C9B974);text-decoration:none}.gwq a:hover{text-decoration:underline}
.gwq a:focus-visible,.gwq input:focus-visible,.gwq select:focus-visible,.gwq button:focus-visible{outline:2px solid var(--oh-focus,#fff);outline-offset:2px}
.gwq .scroll{overflow:auto;max-height:560px}
.gwq .recommendation{margin-top:8px;padding:8px;border-left:3px solid var(--oh-color-primary,#C9B974);background:var(--oh-surface-raised,#2C313F);min-width:220px}
.gwq .recommendation summary{cursor:pointer;font-weight:600}
.gwq .recommendation p{margin:6px 0}
.gwq .muted{color:var(--oh-muted,#A3B0C4)}
.gwq button{height:34px;border-radius:8px;border:1px solid var(--oh-border,#4B5468);background:transparent;color:var(--oh-contrast,#fff);padding:0 12px;cursor:pointer}
.gwq button[aria-pressed="true"]{background:var(--oh-color-primary,#C9B974);color:var(--oh-accent-foreground,#0B0E14);border-color:transparent;font-weight:600}
.gwq .spinner{display:inline-block;width:13px;height:13px;margin-right:8px;vertical-align:middle;border:2px solid var(--oh-border,#4B5468);border-top-color:var(--oh-color-primary,#C9B974);border-radius:50%;animation:gwq-spin .8s linear infinite}
@keyframes gwq-spin{to{transform:rotate(360deg)}}
@media (prefers-reduced-motion:reduce){.gwq *{transition:none!important;animation:none!important}}
`;
const PRI_COLORS = {"Urgent":"#E76A5E","High":"#E76A5E","Medium":"#C9B974","Low":"#7E8A9E","No priority":"#4B5468"};
const PRI_ORDER = ["No priority","Urgent","High","Medium","Low"];
function el(tag, cls, text){ const n=document.createElement(tag); if(cls) n.className=cls; if(text!=null) n.textContent=text; return n; }
function link(label, url){ if(!url) return document.createTextNode(label||"—"); const a=document.createElement("a"); a.href=url; a.target="_blank"; a.rel="noopener noreferrer"; a.textContent=label; return a; }
function pill(text, kind){ return el("span","pill "+(kind||""),text); }
function ciKind(ci){ const t=(ci||"").toLowerCase(); if(t.includes("fail")) return "fail"; if(t.includes("pass")||t.includes("success")) return "pass"; return "unk"; }
function isQueueMember(r){ return r.liveState==="OPEN" && r.reviewRequested===true && r.draft!==true; }
function queueDate(r){ return [r.due, r.cycleEnd].filter(Boolean).sort()[0] || "9999"; }

async function discoverReviewRequests(user, signal){
  if(!/^[a-z\d-]+$/i.test(user)) throw new Error("GitHub username is not configured");
  const rows=new Map();
  for(let page=1;page<=10;page++){
    const query=encodeURIComponent("is:pr is:open draft:false review-requested:"+user);
    const response=await fetch("https://api.github.com/search/issues?q="+query+"&sort=updated&order=desc&per_page=100&page="+page,
      {headers:{Accept:"application/vnd.github+json"},signal,cache:"no-store"});
    if(!response.ok) throw new Error("GitHub HTTP "+response.status);
    const result=await response.json();
    if(!Array.isArray(result.items) || !Number.isInteger(result.total_count) || result.total_count<0 || result.incomplete_results!==false)
      throw new Error("GitHub returned an incomplete or invalid search");
    if(result.total_count>1000) throw new Error("GitHub search exceeds its 1,000-result limit; narrow the queue on GitHub");
    for(const item of result.items){
      if(typeof item.html_url!=="string" || !/^https:\/\/github\.com\/[^/]+\/[^/]+\/pull\/\d+$/.test(item.html_url) || typeof item.title!=="string" || typeof item.user?.login!=="string")
        throw new Error("GitHub returned an invalid PR");
      if(item.state!=="open" || item.draft===true) continue;
      const ref=item.html_url.split("github.com/")[1].replace("/pull/","#");
      rows.set(item.html_url,{pr:{label:ref+" — "+item.title,url:item.html_url},author:item.user.login,
        ci:"unknown — not fetched",review:"Your review requested",action:"Review on GitHub",liveState:"OPEN",reviewRequested:true});
    }
    if(page*100>=result.total_count) return [...rows.values()];
    if(result.items.length<100) throw new Error("GitHub search changed during pagination; retry refresh");
  }
  throw new Error("GitHub pagination limit reached");
}

export async function discoverLinear(){
  throw new Error("Linear access is disabled until an approved managed backend is configured.");
}

export function activate(host, snapshot=DATA){
  const DATA=snapshot;
  if(host.apiVersion!=="1") throw new Error("Work Queue requires host API 1.");
  return host.registerPage("work-queue", ({container, path}) => {
    const style=document.createElement("style"); style.textContent=CSS; document.head.append(style);
    const root=el("section","gwq");
    let linear=DATA.linear||[];
    const TODAY=new Date().toISOString().slice(0,10);
    const review=DATA.review||[], align=DATA.align||[], slack=DATA.slack||[], actions=DATA.actions||[];
    function withRecommendation(node, url){
      const rec=DATA.recommendations?.[url];
      if(!rec || typeof rec.summary!=="string" || !rec.summary.trim()) return node;
      const wrap=el("div"); wrap.append(node);
      const block=el("details","recommendation");
      block.append(el("summary",null,"Agent recommendation: "+rec.summary));
      block.append(el("p",null,rec.rationale||""));
      block.append(el("p","sub","OpenHands · assessed "+(rec.assessedAt||"unknown")+(rec.headSha?" · head "+rec.headSha:"")+" · snapshot judgment, not live status or approval"));
      for(const ref of rec.links||[]) if(typeof ref.url==="string" && /^https:\/\//.test(ref.url)){
        const p=el("p"); p.append(link(ref.label,ref.url)); block.append(p);
      }
      wrap.append(block); return wrap;
    }
    const overdue=linear.filter(x=>x.due && x.due < TODAY);
    const failing=linear.filter(x=>ciKind(x.ci)==="fail");
    const noPri=linear.filter(x=>x.priorityNum===0);
    function hasCanonicalTracker(ref, kind){
      if(!ref?.url || /^(none|unknown|not verified|possible|candidate)\b/i.test(ref.label||"")) return false;
      try{
        const url=new URL(ref.url);
        return url.protocol==="https:" && (kind==="github"
          ? url.hostname==="github.com" && /^\/[^/]+\/[^/]+\/issues\/\d+\/?$/.test(url.pathname)
          : url.hostname==="linear.app" && /^\/[^/]+\/issue\/[^/]+/.test(url.pathname));
      }catch{return false;}
    }
    const needsTracking=align.filter(a=>!hasCanonicalTracker(a.issue,"github") && !hasCanonicalTracker(a.linear,"linear"));

    const head=el("div","head");
    head.append(el("h1",null,DATA.displayName||"Work Queue"));
    head.append(el("p","sub","Snapshot "+(DATA.generated||"")+" · "+(DATA.source||"")+" · read-only, blocked Linear tickets omitted"));
    if(path) head.append(el("p","sub","/"+path));
    root.append(head);
    const summary=el("div","summary");
    function stat(label,val,alert){ const s=el("span",alert?"alert":null); s.append(el("b",null,String(val)), document.createTextNode(" "+label)); return s; }
    const awaitingVal = el("b", null, "…");
    const awaitingStat = el("span");
    const awaitingLabel=document.createTextNode(" awaiting review (loading)");
    awaitingStat.append(awaitingVal, awaitingLabel);
    const linearStat=stat("Linear open (snapshot)",linear.length), overdueStat=stat("overdue",overdue.length), failingStat=stat("CI failing (snapshot)",failing.length), noPriStat=stat("no priority",noPri.length);
    summary.append(
      awaitingStat,
      stat("authored PRs ("+needsTracking.length+" need tracking)", align.length),
      linearStat,
      overdueStat,
      failingStat,
      noPriStat,
      ...(slack.length ? [stat("Slack proposals", slack.length)] : [])
    );
    root.append(summary);

    function tableCard(title, subtitle, headers, rows){
      const card=el("div","card"); card.append(el("h2",null,title)); if(subtitle) card.append(el("p","sub",subtitle));
      const wrap=el("div","scroll"); const t=document.createElement("table"); const thead=document.createElement("thead"); const tr=document.createElement("tr");
      headers.forEach(h=>tr.append(el("th",null,h))); thead.append(tr); t.append(thead);
      const tb=document.createElement("tbody"); rows.forEach(cells=>{ const r=document.createElement("tr"); cells.forEach(c=>{ const td=document.createElement("td"); if(typeof c==="string") td.textContent=c; else if(c) td.append(c); r.append(td); }); tb.append(r); });
      t.append(tb); wrap.append(t); card.append(wrap); return card;
    }

    const reviewCard=el("div","card"); reviewCard.setAttribute("aria-busy","true");
    reviewCard.append(el("h2",null,"PRs awaiting review"));
    const reviewNote=el("p","sub"); reviewNote.setAttribute("role","status"); reviewNote.setAttribute("aria-live","polite");
    reviewCard.append(reviewNote);
    const ghUser=DATA.githubUser||"";
    const refresh=el("button",null,"Refresh reviews"); refresh.type="button"; refresh.setAttribute("aria-label","Refresh review requests"); reviewCard.append(refresh);
    const lsWrap=el("p"); lsWrap.append(link("Open live review queue on GitHub ↗", "https://github.com/pulls?q="+encodeURIComponent("is:pr is:open review-requested:"+ghUser))); reviewCard.append(lsWrap);
    const rWrap=el("div","scroll"); const rTable=document.createElement("table");
    const rHead=document.createElement("thead"); const rHr=document.createElement("tr"); ["PR","Author","CI","Review","Action"].forEach(h=>rHr.append(el("th",null,h))); rHead.append(rHr); rTable.append(rHead);
    const rBody=document.createElement("tbody"); rTable.append(rBody); rWrap.append(rTable); reviewCard.append(rWrap); root.append(reviewCard);
    let disposed=false; let ctrl=new AbortController();
    function renderReview(rows, emptyMessage="No public PRs currently request your review (open, non-draft, directly requested)."){
      rBody.replaceChildren();
      if(!rows.length){ const tr=document.createElement("tr"); const td=el("td",null,emptyMessage); td.colSpan=5; tr.append(td); rBody.append(tr); return; }
      rows.forEach(r=>{
        const tr=document.createElement("tr");
        const c1=document.createElement("td"); c1.append(withRecommendation(link(r.pr.label, r.pr.url),r.pr.url));
        if(r.liveState){ const b=el("span","pill",r.liveState); b.style.marginLeft="6px"; c1.append(b); }
        const c3=document.createElement("td"); c3.append(pill(r.ci, ciKind(r.ci)));
        [c1, el("td",null,r.author), c3, el("td",null,r.review), el("td",null,r.action)].forEach(c=>tr.append(c)); rBody.append(tr);
      });
    }
    let lastLive=null, reviewTimer;
    async function loadReviews(){
      refresh.disabled=true; reviewCard.setAttribute("aria-busy","true");
      reviewNote.replaceChildren(el("span","spinner"),document.createTextNode("Loading review requests directly from GitHub…"));
      rBody.replaceChildren(); awaitingVal.textContent="…"; awaitingLabel.textContent=" awaiting review (loading)";
      reviewTimer=setTimeout(()=>ctrl?.abort(),20000);
      try{
        const rows=await discoverReviewRequests(ghUser,ctrl?.signal);
        if(disposed) return;
        lastLive=rows; renderReview(rows); awaitingVal.textContent=String(rows.length); awaitingLabel.textContent=" awaiting review (public GitHub)";
        awaitingStat.className=rows.length?"alert":"";
        reviewNote.textContent="Loaded directly from GitHub at "+new Date().toLocaleTimeString()+". All matching public, open, non-draft PRs directly requesting "+ghUser+"; independent of the agent snapshot. Private repositories and team-only requests are not included. GitHub search may briefly lag recent changes. CI is not fetched by this search.";
      }catch(error){
        if(disposed) return;
        const rows=lastLive ?? review.filter(isQueueMember);
        renderReview(rows,"No cached review requests — the live queue is unknown."); awaitingVal.textContent=String(rows.length); awaitingLabel.textContent=lastLive?" awaiting review (stale live results)":" awaiting review (snapshot)";
        awaitingStat.className="";
        reviewNote.textContent=(lastLive?"Stale live results":"Snapshot fallback ("+(DATA.generated||"unknown date")+")")+" — "+(error.name==="AbortError"?"GitHub request timed out":error.message)+". This is not a current or complete queue; private PR coverage is unavailable. Retry or open GitHub above.";
      }finally{
        clearTimeout(reviewTimer);
        if(!disposed){reviewCard.setAttribute("aria-busy","false");refresh.disabled=false;}
      }
    }
    refresh.addEventListener("click",()=>{ctrl=new AbortController();loadReviews();});
    loadReviews();

    root.append(tableCard("PRs needing issue alignment", "Showing "+needsTracking.length+" of "+align.length+" PR entries without a verified canonical GitHub issue or Linear tracker. Umbrella trackers count; unverified candidates do not.",
      ["PR","Associated issue","Assigned?","Linear tracked","Action"],
      needsTracking.map(a=>[withRecommendation(link(a.pr.label,a.pr.url),a.pr.url), link(a.issue.label,a.issue.url), a.assigned, link(a.linear.label,a.linear.url), a.action])));

    if(slack.length) root.append(tableCard("Slack proposals (proposed only — no tickets created)", null,
      ["Source","Proposed ticket","Destination","Reason","Awaiting confirmation"],
      slack.map(sn=>[link(sn.source.label,sn.source.url||null), sn.ticket, sn.destination, sn.reason, sn.awaiting])));

    const lcard=el("div","card"); lcard.append(el("h2",null,"Linear priority walkthrough"));
    const linearNote=el("p","sub");linearNote.setAttribute("role","status");linearNote.setAttribute("aria-live","polite");
    const linearRefresh=el("button",null,"Refresh Linear");linearRefresh.type="button";
    const queueExport=el("button",null,"Export queue for agent");queueExport.type="button";
    lcard.append(linearNote,linearRefresh,queueExport);
    let linearProvenance={status:"snapshot",generated:DATA.generated},linearRun=0,linearTimer;
    queueExport.addEventListener("click",()=>{
      const blob=new Blob([JSON.stringify({schemaVersion:1,generated:new Date().toISOString(),linear,linearProvenance,scope:"All loaded Linear tickets before UI filters; all cycles included; PR open state, CI and evidence unverified"},null,2)],{type:"application/json"});
      const url=URL.createObjectURL(blob),a=link("Download",url);a.download="work-queue-live.json";a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    });
    const barrow=el("div","barrow"); const bar=el("div","bar");
    PRI_ORDER.forEach(p=>{ const n=linear.filter(x=>x.priority===p).length; if(!n) return; const seg=document.createElement("i"); seg.style.width=(n/Math.max(linear.length,1)*100)+"%"; seg.style.background=PRI_COLORS[p]; seg.title=p+": "+n; bar.append(seg); });
    barrow.append(bar, el("span",null,PRI_ORDER.map(p=>p+" "+linear.filter(x=>x.priority===p).length).join(" · ")+" · with linked PR: "+linear.filter(x=>x.pr&&x.pr.url).length));
    lcard.append(barrow);
    const toolbar=el("div","toolbar");
    const search=document.createElement("input"); search.type="search"; search.placeholder="Search ID, title, PR, context…"; search.setAttribute("aria-label","Search Linear tickets");
    const priSel=document.createElement("select"); priSel.setAttribute("aria-label","Filter by priority");
    ["All priorities",...PRI_ORDER].forEach(p=>{ const o=document.createElement("option"); o.value=p; o.textContent=p; priSel.append(o); });
    const wsSel=document.createElement("select"); wsSel.setAttribute("aria-label","Filter by workspace");
    ["All workspaces",...new Set(linear.map(x=>x.workspace).filter(Boolean))].forEach(p=>{ const o=document.createElement("option"); o.value=p; o.textContent=p; wsSel.append(o); });
    const overdueBtn=el("button",null,"Overdue only"); overdueBtn.type="button"; overdueBtn.setAttribute("aria-pressed","false");
    const prBtn=el("button",null,"Has linked PR only"); prBtn.type="button"; prBtn.setAttribute("aria-pressed","false");
    const count=el("span","muted");
    toolbar.append(search, priSel, wsSel, overdueBtn, prBtn, count); lcard.append(toolbar);
    const lwrap=el("div","scroll"); lcard.append(lwrap); root.append(lcard);

    function renderLinear(){
      const q=search.value.trim().toLowerCase();
      const rows=[...linear].sort((a,b)=>(a.priorityNum ?? 5)-(b.priorityNum ?? 5)||queueDate(a).localeCompare(queueDate(b))||a.id.localeCompare(b.id)).filter(x=>{
        if(priSel.value!=="All priorities" && x.priority!==priSel.value) return false;
        if(wsSel.value!=="All workspaces" && x.workspace!==wsSel.value) return false;
        if(overdueBtn.getAttribute("aria-pressed")==="true" && !(x.due && x.due<TODAY)) return false;
        if(prBtn.getAttribute("aria-pressed")==="true" && !(x.pr&&x.pr.url)) return false;
        if(q && !(x.id+" "+x.title+" "+(x.pr.label||"")+" "+x.context).toLowerCase().includes(q)) return false;
        return true;
      });
      count.textContent=rows.length+" / "+linear.length+" tickets";
      lwrap.replaceChildren();
      const t=document.createElement("table"); const thead=document.createElement("thead"); const tr=document.createElement("tr");
      ["Linear","Priority","Linked PR","CI","Review","Live evidence","Context needed"].forEach(h=>tr.append(el("th",null,h))); thead.append(tr); t.append(thead);
      const tb=document.createElement("tbody");
      if(!rows.length){ const r=document.createElement("tr"); const td=el("td",null,"No tickets match these filters."); td.colSpan=7; r.append(td); tb.append(r); }
      rows.forEach(x=>{
        const r=document.createElement("tr");
        const c1=document.createElement("td"); c1.append(withRecommendation(link(x.id+" — "+x.title, x.url),x.url)); const wsTag=el("div","muted",x.workspace); wsTag.style.fontSize="11px"; c1.append(wsTag);
        const c2=document.createElement("td"); const pk=x.priority==="High"||x.priority==="Urgent"?"high":x.priority==="Medium"?"med":x.priority==="Low"?"low":"none"; c2.append(pill(x.priority+(x.due?" · "+x.due:""), pk)); if(x.due && x.due<TODAY){ const o=el("div",null,"OVERDUE"); o.style.color="var(--oh-danger,#E76A5E)"; o.style.fontSize="11px"; o.style.fontWeight="700"; c2.append(o); }
        const c3=document.createElement("td"); c3.append(link(x.pr.label, x.pr.url));
        const c4=document.createElement("td"); c4.append(pill(x.ci, ciKind(x.ci)));
        [c1,c2,c3,c4, el("td",null,x.review), el("td",null,x.evidence), el("td",null,x.context)].forEach(c=>r.append(c)); tb.append(r);
      });
      t.append(tb); lwrap.append(t);
    }
    [search,priSel,wsSel].forEach(n=>n.addEventListener("input",renderLinear));
    [overdueBtn,prBtn].forEach(b=>b.addEventListener("click",()=>{ b.setAttribute("aria-pressed", b.getAttribute("aria-pressed")==="true"?"false":"true"); renderLinear(); }));
    renderLinear();
    async function loadLinear(){
      const run=++linearRun;linearProvenance={...linearProvenance,status:"loading"};linearRefresh.disabled=true;lcard.setAttribute("aria-busy","true");
      linearNote.replaceChildren(el("span","spinner"),document.createTextNode("Checking approved Linear backend…"));
      linearTimer=setTimeout(()=>{if(!disposed && run===linearRun){linearRun++;linearProvenance={...linearProvenance,status:"stale"};linearNote.textContent="Linear refresh timed out — showing stale data. Retry when Linear is available.";linearRefresh.disabled=false;lcard.setAttribute("aria-busy","false");}},185000);
      try{
        const result=await discoverLinear(host,()=>!disposed && run===linearRun);
        if(disposed || run!==linearRun)return;
        linear=result.rows;linearProvenance={status:"live",generated:new Date().toISOString(),sources:result.sources};
        const selected=wsSel.value;wsSel.replaceChildren();
        ["All workspaces",...new Set(linear.map(x=>x.workspace))].forEach(p=>{const o=el("option",null,p);o.value=p;wsSel.append(o);});
        if([...wsSel.options].some(o=>o.value===selected))wsSel.value=selected;
        bar.replaceChildren();PRI_ORDER.forEach(p=>{const n=linear.filter(x=>x.priority===p).length;if(n){const seg=el("i");seg.style.width=(n/linear.length*100)+"%";seg.style.background=PRI_COLORS[p];bar.append(seg);}});
        barrow.lastChild.textContent=PRI_ORDER.map(p=>p+" "+linear.filter(x=>x.priority===p).length).join(" · ");
        linearStat.replaceChildren(stat("Linear open (live)",linear.length));overdueStat.replaceChildren(stat("overdue",linear.filter(x=>x.due && x.due<TODAY).length));noPriStat.replaceChildren(stat("no priority",linear.filter(x=>x.priorityNum===0).length));failingStat.textContent="CI unknown — not fetched";
        linearNote.textContent="Live Linear · "+new Date().toLocaleTimeString()+" · "+result.sources.length+" connection(s). Completed, archived and actively blocked tickets omitted. Unprioritized first, then priority and the earlier of due date or assigned cycle end date; all cycles included. Linked PR open state, CI, review and live-code evidence require separate verification. Agent recommendations are optional snapshot judgments.";
        renderLinear();
      }catch(error){
        if(disposed || run!==linearRun)return;
        linearProvenance={...linearProvenance,status:"stale"};
        linearStat.replaceChildren(stat("Linear open (stale)",linear.length));
        linearNote.textContent="Stale Linear fallback ("+(linearProvenance.generated||"unknown date")+"). Live access disabled: the unsafe secret loader has been removed. A declared managed backend and explicit secret approval are required. No partial results substituted.";
      }finally{if(run===linearRun){clearTimeout(linearTimer);if(!disposed){linearRefresh.disabled=false;lcard.setAttribute("aria-busy","false");}}}
    }
    linearRefresh.addEventListener("click",loadLinear);loadLinear();

    root.append(tableCard("Action items", "Decisions only — running the workflow applies no assignments, priorities, merges, or tickets unless you approve them.",
      ["Item","Needed"],
      actions.map(a=>[link(a.item.label, a.item.url), a.needed])));

    root.append(el("p","sub","Review requests load directly from GitHub on page open and Refresh reviews — no agent run needed. Public repositories only; private review requests need an authenticated server-side GitHub connection. Live Linear loading is disabled pending managed-backend setup and explicit secret approval. Other sections use the daily-workflow snapshot. Never commit private queue data to a public repository."));
    container.append(root);
    return () => { disposed=true; linearRun++;clearTimeout(linearTimer); clearTimeout(reviewTimer); if(ctrl) try{ctrl.abort();}catch(e){} root.remove(); style.remove(); };
  });
}
