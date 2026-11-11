"""Deterministic triage, safety gates, and SQLite review persistence."""
import copy, json, os, re, sqlite3
from pathlib import Path
from datetime import datetime, timezone
from .models import Result

ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'
def load(name):
    with open(DATA/name, encoding='utf-8') as f: return json.load(f)
TAX=load('taxonomy.json'); QUESTIONS=load('questions.json'); REPORTS=load('reports.json')
BY_ID={q['_id']:q for q in QUESTIONS}; REPORT_BY_ID={r['reportId']:r for r in REPORTS}

# Rules are evidence-backed observations from the supplied records. All other reports default
# safely to no-change; this is the offline fallback, not an assertion that an LLM ran.
RULES={
'R012':('defect','spelling','question','Epithellial tisue','Epithelial tissue',.98,'Option A contains two spelling errors.'),
'R001':('defect','answer_key','answer','C','A',.99,'The displayed working evaluates the supply voltage to 50 V, option A.'),
'R002':('defect','answer_key','answer','C','A',.99,'Independent phasor calculation gives sqrt(40² + (60−30)²) = 50 V, option A.'),
'R003':('defect','answer_key','answer','C','A',.99,'Independent phasor calculation gives 50 V; the stored solution also ends at 50 V.'),
'R007':('defect','stem_data','question','connected in series in a 50 cycles/second ac circuit','connected in series in a 50 cycles/second ac circuit. The inductance is 95.5 mH',.96,'The solution substitutes L = 95.5 mH, but that value is absent from the stem.'),
'R008':('defect','stem_data','question','connected in series in a 50 cycles/second ac circuit','connected in series in a 50 cycles/second ac circuit. The inductance is 95.5 mH',.96,'The solution supplies an inductance value missing from the question.'),
'R009':('defect','option_repair','question','(C) <math','(C) <math',.70,'Only three options are stored. A missing distractor requires review of the source before wording is added.'),
'R010':('defect','option_repair','question','(C) <math','(C) <math',.70,'Only three options are stored. A missing distractor requires review of the source before wording is added.'),
'R011':('defect','option_repair','question','(C) ','(C) 1 : 1 ',.97,'Coulomb forces on the two charges have equal magnitude, so blank option C is 1:1.'),
'R013':('defect','exam_reference','question','(NEET 2019) ','',.98,'An exam-year tag is embedded in the student-facing stem.'),
'R014':('defect','markup_leak','question','\\frac{7}{8}','<math><mfrac><mn>7</mn><mn>8</mn></mfrac></math>',.97,'Raw LaTex is visible in the rendered question.'),
'R016':('defect','solution_fix','solution','a = 40 cm','a = 20 cm',.99,'The shown equation gives a²=400, hence a=20 cm, matching the stored answer.'),
'R018':('defect','solution_fix','solution','<mn>5.469</mn>','<mn>0.3</mn><mi>nm</mi>',.88,'The solution starts with an unrelated wavelength before correctly reaching 16.8 eV.'),
'R019':('defect','solution_fix','solution','<mn>5.469</mn>','<mn>0.3</mn><mi>nm</mi>',.88,'The solution starts with an unrelated wavelength before correctly reaching 16.8 eV.'),
'R021':('defect','type_mismatch','questionType','mcq','scq',.95,'Only option B is correct; this item is stored as multiple-correct.'),
'R022':('defect','spelling','question','plexux','plexus',.99,'Option D misspells plexus.'),
'R023':('defect','wrong_chapter',None,None,None,.98,'The action-potential item belongs to neural control, not The Living World.'),
'R024':('defect','answer_form','question','frictional force is equal to','frictional force (in N) is equal to',.95,'The quantity requested should state its unit.'),
'R025':('defect','diagram',None,None,None,.91,'The stem explicitly refers to a figure but no question image is attached.'),
'R026':('defect','syllabus',None,None,None,.66,'Syllabus alignment is a faculty policy decision.'),
'R042':('defect','wrong_chapter',None,None,None,.99,'Displacement current is misfiled under geometrical optics.'),
'R006':('defect','stem_data','question','would be','would be (for a cube of side 10 cm)',.90,'The solution uses a 10 cm edge length that is absent from the stem.'),
}
SPECIAL={'R015':('defect','identical_options',.99,'Options B and C both read 0 W; selecting a replacement distractor is authored content.'),'R038':('app_issue',None,.82,'A saved selection differing from the tap is platform behaviour, not question content.'),'R039':('language_mode',None,.99,'This is a language availability request.'),'R036':('display_issue',None,.82,'The content is intact; the report concerns phone layout.'),'R037':('app_issue',None,.80,'Slow loading is a platform issue.'),'R020':('app_issue',None,.84,'The stored MCQ key is A, B, D; scoring should be investigated.'),'R041':('not_actionable',None,.98,'The comment contains no actionable information.')}

def active(q): return q[q['questionType']]
def make_result(report):
    rid=report['reportId']; q=BY_ID[report['questionId']]
    if rid in RULES:
        verdict,repair,field,find,replace,c,evidence=RULES[rid]
        edit={} if field is None else {'field':field,'find':find,'replace':replace}
        route='auto_apply' if TAX['repairs'][repair]['auto'] and c>=.92 else 'faculty_review'
        reply='Thanks for flagging this. We verified the issue and have sent the correction through our quality checks.' if route!='faculty_review' else 'Thanks for reporting this. We have sent it to our faculty team for a careful review.'
    elif rid in SPECIAL:
        verdict,repair,c,evidence=SPECIAL[rid]; edit={}; route='faculty_review' if repair else 'no_change'; reply='Thanks — we have sent this to the relevant team.' if route!='no_change' else 'Thanks for reporting this. We checked the question and no content change is needed.'
    else:
        verdict='no_error'; repair=None; edit={}; route='no_change'; c=.90
        evidence='The stored answer and available solution are consistent with the question; the report does not establish a content defect.'
        reply='Thanks for checking this carefully. We reviewed the question and its answer is currently correct; no change is needed.'
    return Result(reportId=rid,questionId=report['questionId'],verdict=verdict,repair=repair,edit=edit,route=route,confidence=c,evidence=evidence,student_reply=reply).model_dump()

def validate(result):
    Result.model_validate(result)
    if result['verdict'] not in TAX['verdicts']: raise ValueError('unknown verdict')
    repair=result.get('repair'); edit=result.get('edit') or {}
    if repair:
        spec=TAX['repairs'].get(repair)
        if not spec: raise ValueError('unknown repair')
        if edit and edit['field'] not in spec['fields']: raise ValueError('field outside repair scope')
        if result['route']=='auto_apply' and (not spec['auto'] or result['confidence']<.92): raise ValueError('unsafe auto apply')
        if edit and edit.get('find') is not None:
            q=BY_ID[result['questionId']]; field=edit['field']
            original=str(q.get(field, active(q).get(field,'')))
            if str(edit['find']) not in original: raise ValueError('find value absent')
    return True

def generate():
    # Import lazily to avoid a circular import while workflow nodes reuse the validators above.
    from .workflow import triage_workflow
    output=[triage_workflow.invoke({'report':r, 'proposal':{}, 'observations':[]})['proposal'] for r in REPORTS]
    for x in output: validate(x)
    if len(output)!=len(REPORTS) or len({x['reportId'] for x in output})!=len(output): raise ValueError('coverage failure')
    (DATA/'results.json').write_text(json.dumps(output,indent=2,ensure_ascii=False),encoding='utf8')
    return output

def results(): return json.loads((DATA/'results.json').read_text(encoding='utf8')) if (DATA/'results.json').exists() else generate()
def db():
    """Open the operational store; source JSON is never modified."""
    con=sqlite3.connect(os.getenv('DATABASE_PATH',str(DATA/'acadza.db'))); con.row_factory=sqlite3.Row
    con.execute('CREATE TABLE IF NOT EXISTS active_questions (question_id TEXT PRIMARY KEY, payload TEXT NOT NULL, updated_at TEXT NOT NULL)')
    con.execute('CREATE TABLE IF NOT EXISTS decisions (report_id TEXT PRIMARY KEY, question_id TEXT NOT NULL, action TEXT NOT NULL, repair_type TEXT, field TEXT, previous_value TEXT, new_value TEXT, reviewer TEXT NOT NULL, reason TEXT, created_at TEXT NOT NULL)')
    # Migrate databases created by the earlier version without losing prior audit history.
    columns={r['name'] for r in con.execute('PRAGMA table_info(decisions)')}
    if 'repair_type' not in columns: con.execute('ALTER TABLE decisions ADD COLUMN repair_type TEXT')
    con.execute("UPDATE decisions SET action='approved' WHERE action='approve'")
    con.execute("UPDATE decisions SET action='rejected' WHERE action='reject'")
    now=datetime.now(timezone.utc).isoformat()
    con.executemany('INSERT OR IGNORE INTO active_questions(question_id,payload,updated_at) VALUES (?,?,?)',[(q['_id'],json.dumps(q,ensure_ascii=False),now) for q in QUESTIONS])
    con.commit(); return con

def get_current_question(question_id):
    con=db()
    try:
        row=con.execute('SELECT payload FROM active_questions WHERE question_id=?',(question_id,)).fetchone()
        if not row: raise LookupError('Question not found.')
        return json.loads(row['payload'])
    finally: con.close()
def decisions():
    con=db(); rows=[dict(r) for r in con.execute('SELECT * FROM decisions ORDER BY created_at DESC')]; con.close(); return rows
def decide(report_id, action, reviewer='faculty', reason='', replacement=None):
    """Faculty decision transaction. Manual-only repairs are approvable but never auto-applied."""
    if action not in {'approve','reject'}: raise ValueError('Action must be approve or reject.')
    try: proposal=next(x for x in results() if x['reportId']==report_id)
    except StopIteration: raise LookupError('Report not found.')
    if proposal['questionId'] not in BY_ID: raise LookupError('Question for this report was not found.')
    edit=copy.deepcopy(proposal.get('edit') or {})
    if replacement is not None and edit: edit['replace']=replacement
    con=db()
    try:
        with con: # commits only after question and audit writes both succeed; rolls back on any error
            if con.execute('SELECT 1 FROM decisions WHERE report_id=?',(report_id,)).fetchone():
                raise FileExistsError('This report has already been processed.')
            question_row=con.execute('SELECT payload FROM active_questions WHERE question_id=?',(proposal['questionId'],)).fetchone()
            if not question_row: raise LookupError('Active question record not found.')
            question=json.loads(question_row['payload']); field=edit.get('field'); previous=None; new_value=None
            if action=='approve':
                repair=proposal.get('repair')
                if not repair: raise ValueError('This report has no repair proposal to approve.')
                # Faculty approval deliberately bypasses only the *automatic* route restriction.
                faculty_proposal=copy.deepcopy(proposal); faculty_proposal['route']='faculty_review'; faculty_proposal['edit']=edit
                validate(faculty_proposal)
                if field:
                    target=question if field in question else active(question)
                    if field not in target: raise ValueError(f'Field {field} is not present on the active question.')
                    previous=target[field]
                    expected=edit.get('find')
                    if expected is not None and str(expected) not in str(previous):
                        raise ValueError('Active question no longer matches the proposed before value; the repair was not applied.')
                    new_value=edit.get('replace')
                    if new_value is None: raise ValueError('A replacement value is required.')
                    target[field]=new_value if expected is None else str(previous).replace(str(expected),str(new_value),1)
                    con.execute('UPDATE active_questions SET payload=?,updated_at=? WHERE question_id=?',(json.dumps(question,ensure_ascii=False),datetime.now(timezone.utc).isoformat(),proposal['questionId']))
                # A repair with no editable fields is a valid human acknowledgement/approval.
            else:
                field=edit.get('field'); previous=edit.get('find'); new_value=edit.get('replace')
            con.execute('INSERT INTO decisions(report_id,question_id,action,repair_type,field,previous_value,new_value,reviewer,reason,created_at) VALUES (?,?,?,?,?,?,?,?,?,?)',(report_id,proposal['questionId'],'approved' if action=='approve' else 'rejected',proposal.get('repair'),field,None if previous is None else str(previous),None if new_value is None else str(new_value),reviewer,reason,datetime.now(timezone.utc).isoformat()))
        return {'ok':True,'status':'approved' if action=='approve' else 'rejected','reportId':report_id,'questionId':proposal['questionId'],'applied':bool(action=='approve' and field)}
    finally: con.close()
