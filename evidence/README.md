# Evidence Directory — Day 22: LangSmith + Prompt Versioning

This directory contains all required evidence files for the lab submission.

## Files

| File | Description |
|------|-------------|
| `01_langsmith_traces.png` | Screenshot of LangSmith dashboard showing ≥ 50 traces |
| `02_prompt_hub.png` | Screenshot of Prompt Hub showing both prompt versions |
| `02_ab_routing_log.txt` | Console output of A/B routing (50 queries with v1/v2 labels) |
| `03_ragas_scores.png` | Terminal screenshot showing RAGAS comparison table |
| `03_ragas_report.json` | Full RAGAS evaluation report (copy of data/ragas_report.json) |
| `04_pii_demo_log.txt` | Console output of PII detection demo (6 test cases) |
| `04_json_demo_log.txt` | Console output of JSON formatter demo (5 test cases) |

## V1 vs V2 Prompt Analysis

### Prompt V1 — Concise & Friendly
- **Style**: Direct, 2–4 sentence answers
- **Behavior**: Minimal formatting, quick responses
- **Best for**: Simple factual questions where brevity is preferred
- **Expected metric**: Higher answer_relevancy (direct answers match questions better)

### Prompt V2 — Structured & Professional
- **Style**: Answer / Key Points / Confidence format
- **Behavior**: Verbose with structured markdown output
- **Best for**: Complex questions requiring depth and organization
- **Expected metric**: Higher faithfulness (more careful extraction from context)

### Comparison Analysis

V1 tends to be more concise and directly addresses questions with 2–4 sentences.
V2 provides more structured responses with clear sections, which may improve faithfulness
since the model is prompted to carefully read the context before answering.

The structured format of V2 (Answer / Key Points / Confidence) encourages more careful
grounding in the retrieved context, which typically results in higher faithfulness scores.
V1's direct style may score higher on answer_relevancy since it closely mirrors the question
format without adding unnecessary structure.

In practice, the best prompt depends on the use case:
- Production chatbots → V1 (concise, user-friendly)
- Research/analysis tools → V2 (structured, verifiable)
