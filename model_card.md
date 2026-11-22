# DocuBot Model Card

## 1. System Overview

**What is DocuBot trying to do?**

DocuBot searches local Markdown documentation and, in RAG mode, asks a Gemini model to answer from relevant retrieved sections. The goal is to answer codebase questions with documented evidence and refuse unsupported requests.

**What inputs does DocuBot take?**

It takes a user question, Markdown or text files in `docs/`, optional retrieval settings, and `GEMINI_API_KEY` for LLM modes.

**What outputs does DocuBot produce?**

Retrieval-only mode returns raw source snippets. Naive and RAG modes produce natural-language answers, and RAG cites the source files it used.

## 2. Retrieval Design

**How does your retrieval system work?**

- How do you turn documents into an index?
- How do you score relevance for a query?
- How do you choose top snippets?

DocuBot builds an inverted index of lowercase alphanumeric words to filenames. Retrieval divides Markdown by headings and scores section text by the number of unique meaningful query words it contains. It sorts matches by descending score and returns the top `top_k` snippets.

**What tradeoffs did you make?**

The heading-based unit is more precise than an entire file, but it can include nearby irrelevant text. The index and scoring are fast and understandable, but they do not use stemming, phrases, or semantic similarity.

## 3. Use of the LLM (Gemini)

**When does DocuBot call the LLM and when does it not?**

- Naive LLM mode: calls Gemini with a generic question and no corpus context.
- Retrieval only mode: never calls the LLM; it returns matching snippets or refusal text.
- RAG mode: retrieves first and calls Gemini only when snippets pass the evidence guardrail.

**What instructions do you give the LLM to keep it grounded?**

The RAG prompt requires the model to use only supplied snippets, refuse when evidence is insufficient, use an exact refusal sentence, and mention source files.

## 4. Experiments and Comparisons

| Query | Naive LLM: helpful or harmful? | Retrieval only: helpful or harmful? | RAG: helpful or harmful? | Notes |
|------|---------------------------------|--------------------------------------|---------------------------|-------|
| Where is the auth token generated? | Harmful for the first run: a stale model name returned an API error. After correction, naive mode lacked project context and asked for code. | Helpful: returned `AUTH.md` token-generation sections. | Helpful: identified `generate_access_token` in `auth_utils.py` and cited `AUTH.md`. | RAG was grounded in retrieved evidence. |
| How do I connect to the database? | Harmful: suggested invented database credentials and ORM patterns. | Helpful: returned `DATABASE.md` connection sections. | Helpful: stated `DATABASE_URL`, SQLite, and PostgreSQL examples from `DATABASE.md`. | This showed a clear grounding improvement. |
| Which endpoint lists all users? | Harmful: guessed generic endpoints instead of the documented route. | Helpful: returned `GET /api/users` and its response. | Helpful: answered `GET /api/users` and cited `API_REFERENCE.md`. | Retrieval-only was accurate but raw; RAG was easier to read. |
| How does a client refresh an access token? | Harmful: produced a generic OAuth refresh-token process unsupported by these docs. | Helpful: returned authentication workflow and API refresh sections. | Helpful: described `POST /api/refresh`, the Bearer header, and cited both relevant files. | RAG separated documented behavior from generic OAuth assumptions. |

**What patterns did you notice?**

- Naive generation is untrustworthy when it adds plausible variable names or OAuth details absent from the docs.
- Retrieval-only is clearly better for exact source-backed facts.
- RAG is clearly better when it explains matching evidence concisely and cites files.

## 5. Failure Cases and Guardrails

**Describe at least two concrete failure cases you observed.**

**Failure case 1:** “Is there any mention of payment processing in these docs?” The system retrieved no evidence and returned “I do not know based on these docs.” That refusal was appropriate.

**Failure case 2:** Naive mode answered the database question with invented `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, and `DB_PASSWORD` fields. The docs instead specify `DATABASE_URL`; the answer should have been grounded in that variable and its SQLite/PostgreSQL examples.

**When should DocuBot say “I do not know based on the docs I have”?**

- When no snippets match the query.
- When all candidates have no meaningful query-word matches.
- When retrieved text does not discuss the requested topic.

**What guardrails did you implement?**

The retrieval guardrail rejects empty results or candidates with no meaningful query-word match. RAG repeats the refusal when snippets are empty or weak. The RAG prompt forbids invented endpoints, functions, and configuration values.

## 6. Limitations and Future Improvements

**Current limitations**

1. Indexing is keyword-based and misses synonyms and semantic meaning.
2. Markdown heading and paragraph boundaries can include surrounding irrelevant text.
3. The guardrail uses a simple match threshold rather than a confidence model.

**Future improvements**

1. Add stemming or a lightweight BM25-style score.
2. Use smaller Markdown chunks with heading metadata preserved.
3. Require stronger match thresholds or a dedicated relevance classifier.

## 7. Responsible Use

**Where could this system cause real world harm if used carelessly?**

An unsupported answer could cause developers to configure nonexistent variables, call wrong endpoints, weaken authentication, or use incorrect database settings.

**What instructions would you give real developers who want to use DocuBot safely?**

- Verify source filenames and snippets before acting on an answer.
- Treat confident or generic LLM details as hypotheses until matched to project documentation.
- Keep refusal behavior enabled for unsupported or out-of-scope questions.
