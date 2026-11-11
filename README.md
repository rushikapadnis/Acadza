# Acadza | Report → Fix

**AI-assisted question quality operations for JEE & NEET content**

Turn unstructured student error reports into evidence-backed defect decisions and safe, reviewable question corrections—with faculty in control.

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/Orchestration-LangGraph-1C3C3C)](https://langchain-ai.github.io/langgraph/)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![LLM](https://img.shields.io/badge/LLM-Groq-F55036)](https://groq.com/)
[![Database](https://img.shields.io/badge/Database-SQLite-003B57?logo=sqlite&logoColor=white)](https://www.sqlite.org/)

> **Project status:** This repository is an implementation of the Acadza AI Intern build assignment. Check the live deployment, test results and current feature status before treating any feature as production-ready.

---

## The problem

Acadza serves a large JEE/NEET question bank. When students report issues such as “answer is wrong”, “option D is missing”, or “figure not given”, the report is only a signal—not proof that the question is defective.

A useful quality workflow must distinguish genuine content defects from misunderstandings, duplicate reports, display problems and non-actionable feedback. It must also prevent an AI-generated suggestion from silently changing learning material without sufficient evidence.

**Report → Fix** is designed to support that workflow: inspect the report, examine the source question, assess the evidence, propose a narrowly scoped correction, and route the decision to automation or faculty review according to the permitted repair policy.

## What the system does

1. **Ingests reports** and associates each report with its source question.
2. **Triages the report** using the permitted verdict and repair taxonomy.
3. **Examines question content** including the question type, options, answer and solution.
4. **Produces a proposed action** with confidence, concise evidence and a student-facing reply.
5. **Validates proposed edits** against the repair type's allowed fields and safety rules.
6. **Routes the case** to automatic application, faculty review or no change, as appropriate.
7. **Supports faculty decisions** through a review console with question rendering, before/after comparison and approve, edit and reject actions.
8. **Records decisions** so review actions can be audited and retained across application restarts when persistent storage is configured.

The student's comment is treated as a lead to investigate, never as an instruction to change the question.

## Review console

The faculty console is designed around the decisions a reviewer needs to make quickly:

- **Question-oriented queue:** reports can be reviewed in the context of the question they refer to, including multiple reports about the same question.
- **Evidence-led case view:** inspect the original report, question metadata, AI verdict, confidence and reasoning evidence.
- **Readable question content:** preserve the source HTML and inline MathML so mathematical notation and options can be inspected in the browser.
- **Before/after comparison:** show the specific field and proposed change rather than obscuring a small correction inside a rewritten question.
- **Faculty control:** review, edit, approve or reject a proposal, subject to server-side validation.
- **Audit trail:** record the decision and relevant change details for traceability.

A faculty approval is a human decision. A taxonomy rule that disallows automatic application must not, by itself, prevent a permitted manual faculty approval.

## Architecture

```text
Student Reports + Question Bank + Repair Taxonomy
                         |
                         v
                 FastAPI application
                         |
                         v
                  LangGraph workflow
                         |
       +-----------------+------------------+
       |                 |                  |
       v                 v                  v
  Classification    Verification      Repair proposal
       |                 |                  |
       +-----------------+------------------+
                         |
                         v
                Pydantic validation
                         |
                         v
             Taxonomy and safety guards
                         |
              +----------+----------+
              |          |          |
              v          v          v
          Auto apply  Faculty review  No change
                         |
                         v
                SQLite decision log
                         |
                         v
                Streamlit review UI
```

### Technology choices

| Layer | Technology | Responsibility |
|---|---|---|
| API | FastAPI | Application endpoints and workflow access |
| Orchestration | LangGraph | Structured triage and repair workflow |
| LLM provider | Groq | Language-model inference through a centralized client |
| Model integration | `langchain-groq` / `ChatGroq` | Connect Groq to LangChain and LangGraph |
| Validation | Pydantic | Validate model outputs, requests and proposed edits |
| Faculty interface | Streamlit | Queue, case inspection and review actions |
| Persistence | SQLite | Review decisions and audit history |
| Source data | JSON | Questions, reports, taxonomy and generated triage results |

## AI workflow and safety

The workflow separates language-model judgement from deterministic enforcement. The model can help interpret a report and propose a repair; application code remains responsible for checking whether that proposal is allowed.

### Triage output

Each report is represented by a structured result containing:

| Field | Meaning |
|---|---|
| `reportId` | Original report identifier |
| `questionId` | Associated question identifier |
| `verdict` | A verdict key defined by the supplied taxonomy |
| `repair` | An allowed repair key, or `null` when no repair applies |
| `edit` | A surgical proposed change, not a full question rewrite |
| `route` | `auto_apply`, `faculty_review` or `no_change` |
| `confidence` | Confidence score between 0 and 1 |
| `evidence` | Concise explanation supporting the decision |
| `student_reply` | Clear, respectful response for the reporting student |

### Safety principles

- **Closed taxonomy:** verdicts and repair types must come from `taxonomy.json`; the model cannot invent new categories.
- **Field-level scope:** a repair may change only fields permitted by its taxonomy definition.
- **Surgical edits:** preserve unrelated question content and avoid rewriting an entire question for a small correction.
- **Evidence before action:** student comments are checked against the question and available answer/solution evidence.
- **Human review:** repairs that are not eligible for automatic application, uncertain cases and failed validations are routed for review or no change.
- **Server-side validation:** frontend controls are not a security or correctness boundary; approval and edit operations must be validated by the backend.
- **Traceability:** retain the proposed change and record the faculty decision separately from the original source data.
- **Honest uncertainty:** when the evidence is insufficient, do not manufacture a correction.

**Automatic application and faculty approval are different permissions.** `auto: false` means the system must not apply that repair autonomously. It may still be presented for manual approval when the taxonomy and validation rules permit it.

## Groq configuration

Groq is the configured LLM provider. The application uses a centralized `ChatGroq` client for LangGraph nodes. The model name is configurable; the example below uses `openai/gpt-oss-20b` as a Groq-hosted model identifier. This does **not** mean the application calls the OpenAI API.

Create a `.env` file in the project root from the committed template:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Then set only your private key in `.env`:

```env
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=openai/gpt-oss-20b
```

Create a key in the [Groq Console](https://console.groq.com/keys). Keep the key private and never commit `.env` to Git.

### No-key and API-failure behaviour

The application should remain usable when the Groq key is absent or the API is unavailable. In that situation, it should clearly identify fallback mode and use validated precomputed results or the project's deterministic fallback path. Faculty review actions should remain available if the configured backend and database are running.

Fallback output must not be represented as a fresh LLM analysis. Groq free-tier limits and availability can change; check the current Groq account limits rather than assuming unlimited inference.

## Dataset

The assignment supplies three JSON files under `data/`:

| File | Description |
|---|---|
| `questions.json` | 43 questions in Acadza's production-style format, including HTML, inline MathML, options and type-specific answer fields |
| `reports.json` | 44 student reports with report ID, question ID, student ID, source, timestamp and comment |
| `taxonomy.json` | Allowed verdicts and repair types, including editable-field scope and automatic-application policy |

The supplied data is intentionally imperfect and includes misleading reports. The system must inspect the actual source content and taxonomy rather than relying on assumptions about the dataset.

### Results file

`data/results.json` contains the triage output for the supplied reports. It should contain exactly one result per input report, with original identifiers preserved and no duplicate or missing report IDs. The results are generated by the project's triage workflow and should be validated before submission.

Example shape (illustrative only):

```json
[
  {
    "reportId": "R000",
    "questionId": "000000000000000000000000",
    "verdict": "defect",
    "repair": "answer_key",
    "edit": {
      "field": "answer",
      "find": "B",
      "replace": "D"
    },
    "route": "faculty_review",
    "confidence": 0.93,
    "evidence": "The proposed correction is supported by the question and independent verification.",
    "student_reply": "Thanks for reporting this. We have sent the question for faculty review."
  }
]
```

The example is illustrative; actual verdicts, repair keys, edit structures and routes must conform to the supplied taxonomy and implementation rules.

## Run locally

### Requirements

- Python 3.11 or a compatible version supported by the project's dependencies
- `pip`
- A Groq API key for live LLM inference (optional if fallback mode is supported)

### 1. Create and activate a virtual environment

**Windows PowerShell:**

```powershell
py -3.11 -m venv Acadza
.\Acadza\Scripts\Activate.ps1
```

**macOS / Linux:**

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 3. Configure environment variables

Create `.env` in the project root and add the Groq configuration shown above. If you are testing fallback mode, leave `GROQ_API_KEY` unset.

### 4. Run tests

```bash
python -m pytest -q
```

### 5. Start the FastAPI backend

From the project root, in terminal 1:

```bash
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Backend health check: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

### 6. Start the Streamlit console

In terminal 2, from the project root:

```bash
python -m streamlit run frontend/app.py
```

Open: [http://localhost:8501](http://localhost:8501)

> If the repository uses different module paths or entry points, update these commands to match the actual files. Do not create duplicate entry points just to match this documentation.

## Configuration and persistence

| Variable | Purpose | Example |
|---|---|---|
| `GROQ_API_KEY` | Groq API credential | Set privately in `.env` |
| `GROQ_MODEL` | Groq-hosted model identifier | `openai/gpt-oss-20b` |

The default local SQLite database is `data/acadza.db`. Set `DATABASE_PATH` to override it. For hosted deployment, attach and configure persistent storage if review decisions and audit records must survive instance replacement or redeployment. An ephemeral filesystem must not be described as durable storage.

## Deployment

The repository includes a Render blueprint (`render.yaml`) for the Streamlit console. It installs `requirements.txt` and starts `frontend/app.py`. It does not configure a persistent disk, so its SQLite audit database is ephemeral on Render; attach a disk and set `DATABASE_PATH` to a path on that disk before claiming durable audit storage. The FastAPI service is runnable locally via the command above, but a separate Render API service is a manual deployment choice because the current Streamlit console uses the shared application service layer directly.

Before sharing a live URL:

- Deploy the backend and frontend with compatible service URLs.
- Configure `GROQ_API_KEY` as a private environment variable if live inference is enabled.
- Configure persistent storage for SQLite if the deployment relies on local SQLite files.
- Verify the health endpoint and the public console URL.
- Test a report review, edit, approval and rejection on the deployed application.
- Confirm the application can load precomputed results if Groq is unavailable.
- Keep the deployment available for the assignment's required evaluation period.

Do not put API keys, database credentials or private environment files in the repository.

## Quality checks before submission

Run the checks below and report their actual outcomes in the submission. Do not mark a check as passed unless it has been executed.

- [ ] All supplied reports have exactly one result in `data/results.json`.
- [ ] No report IDs are missing or duplicated.
- [ ] Every verdict and repair key is permitted by `taxonomy.json`.
- [ ] Every edit is within the allowed field scope.
- [ ] Automatic application respects the taxonomy's `auto` policy.
- [ ] Faculty can manually approve eligible proposals, including permitted `auto: false` repairs.
- [ ] Invalid or stale edits are rejected safely.
- [ ] Approve, edit and reject actions work end-to-end.
- [ ] Failed database operations do not show false success or leave partial changes.
- [ ] Audit history records faculty decisions.
- [ ] Decisions persist after application restart when persistent storage is configured.
- [ ] HTML and MathML question content renders correctly.
- [ ] Groq API errors and missing credentials trigger an explicit fallback state.
- [ ] The deployed console has been tested independently of the local environment.

## Repository deliverables

| Deliverable | Purpose |
|---|---|
| `results.json` | Machine-evaluable triage output for all supplied reports |
| `PROMPTS.md` | Verbatim product prompts, key coding-assistant prompts, prompt iterations, failure analysis and design-decision log |
| `PRODUCT.md` | Concise product-thinking response to the four assignment questions (maximum one page) |
| Faculty console | Live review experience with question rendering, evidence, diff and faculty actions |
| Screen recording | Three-minute walkthrough of the console and one challenging case |

For the assignment submission, include the public repository URL, live console URL, recording URL and answers to the four questions in the original assignment email.

## Product principles

1. **Protect the learner:** a wrong answer or broken question can undermine a student's preparation and confidence.
2. **Verify before changing:** a report is evidence to investigate, not proof of a defect.
3. **Make changes reviewable:** faculty should see exactly what changes and why.
4. **Keep humans accountable:** high-impact or uncertain content decisions belong with qualified reviewers.
5. **Measure quality, not activity:** optimise for correctly resolved defects and safe turnaround, not simply the number of reports processed.

---

**Built for the Acadza AI Intern assignment — Report → Fix.**
