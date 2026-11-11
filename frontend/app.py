import json, sys, html
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import streamlit as st
import pandas as pd
from backend.services import results, REPORTS, BY_ID, decisions, decide, active, get_current_question
from backend.llm import get_llm

st.set_page_config(page_title='Acadza | Quality Ops', page_icon='🎓', layout='wide', initial_sidebar_state='collapsed')

CSS = '''
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
:root{
  --ink:#eaf0ff; --muted:#9fb0cc; --line:#26334f; --bg:#0a1020; --card:#111a2e; --card2:#16213a;
  --brand:#6366f1; --brand2:#8b5cf6; --accent:#2dd4bf;
}
html,body,.stApp,[class*="css"]{font-family:'Plus Jakarta Sans',system-ui,sans-serif}
.stApp{background:radial-gradient(900px 500px at 100% 0,rgba(99,102,241,.12),transparent 60%),var(--bg)!important;color:var(--ink)!important}
.stApp p,.stApp li,.stApp label,.stApp h1,.stApp h2,.stApp h3,.stApp h4,.stApp h5,.stApp h6,
.stApp [data-testid="stMarkdownContainer"],.stApp [data-testid="stWidgetLabel"] p,.stApp [data-testid="stCheckbox"] p,
.stApp summary,.stApp summary p{color:var(--ink)}
.stApp [data-testid="stCaptionContainer"],.stApp [data-testid="stCaptionContainer"] p{color:var(--muted)!important}
section[data-testid="stSidebar"],div[data-testid="collapsedControl"],#MainMenu,footer{display:none!important}
header[data-testid="stHeader"]{background:transparent;height:0}
.block-container{padding:0 1.6rem 3rem;max-width:1680px}

/* top bar */
.topbar{margin:0 -1.6rem 1.2rem;padding:20px 1.6rem 70px;background:radial-gradient(1000px 360px at 90% -60%,#7c3aed 0,transparent 60%),linear-gradient(120deg,#0d1530 0%,#1b1f4d 60%,#2a2a78 100%);border-bottom:1px solid var(--line);display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:14px}
.logo-row{display:flex;align-items:center;gap:12px}
.logo{width:42px;height:42px;border-radius:12px;background:linear-gradient(135deg,#818cf8,#2dd4bf);display:flex;align-items:center;justify-content:center;font-weight:800;font-size:1.2rem;color:#fff;box-shadow:0 6px 18px rgba(99,102,241,.5)}
.tb-title{font-weight:800;font-size:1.15rem;line-height:1.1;color:#fff}.tb-sub{font-size:.74rem;color:#a5b4fc;letter-spacing:.08em;text-transform:uppercase}
.chip{display:inline-flex;align-items:center;gap:7px;background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.2);padding:6px 12px;border-radius:999px;font-size:.78rem;font-weight:600;color:#fff}
.chip i{width:8px;height:8px;border-radius:50%;display:inline-block}

/* nav */
div.nav-wrap{margin-top:-62px}
div.nav-wrap div[role="radiogroup"]{gap:6px;background:rgba(10,16,32,.55);backdrop-filter:blur(8px);padding:5px;border-radius:14px;width:fit-content;max-width:100%;flex-wrap:wrap;border:1px solid rgba(255,255,255,.18)}
div.nav-wrap div[role="radiogroup"] label{padding:8px 18px;border-radius:10px;margin:0;cursor:pointer}
div.nav-wrap div[role="radiogroup"] label>div:first-child{display:none}
div.nav-wrap div[role="radiogroup"] label p{color:#c7d2fe!important;font-weight:600}
div.nav-wrap div[role="radiogroup"] label:has(input:checked){background:linear-gradient(135deg,var(--brand),var(--brand2));box-shadow:0 4px 14px rgba(99,102,241,.5)}
div.nav-wrap div[role="radiogroup"] label:has(input:checked) p{color:#fff!important}

/* cards */
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:18px 20px;box-shadow:0 8px 24px rgba(0,0,0,.25);margin-bottom:14px;color:var(--ink)}
.card h4{margin:0 0 10px;font-size:.72rem;letter-spacing:.09em;text-transform:uppercase;color:var(--accent)!important;font-weight:700}
.h-title{font-size:1.55rem;font-weight:800;letter-spacing:-.02em;margin:0;color:#fff}.h-sub{color:var(--muted);font-size:.92rem;margin:.15rem 0 1rem}
.muted{color:var(--muted)!important;font-size:.82rem}

.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:14px;margin-bottom:14px}
.kpi{position:relative;overflow:hidden;background:var(--card);border:1px solid var(--line);border-radius:16px;padding:16px 18px;box-shadow:0 8px 24px rgba(0,0,0,.25)}
.kpi:before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--c,#6366f1)}
.kpi .l{font-size:.72rem;color:var(--muted);font-weight:700;text-transform:uppercase;letter-spacing:.07em}
.kpi .v{font-size:2.1rem;font-weight:800;letter-spacing:-.02em;margin-top:2px;color:#fff}

.pill{display:inline-flex;align-items:center;gap:6px;padding:3px 10px;border-radius:999px;font-size:.72rem;font-weight:700;white-space:nowrap}
.pill i{width:6px;height:6px;border-radius:50%;background:currentColor;display:inline-block}
.p-ok{background:rgba(34,197,94,.16);color:#4ade80!important}.p-bad{background:rgba(248,113,113,.16);color:#fca5a5!important}
.p-warn{background:rgba(251,191,36,.16);color:#fcd34d!important}.p-info{background:rgba(96,165,250,.16);color:#93c5fd!important}.p-n{background:rgba(148,163,184,.16);color:#cbd5e1!important}

.ring-wrap{display:flex;align-items:center;gap:18px}
.ring{--p:0;width:96px;height:96px;border-radius:50%;background:conic-gradient(var(--accent) calc(var(--p)*1%),#26334f 0);display:flex;align-items:center;justify-content:center;flex:none}
.ring span{width:74px;height:74px;border-radius:50%;background:var(--card);display:flex;align-items:center;justify-content:center;font-weight:800;font-size:1.2rem;color:#fff}

.bar-row{display:grid;grid-template-columns:minmax(80px,32%) 1fr 34px;gap:10px;align-items:center;margin:9px 0;font-size:.86rem;color:var(--ink)}
.bar{height:9px;border-radius:99px;background:#223050;overflow:hidden}.bar b{display:block;height:100%;border-radius:99px;background:linear-gradient(90deg,var(--accent),var(--brand))}

.row{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:11px 0;border-bottom:1px solid var(--line)}
.row:last-child{border-bottom:0}.row .t{font-weight:700;font-size:.9rem;color:#fff}

.case{border:1px solid var(--line);border-radius:14px;padding:12px 14px;background:var(--card2);margin-bottom:6px}
.case.sel{border-color:var(--accent);box-shadow:0 0 0 3px rgba(45,212,191,.18);background:#1a2848}
.case .top{display:flex;justify-content:space-between;gap:8px;align-items:center}
.case .id{font-weight:700;font-size:.88rem;color:#fff}.case .sub{color:var(--muted);font-size:.78rem;margin:4px 0 8px}
.meter{height:5px;background:#26334f;border-radius:9px;overflow:hidden;margin-top:8px}.meter b{display:block;height:100%;background:linear-gradient(90deg,var(--accent),var(--brand))}

.quote{border-left:3px solid var(--accent);background:rgba(45,212,191,.08);padding:10px 14px;border-radius:0 10px 10px 0;color:var(--ink)}
.reply{background:#0c1426;border:1px dashed #3a4a6b;border-radius:10px;padding:10px 12px;font-size:.9rem;color:var(--ink)}
.diff{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:.8rem;border:1px solid var(--line);border-radius:10px;overflow:hidden}
.diff div{padding:6px 10px;white-space:pre-wrap;word-break:break-word}
.diff .f{background:#1b2846;font-weight:700;color:#cbd5e1}.diff .m{background:rgba(239,68,68,.2);color:#fecaca}.diff .p{background:rgba(34,197,94,.2);color:#bbf7d0}
.empty{text-align:center;padding:50px 16px;color:var(--muted);background:var(--card);border:1px dashed #3a4a6b;border-radius:16px}

/* white "paper" for authored question content, so any inline colours stay readable */
.st-key-paper{background:#ffffff;border-radius:14px;padding:18px 20px;margin-bottom:14px;box-shadow:0 8px 24px rgba(0,0,0,.3)}
.st-key-paper,.st-key-paper *{color:#111827}
.st-key-paper .answer{background:#ecfdf5;border:1px solid #a7f3d0;border-radius:10px;padding:8px 12px;margin:12px 0}
.st-key-paper .answer,.st-key-paper .answer *{color:#065f46}
.st-key-paper h5{margin:14px 0 6px;color:#4338ca}

/* widgets */
div[data-baseweb="select"]>div,div[data-baseweb="input"]>div,div[data-baseweb="base-input"]{background:#0f1930!important;border:1px solid #2c3b5c!important;border-radius:10px!important;color:var(--ink)!important}
div[data-baseweb="select"] *,div[data-baseweb="input"] input{color:var(--ink)!important;-webkit-text-fill-color:var(--ink)}
input::placeholder{color:#7f90b0!important;-webkit-text-fill-color:#7f90b0!important}
div[data-baseweb="popover"] ul,div[data-baseweb="popover"] li{background:#111a2e!important;color:var(--ink)!important}
div[data-baseweb="popover"] li:hover{background:#1d2b4d!important}
div[data-testid="stButton"]>button,div[data-testid="stDownloadButton"]>button{border-radius:10px;font-weight:700;border:1px solid #33456b;background:#1a2745;padding:.5rem 1rem;transition:all .15s}
div[data-testid="stButton"]>button *,div[data-testid="stDownloadButton"]>button *{color:var(--ink)!important}
div[data-testid="stButton"]>button[kind="primary"]{background:linear-gradient(135deg,var(--brand),var(--brand2));border:0;box-shadow:0 6px 16px rgba(99,102,241,.4)}
div[data-testid="stButton"]>button[kind="primary"] *{color:#fff!important}
div[data-testid="stButton"]>button:hover{transform:translateY(-1px);border-color:var(--accent)}
div[data-testid="stExpander"]{background:var(--card);border:1px solid var(--line);border-radius:12px}
div[data-testid="stAlert"]{border-radius:12px}
div[data-testid="stVerticalBlockBorderWrapper"]{border-radius:16px}
::-webkit-scrollbar{width:8px;height:8px}::-webkit-scrollbar-thumb{background:#33456b;border-radius:9px}

@media (max-width:1100px){.block-container{padding:0 1rem 2rem}.topbar{margin:0 -1rem 1rem;padding:16px 1rem 70px}}
@media (max-width:640px){.kpis{grid-template-columns:repeat(2,1fr);gap:10px}.kpi .v{font-size:1.6rem}.h-title{font-size:1.25rem}div[data-testid="stButton"]>button{width:100%}.ring-wrap{flex-direction:column;align-items:flex-start}}

/* self-contained dark fallback (no config.toml needed) */
div[data-testid="stDataFrame"]{border:1px solid var(--line);border-radius:12px;overflow:hidden;filter:invert(.92) hue-rotate(180deg)}
div[data-testid="stCheckbox"] label span{color:var(--ink)!important}
div[data-testid="stCheckbox"] div[role="checkbox"],div[data-testid="stCheckbox"] span[data-baseweb="checkbox"]>span{border-color:#5b6b8f!important}
div[data-testid="stTextInput"] input:disabled{opacity:.6}
div[data-testid="stExpander"] summary:hover{color:#fff}
</style>
'''
st.markdown(CSS, unsafe_allow_html=True)

E = lambda v: html.escape(str(v))
def pill(t, k='n'): return f"<span class='pill p-{k}'><i></i>{E(t)}</span>"
def vpill(v): return pill(str(v).replace('_', ' ').title(), {'defect': 'bad', 'no_defect': 'ok', 'not_a_defect': 'ok'}.get(v, 'warn'))
def rpill(r): return pill(str(r).replace('_', ' ').title(), 'info' if r == 'faculty_review' else 'n')
def bars(counter):
    if not counter: return "<div class='muted'>No data</div>"
    mx = max(counter.values())
    return ''.join(f"<div class='bar-row'><span>{E(str(k).replace('_',' ').title())}</span><div class='bar'><b style='width:{v/mx*100:.0f}%'></b></div><b>{v}</b></div>" for k, v in counter.most_common())

items = results(); dec = {x['report_id']: x for x in decisions()}; llm = get_llm()
pending = [x for x in items if x['route'] == 'faculty_review' and x['reportId'] not in dec]
decided = len([x for x in items if x['reportId'] in dec])
rate = round(decided / len(items) * 100) if items else 0
ai_on = llm.mode == 'groq'

# ---------- top bar + nav
st.markdown(f"""<div class='topbar'><div class='logo-row'><div class='logo'>A</div><div><div class='tb-title'>Acadza</div><div class='tb-sub'>Quality Operations</div></div></div>
<div style='display:flex;gap:10px;flex-wrap:wrap'><span class='chip'><i style='background:{"#4ade80" if ai_on else "#fbbf24"}'></i>{"Groq AI online" if ai_on else "Fallback mode"}</span><span class='chip'>{len(pending)} awaiting review</span></div></div>""", unsafe_allow_html=True)
st.markdown("<div class='nav-wrap'>", unsafe_allow_html=True)
page = st.radio('nav', ['Overview', 'Review Workspace', 'Approved', 'Audit Trail', 'System'], horizontal=True, label_visibility='collapsed')
st.markdown("</div>", unsafe_allow_html=True)
st.write('')
if message := st.session_state.pop('decision_message', None): st.success(message)

# ================================================= OVERVIEW
if page == 'Overview':
    st.markdown("<p class='h-title'>Quality at a glance</p><p class='h-sub'>AI finds the defects. Faculty make the final call.</p>", unsafe_allow_html=True)
    affected = len({x['questionId'] for x in items}); defects = sum(x['verdict'] == 'defect' for x in items)
    cards = [('Total reports', len(items), '#4f46e5'), ('Questions affected', affected, '#7c3aed'), ('Pending review', len(pending), '#d97706'),
             ('Verified defects', defects, '#dc2626'), ('Approved', sum(x['action'] == 'approved' for x in dec.values()), '#16a34a'), ('Rejected', sum(x['action'] == 'rejected' for x in dec.values()), '#64748b')]
    st.markdown("<div class='kpis'>" + ''.join(f"<div class='kpi' style='--c:{c}'><div class='l'>{l}</div><div class='v'>{v}</div></div>" for l, v, c in cards) + "</div>", unsafe_allow_html=True)

    c1, c2 = st.columns([1.5, 1], gap='medium')
    with c1:
        top = sorted(pending, key=lambda x: (-x['confidence'], x['questionId']))[:6]
        rows = ''.join(f"<div class='row'><div><div class='t'>{E(x['questionId'])}</div><div class='muted'>{E(BY_ID[x['questionId']]['subject'])} · {E(x['reportId'])}</div></div><div style='display:flex;gap:6px;align-items:center'>{vpill(x['verdict'])}<b>{x['confidence']:.0%}</b></div></div>" for x in top)
        st.markdown(f"<div class='card'><h4>Needs attention first</h4>{rows or '<div class=muted>Nothing pending. Great work.</div>'}</div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='card'><h4>Review progress</h4><div class='ring-wrap'><div class='ring' style='--p:{rate}'><span>{rate}%</span></div><div><b>{decided}</b> of {len(items)} reports decided<div class='muted'>Duplicates are grouped by question.</div></div></div></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='card'><h4>Verdicts</h4>{bars(Counter(x['verdict'] for x in items))}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='card'><h4>Reports by subject</h4>{bars(Counter(BY_ID[x['questionId']]['subject'] for x in items))}</div>", unsafe_allow_html=True)

# ================================================= WORKSPACE
elif page == 'Review Workspace':
    st.markdown("<p class='h-title'>Review workspace</p><p class='h-sub'>Pick a case, read the evidence, decide.</p>", unsafe_allow_html=True)
    t1, t2, t3, t4, t5 = st.columns([2, 1, 1, 1, 1])
    query = t1.text_input('Search', placeholder='🔍  Search question or report ID', label_visibility='collapsed')
    subject = t2.selectbox('Subject', ['All subjects'] + sorted({BY_ID[x['questionId']]['subject'] for x in items}), label_visibility='collapsed')
    verdict = t3.selectbox('Verdict', ['All verdicts'] + sorted({x['verdict'] for x in items}), label_visibility='collapsed')
    route = t4.selectbox('Route', ['All routes'] + sorted({x['route'] for x in items}), label_visibility='collapsed')
    status = t5.selectbox('Status', ['Any status', 'Pending', 'Decided'], label_visibility='collapsed')

    cand = [x for x in items if (not query or query.lower() in (x['questionId'] + x['reportId']).lower())
            and (subject.startswith('All') or BY_ID[x['questionId']]['subject'] == subject)
            and (verdict.startswith('All') or x['verdict'] == verdict)
            and (route.startswith('All') or x['route'] == route)
            and (status == 'Any status' or (status == 'Decided') == (x['reportId'] in dec))]
    cand.sort(key=lambda x: (x['route'] != 'faculty_review', -x['confidence'], x['questionId']))
    if not cand:
        st.markdown("<div class='empty'><b>No cases match</b><br>Clear a filter to see more.</div>", unsafe_allow_html=True); st.stop()

    ids = [x['reportId'] for x in cand]
    if st.session_state.get('sel') not in ids: st.session_state['sel'] = ids[0]
    def pick(rid): st.session_state['sel'] = rid

    left, mid, right = st.columns([1.05, 1.9, 1.35], gap='medium')

    with left:
        st.caption(f'{len(cand)} case(s) · priority order')
        with st.container(height=720, border=False):
            for x in cand[:100]:
                is_sel = x['reportId'] == st.session_state['sel']
                done = pill('Decided', 'ok') if x['reportId'] in dec else ''
                st.markdown(f"""<div class='case {"sel" if is_sel else ""}'><div class='top'><span class='id'>{E(x['questionId'])}</span>{vpill(x['verdict'])}</div>
<div class='sub'>{E(BY_ID[x['questionId']]['subject'])} · {E(x['reportId'])}</div><div style='display:flex;gap:6px;flex-wrap:wrap'>{rpill(x['route'])}{done}</div>
<div class='meter'><b style='width:{x['confidence']*100:.0f}%'></b></div></div>""", unsafe_allow_html=True)
                st.button('Viewing' if is_sel else 'Open', key='o_' + x['reportId'], on_click=pick, args=(x['reportId'],), use_container_width=True, type='primary' if is_sel else 'secondary')

    selected = next(x for x in cand if x['reportId'] == st.session_state['sel'])
    report = next(r for r in REPORTS if r['reportId'] == selected['reportId'])
    q = get_current_question(selected['questionId']); content = active(q); same = [r for r in REPORTS if r['questionId'] == q['_id']]
    edit = selected.get('edit') or {}

    with mid:
        with st.container(height=745, border=False):
            st.markdown(f"<div class='card'><h4>Question · {E(q['_id'])}</h4><div class='muted'>{E(q['subject'])} / {E(q['chapter'])} · {E(q['questionType'])} · {E(q['level'])}</div></div>", unsafe_allow_html=True)
            with st.container(key='paper'):
                st.markdown(content['question'], unsafe_allow_html=True)
                st.markdown(f"<div class='answer'><b>Stored answer:</b> {E(content['answer'])}</div>", unsafe_allow_html=True)
                st.markdown("<h5>Solution</h5>", unsafe_allow_html=True)
                st.markdown(content['solution'], unsafe_allow_html=True)

    with right:
        with st.container(height=745, border=False):
            st.markdown(f"<div class='card'><h4>Student report</h4><div class='quote'>{E(report['comment'])}</div><div class='muted' style='margin-top:10px'>{E(report['reportId'])} · {E(report['reportedAt'])} · {E(report['source'])} · <b>{len(same)}</b> on this question</div></div>", unsafe_allow_html=True)
            st.markdown(f"""<div class='card'><h4>AI analysis</h4><div style='display:flex;gap:6px;flex-wrap:wrap'>{vpill(selected['verdict'])}{rpill(selected['route'])}{pill(f"{selected['confidence']:.0%} confidence",'info')}</div>
<p style='font-size:.9rem;margin:12px 0'>{E(selected['evidence'])}</p><h4>Suggested reply</h4><div class='reply'>{E(selected['student_reply'])}</div></div>""", unsafe_allow_html=True)
            if edit:
                st.markdown(f"<div class='card'><h4>Proposed change</h4><div class='diff'><div class='f'>{E(edit['field'])}</div><div class='m'>− {E(edit.get('find'))}</div><div class='p'>+ {E(edit.get('replace'))}</div></div></div>", unsafe_allow_html=True)
            if selected['reportId'] in dec:
                st.success('Decision recorded: ' + dec[selected['reportId']]['action'])
            else:
                st.markdown("<div class='card'><h4>Your decision</h4>", unsafe_allow_html=True)
                replacement = st.text_input('Edit proposed value', str(edit.get('replace', '')), disabled=not bool(edit), key='rep_' + selected['reportId'])
                confirmed = st.checkbox('Record this decision in the audit trail.', key='confirm_' + selected['reportId'])
                b1, b2 = st.columns(2)
                if b1.button('✓ Approve & Apply Fix', type='primary', use_container_width=True, key='ap_' + selected['reportId']):
                    try:
                        if not confirmed: raise ValueError('Confirm the audit action before approving.')
                        outcome=decide(selected['reportId'], 'approve', replacement=replacement)
                        st.session_state['decision_message']=f"Status: Approved · Action: Repair applied successfully · Question ID: {outcome['questionId']}"
                        st.rerun()
                    except (ValueError, LookupError, FileExistsError) as e: st.error(str(e))
                if b2.button('✕ Reject', use_container_width=True, key='rj_' + selected['reportId']):
                    if not confirmed: st.error('Confirm the audit action before rejecting.')
                    else:
                        try: decide(selected['reportId'], 'reject', reason='Faculty rejected proposal'); st.rerun()
                        except (ValueError, LookupError, FileExistsError) as e: st.error(str(e))
                st.markdown("</div>", unsafe_allow_html=True)

# ================================================= APPROVED
elif page == 'Approved':
    st.markdown("<p class='h-title'>Approved repairs</p><p class='h-sub'>Faculty-approved decisions and applied changes.</p>", unsafe_allow_html=True)
    rows=[x for x in decisions() if x['action']=='approved']
    if not rows: st.markdown("<div class='empty'><b>No approved repairs yet</b></div>", unsafe_allow_html=True)
    else: st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)

# ================================================= AUDIT
elif page == 'Audit Trail':
    st.markdown("<p class='h-title'>Audit trail</p><p class='h-sub'>Every faculty decision, recorded for traceability.</p>", unsafe_allow_html=True)
    rows = decisions()
    if not rows:
        st.markdown("<div class='empty'><b>No decisions yet</b><br>Approved and rejected reports will appear here.</div>", unsafe_allow_html=True)
    else:
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button('⬇ Export CSV', df.to_csv(index=False).encode('utf-8'), 'audit_trail.csv', 'text/csv')

# ================================================= SYSTEM
else:
    st.markdown("<p class='h-title'>System</p><p class='h-sub'>Health of the analysis service.</p>", unsafe_allow_html=True)
    if ai_on:
        body = f"{pill('Operational','ok')}<p style='margin:.8rem 0 0'>Groq analysis is live · model <b>{E(llm.model)}</b></p>"
    else:
        body = f"{pill('Degraded','warn')}<p style='margin:.8rem 0 0'>Deterministic fallback active · {E(llm.error)}</p><p class='muted'>{len(items)}/{len(REPORTS)} reports remain available.</p>"
    st.markdown(f"<div class='card'><h4>AI engine</h4>{body}</div>", unsafe_allow_html=True)
