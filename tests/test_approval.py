import os
import sqlite3
import pytest
from backend.services import decide, decisions, get_current_question, db

@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    path=tmp_path/'approval.db'
    monkeypatch.setenv('DATABASE_PATH',str(path))
    yield path

def test_approve_valid_repair_updates_active_question_and_audit():
    outcome=decide('R012','approve',reviewer='qa')
    assert outcome['status']=='approved' and outcome['applied'] is True
    question=get_current_question(outcome['questionId'])
    assert 'Epithelial tissue' in question['scq']['question']
    row=decisions()[0]
    assert row['action']=='approved' and row['repair_type']=='spelling' and row['reviewer']=='qa'

def test_faculty_edited_repair_is_applied_and_recorded():
    outcome=decide('R022','approve',replacement='plexus (corrected)',reviewer='qa')
    question=get_current_question(outcome['questionId'])
    assert 'plexus (corrected)' in question['scq']['question']
    assert decisions()[0]['new_value']=='plexus (corrected)'

def test_manual_only_auto_false_repair_can_be_faculty_approved():
    outcome=decide('R015','approve',reviewer='qa')
    assert outcome['status']=='approved' and outcome['applied'] is False
    row=decisions()[0]
    assert row['repair_type']=='identical_options' and row['action']=='approved'

def test_reject_preserves_question():
    before=get_current_question('61dffbec08489156b684bd22')
    outcome=decide('R012','reject',reviewer='qa',reason='not approved')
    after=get_current_question('61dffbec08489156b684bd22')
    assert outcome['status']=='rejected' and before==after

def test_duplicate_approval_is_conflict():
    decide('R012','approve')
    with pytest.raises(FileExistsError): decide('R012','approve')

def test_invalid_repair_field_is_rejected_without_mutation(monkeypatch):
    import backend.services as service
    original=service.results
    def bad_results():
        data=original()
        row=next(x for x in data if x['reportId']=='R012').copy()
        row['edit']={'field':'chapter','find':'x','replace':'y'}
        return [row if x['reportId']=='R012' else x for x in data]
    monkeypatch.setattr(service,'results',bad_results)
    with pytest.raises(ValueError): decide('R012','approve')
    assert decisions()==[]

def test_missing_report_is_clear_error():
    with pytest.raises(LookupError,match='Report not found'): decide('R999','approve')

def test_database_failure_rolls_back_question_and_audit():
    con=db()
    con.execute("CREATE TRIGGER fail_decision BEFORE INSERT ON decisions BEGIN SELECT RAISE(ABORT, 'simulated database failure'); END;")
    con.commit(); con.close()
    before=get_current_question('61dffbec08489156b684bd22')
    with pytest.raises(sqlite3.Error): decide('R012','approve')
    assert get_current_question('61dffbec08489156b684bd22')==before
    assert decisions()==[]

def test_duplicate_question_repair_is_not_applied_twice():
    decide('R001','approve')
    with pytest.raises(ValueError,match='no longer matches'): decide('R003','approve')

def test_persistence_survives_new_connection():
    decide('R012','approve')
    assert decisions()[0]['report_id']=='R012'
    assert 'Epithelial tissue' in get_current_question('61dffbec08489156b684bd22')['scq']['question']

def test_api_handler_returns_success_and_conflict():
    from fastapi import HTTPException
    from backend.main import action, Decision
    response=action('R012',Decision(action='approve',reviewer='qa'))
    assert response['status']=='approved'
    with pytest.raises(HTTPException) as error:
        action('R012',Decision(action='approve',reviewer='qa'))
    assert error.value.status_code==409
