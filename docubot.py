"""
Core DocuBot class responsible for:
- Loading documents from the docs/ folder
- Building a simple retrieval index (Phase 1)
- Retrieving relevant snippets (Phase 1)
- Supporting retrieval only answers
- Supporting RAG answers when paired with Gemini (Phase 2)
"""

import os
import glob
import re

class DocuBot:
    def __init__(self, docs_folder="docs", llm_client=None):
        """
        docs_folder: directory containing project documentation files
        llm_client: optional Gemini client for LLM based answers
        """
        self.docs_folder = docs_folder
        self.llm_client = llm_client

        # Load documents into memory
        self.documents = self.load_documents()  # List of (filename, text)

        # Build a retrieval index (implemented in Phase 1)
        self.index = self.build_index(self.documents)

    # -----------------------------------------------------------
    # Document Loading
    # -----------------------------------------------------------

    def load_documents(self):
        """
        Loads all .md and .txt files inside docs_folder.
        Returns a list of tuples: (filename, text)
        """
        docs = []
        pattern = os.path.join(self.docs_folder, "*.*")
        for path in glob.glob(pattern):
            if path.endswith(".md") or path.endswith(".txt"):
                with open(path, "r", encoding="utf8") as f:
                    text = f.read()
                filename = os.path.basename(path)
                docs.append((filename, text))
        return docs

    # -----------------------------------------------------------
    # Index Construction (Phase 1)
    # -----------------------------------------------------------

    def build_index(self, documents):
        """
        Build a tiny inverted index mapping lowercase words to the documents
        they appear in.
        """
        index = {}
        for filename, text in documents:
            words = set(re.findall(r"[a-z0-9]+", text.lower()))
            for word in words:
                index.setdefault(word, [])
                if filename not in index[word]:
                    index[word].append(filename)
        return index

    # -----------------------------------------------------------
    # Scoring and Retrieval (Phase 1)
    # -----------------------------------------------------------

    def score_document(self, query, text):
        """
        Count unique meaningful query words that appear in the text.
        """
        stop_words = {
            "a", "an", "and", "are", "do", "does", "for", "how", "is",
            "in", "of", "the", "to", "what", "which", "where", "with",
            "any", "mention", "processing", "docs", "these", "does", "does"
        }
        query_words = set(re.findall(r"[a-z0-9]+", query.lower()))
        query_words -= stop_words
        text_words = set(re.findall(r"[a-z0-9]+", text.lower()))
        return len(query_words & text_words)

    def retrieve(self, query, top_k=3):
        """
        Select the top_k paragraph-sized snippets with the highest relevance.
        """
        results = []
        for filename, text in self.documents:
            section_starts = list(re.finditer(r"(?m)^#{1,6}\s+.+$", text))
            if not section_starts:
                section_starts = [re.match(r"(?s).*", text)]

            for i, heading_match in enumerate(section_starts):
                if i + 1 < len(section_starts):
                    end = section_starts[i + 1].start()
                else:
                    end = len(text)
                snippet = text[heading_match.start():end].strip()
                if not snippet:
                    continue
                score = self.score_document(query, snippet)
                if score > 0:
                    results.append((score, filename, snippet))

        results.sort(key=lambda item: (-item[0], item[1], item[2]))
        retrieved = [(filename, snippet) for _, filename, snippet in results[:top_k]]
        return retrieved

    # -----------------------------------------------------------
    # Answering Modes
    # -----------------------------------------------------------

    def answer_retrieval_only(self, query, top_k=3):
        """
        Phase 1 retrieval only mode.
        Returns raw snippets and filenames with no LLM involved.
        """
        snippets = self.retrieve(query, top_k=top_k)

        if not snippets or all(self.score_document(query, text) < 1 for _, text in snippets):
            return "I do not know based on these docs."

        formatted = []
        for filename, text in snippets:
            formatted.append(f"[{filename}]\n{text}\n")

        return "\n---\n".join(formatted)

    def answer_rag(self, query, top_k=3):
        """
        Phase 2 RAG mode.
        Uses student retrieval to select snippets, then asks Gemini
        to generate an answer using only those snippets.
        """
        if self.llm_client is None:
            raise RuntimeError(
                "RAG mode requires an LLM client. Provide a GeminiClient instance."
            )

        snippets = self.retrieve(query, top_k=top_k)

        if not snippets or all(self.score_document(query, text) < 1 for _, text in snippets):
            return "I do not know based on these docs."

        return self.llm_client.answer_from_snippets(query, snippets)

    # -----------------------------------------------------------
    # Bonus Helper: concatenated docs for naive generation mode
    # -----------------------------------------------------------

    def full_corpus_text(self):
        """
        Returns all documents concatenated into a single string.
        This is used in Phase 0 for naive 'generation only' baselines.
        """
        return "\n\n".join(text for _, text in self.documents)
