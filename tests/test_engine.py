import pytest
from backend.services import generate, REPORTS, validate
from backend.llm import GroqLLMService, DEFAULT_MODEL, get_llm

@pytest.fixture(autouse=True)
def disable_networked_llm(monkeypatch):
    """Engine tests validate deterministic output without consuming a developer API quota."""
    monkeypatch.delenv('GROQ_API_KEY', raising=False)
    get_llm.cache_clear()
    yield
    get_llm.cache_clear()
def test_all_reports_generated_and_valid():
    output=generate(); assert len(output)==44==len(REPORTS); assert len({x['reportId'] for x in output})==44
    for result in output: assert validate(result)
def test_never_auto_applies_human_repairs():
    output=generate(); assert all(x['route']!='auto_apply' or x['repair'] not in {'diagram','identical_options','wrong_question','unsound','wrong_chapter','syllabus'} for x in output)

def test_missing_groq_key_uses_safe_fallback(monkeypatch):
    monkeypatch.delenv('GROQ_API_KEY', raising=False)
    service=GroqLLMService()
    assert service.mode=='deterministic_fallback'
    assert service.model==DEFAULT_MODEL
    assert service.observe('classification', REPORTS[0], __import__('backend.services',fromlist=['BY_ID']).BY_ID[REPORTS[0]['questionId']], __import__('backend.services',fromlist=['TAX']).TAX) is None

def test_groq_model_is_configurable():
    service=GroqLLMService(api_key='test-key',model='test-model')
    assert service.model=='test-model'
