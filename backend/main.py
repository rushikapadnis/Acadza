import sqlite3
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from .services import results, REPORTS, BY_ID, decisions, decide, generate, get_current_question
from .llm import get_llm
app=FastAPI(title='Acadza Question Quality Operations')
class Decision(BaseModel): action:str; reviewer:str='faculty'; reason:str=''; replacement:str|None=None
@app.on_event('startup')
def start(): results() # Use the validated precomputed set; do not spend Groq quota on every restart.
@app.get('/health')
def health():
    llm=get_llm()
    return {'status':'ok','mode':llm.mode,'model':llm.model,'provider':'groq','detail':llm.error,'reports':len(REPORTS)}
@app.get('/results')
def all_results(): return results()
@app.get('/cases')
def cases():
    return [{'result':x,'report':next(r for r in REPORTS if r['reportId']==x['reportId']),'question':get_current_question(x['questionId'])} for x in results()]
@app.get('/audit')
def audit(): return decisions()
@app.post('/cases/{report_id}/decision')
def action(report_id:str, body:Decision):
    try: return decide(report_id,body.action,body.reviewer,body.reason,body.replacement)
    except LookupError as e: raise HTTPException(404,str(e))
    except FileExistsError as e: raise HTTPException(409,str(e))
    except ValueError as e: raise HTTPException(400,str(e))
    except sqlite3.Error: raise HTTPException(500,'Could not persist the faculty decision.')
