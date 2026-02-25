# Career Assistant AI Agent

A self-evaluating AI agent that communicates with potential employers on your behalf, built with **Groq** and **Gradio**. Uses a dual-model architecture: **llama-3.3-70b-versatile** for response generation and **openai/gpt-oss-120b** for response evaluation.

## Architecture

The system consists of 4 core components:

| Component | Description |
|---|---|
| **Career Agent** | Primary agent (llama-3.3-70b-versatile) that generates professional responses using CV/profile context |
| **Response Evaluator** | Self-critic (openai/gpt-oss-120b) LLM-as-a-Judge that scores responses on 7 criteria |
| **Pushover Notification** | Sends mobile alerts for new messages, approvals, and unknown questions |
| **Unknown Question Detector** | Detects questions outside expertise and triggers human intervention |

### System Flow

```
Employer Message (Gradio UI)
        |
  Push Notification (instant alert)
        |
  Career Agent (llama-3.3-70b) + CV Context
        |
  Tool Call? --> Yes --> Execute Tool (record_user_details / record_unknown_question)
        | No
  Generate Draft Response
        |
  Evaluator Agent (gpt-oss-120b, Self-Critic Judge)
        |
  Score >= 7? --> Yes --> Approved --> Push Notification --> Return to Employer
        | No
  Unknown? --> Graceful Decline + Push Alert
  Retry?   --> Revision Loop (max 2 attempts)
        |
  Save to conversation_log.json
```

## Project Structure

```
career-assistant-agent/
├── 20220808026_agent.py      # Main agent source code
├── test_results.json         # Test execution results (3/3 passed)
├── conversation_log.json     # Conversation history with evaluations
├── README.md                 # This file
├── reports/
│   ├── report.pdf            # Design and implementation report
│   ├── report.tex            # LaTeX source for report
│   ├── prompt_documentation.pdf  # Prompt documentation
│   └── prompt_documentation.tex  # LaTeX source for prompt docs
└── me/
    ├── summary.txt           # Personal summary for agent context
    └── linkedin.pdf          # LinkedIn profile for agent context
```

## Quick Start

### Prerequisites
```bash
pip install groq gradio pypdf python-dotenv requests
```

### Environment Variables
Create a `.env` file:
```
GROQ_API_KEY=your_groq_api_key
PUSHOVER_USER=your_pushover_user_key
PUSHOVER_TOKEN=your_pushover_app_token
```

### Run the Agent
```bash
python 20220808026_agent.py
```
Opens Gradio chat interface at `http://127.0.0.1:7860`

## Test Cases

| # | Test | Tool Triggered | Score | Result |
|---|---|---|---|---|
| 1 | **Job Offer** - Employer sends email + interview invite | record_user_details | 9/10 | PASSED |
| 2 | **Technical Question** - REST API and JWT experience | None (expected) | 9/10 | PASSED |
| 3 | **Unknown Question** - Rust/Haskell blockchain code | record_unknown_question | 8/10 | PASSED |

## Key Features

### Self-Evaluating Response Loop
- Agent generates a draft response
- Evaluator (different model) scores it on 7 criteria (professional, clarity, completeness, safety, relevance, confidence, unknown detection)
- Score < 7 triggers automatic revision with feedback injection
- Max 2 attempts before graceful decline

### Anti-Hallucination System
- **Agent-side:** CRITICAL ACCURACY RULES enforce that only technologies from the profile context can be claimed
- **Evaluator-side:** Explicit technology whitelist flags any fabricated experience as `safety=false, score <= 4`
- **Cross-model evaluation:** Different models for generation and evaluation eliminates same-model bias

### Tool Execution
- **record_user_details(email, name, notes)** - Records employer contact info via Pushover
- **record_unknown_question(question)** - Logs unanswerable questions via Pushover

### Mobile Notifications (Pushover)
5 notification types:
1. New employer message (instant)
2. Response approved (score >= 7)
3. Failed to answer / unknown question
4. Low confidence flagged for human review
5. Tool execution alerts (contact recorded, unknown logged)

### Evaluation Criteria (Structured JSON)
```json
{
  "score": 9,
  "confidence": 0.9,
  "is_unknown": false,
  "professional": true,
  "clarity": true,
  "completeness": true,
  "safety": true,
  "relevance": true,
  "feedback": "Well-structured, professional response..."
}
```

### Bonus Features
- **Memory:** Full conversation history saved to conversation_log.json
- **Confidence Visualization:** Score bar and boolean checks displayed in chat

## Tech Stack

| Technology | Purpose |
|---|---|
| **Groq (llama-3.3-70b-versatile)** | Career Agent — response generation |
| **Groq (openai/gpt-oss-120b)** | Evaluator Agent — response evaluation |
| **Gradio** | Chat interface (frontend) |
| **Pushover API** | Mobile push notifications |
| **pypdf** | LinkedIn PDF parsing |
| **Pydantic** | Structured evaluation model |
| **Python** | Core language |

## Author

**Yunus Emre Balci**
Computer Engineering Student - Akdeniz University
