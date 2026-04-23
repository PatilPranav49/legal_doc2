import time
import hashlib
import tempfile
import os
from pathlib import Path

from layer0_pii.redactor import PIIRedactor
from layer1_extraction.extractor import DocumentExtractor
from layer1_5_translation.translator import LanguageTranslator
from utils.cache import get_cache
from utils.logger import get_logger
from config import Config

from core.clause_splitter import ClauseSplitter
from layer3_llm.llm_adapter import LegalLLMAdapter
from layer2_retrieval.pipeline_adapter import LegalRetrievalAdapter

from core.doc_classifier import classify_document, is_risk_relevant

logger = get_logger(__name__)


class LegalDocPipeline:

    def __init__(self):
        self.extractor   = DocumentExtractor()
        self.redactor    = PIIRedactor()
        self.translator  = LanguageTranslator()
        self.cache       = get_cache()

        self.retriever   = LegalRetrievalAdapter()

        # ✅ ADDED (LLM INIT)
        self.llm = LegalLLMAdapter()

    def process(self, file_path: str, language_hint: str = None) -> dict:
        path = Path(file_path)
        if not path.exists():
            return self._error_result(str(path.name), f"File not found: {file_path}")

        file_bytes = path.read_bytes()
        return self._run(file_bytes, path.name, language_hint)

    def process_bytes(self, file_bytes: bytes, filename: str,
                      language_hint: str = None) -> dict:
        return self._run(file_bytes, filename, language_hint)

    def _run(self, file_bytes: bytes, filename: str,
             language_hint: str = None) -> dict:

        t0 = time.time()
        cache_key = self._cache_key(file_bytes, filename, language_hint)

        if Config.ENABLE_CACHE and self.cache:
            cached = self.cache.get(cache_key)
            if cached:
                cached["cached"] = True
                return cached

        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        try:
            extraction = self.extractor.extract(tmp_path, language_hint=language_hint)
        finally:
            os.unlink(tmp_path)

        if not extraction["success"]:
            return self._error_result(filename, extraction.get("error", "Extraction failed"))

        raw_text = extraction.get("text", "") or ""
        if not raw_text.strip():
                return self._error_result(filename, "No text could be extracted from document")
        raw_text = raw_text.replace("Sasstam", "System")
        extraction_method = extraction.get("extraction_method", "unknown")
        page_count = extraction.get("pages", 1)
        demo_mode = extraction.get("demo_mode", False)

        pii_result = self.redactor.redact(raw_text)
        safe_text = pii_result.redacted_text

        if not safe_text.strip():
            english_text  = ""
            detected_lang = "unknown"
            lang_name     = "Unknown"
            lang_confidence = 0.0
        else:
            if language_hint:
                detected_lang   = language_hint
                lang_name       = Config.get_language_name(language_hint)
                lang_confidence = 1.0
            else:
                lang_result     = self.translator.detect_language(safe_text)
                detected_lang   = lang_result["lang_code"]
                lang_name       = Config.get_language_name(detected_lang)
                lang_confidence = lang_result["confidence"]

            english_text = self.translator.translate_to_english(safe_text)
            english_text = self.redactor.restore(english_text, pii_result)

        # 🔥 FIXED BLOCK (Correct Pipeline Flow)
        legal_context = []
        doc_type = classify_document(english_text)
        show_risk = is_risk_relevant(doc_type)
        

        if raw_text and len(raw_text.strip()) > 20:
            try:
                clean_text = " ".join(raw_text.split())

                original_clauses = ClauseSplitter.split(clean_text)

                filtered_clauses = [
                    c.strip() for c in original_clauses if len(c.strip()) >= 30
                ]

                if not filtered_clauses:
                    filtered_clauses = [clean_text[:500]]
                                # debug point
                print("SAFE TEXT LENGTH:", len(safe_text))
                print("CLAUSES COUNT:", len(original_clauses))
                print("FILTERED CLAUSES:", len(filtered_clauses))
                # debug point


                batch_explanations = self.llm.explain_clauses_batch(filtered_clauses)


                for idx, clause in enumerate(filtered_clauses):

                    explanation = (
                                    batch_explanations[idx]
                                    if idx < len(batch_explanations)
                                    else "General information"
)

                    legal_context.append({
                            "clause_id": idx + 1,
                            "original_clause": clause,
                            "english_clause": clause,
                            "context": [],
                            "explanation": explanation,
                            "type": "General"
                        })

                      
                    
                        
                        

                   

            except Exception as e:
                logger.error(f"Clause pipeline error: {e}")
                legal_context = []
        elapsed = round(time.time() - t0, 2)
        

        for clause in legal_context:
            if not show_risk:
                clause.pop("risk", None)
        
        if not raw_text.strip():
            raw_text = safe_text

        result = {
            "document_type":     doc_type,        
            "show_risk":         show_risk,     
            
            "original_text":      raw_text,
            "pii_redacted_text":  safe_text,
            "english_text":       english_text,

            "legal_context":      legal_context,
            "retrieval_count":    len(legal_context),

            "source_file":        filename,
            "success":            True,
            "error":              None,

            "extraction_method":  extraction_method,
            "page_count":         page_count,
            "char_count":         len(raw_text),

            "detected_language":  detected_lang,
            "language_name":      lang_name,
            "lang_confidence":    lang_confidence,

            "pii_found":          pii_result.pii_found,
            "pii_count":          pii_result.pii_count,
            "pii_summary":        self.redactor.get_pii_summary(pii_result),

            "processing_time_s":  elapsed,
            "demo_mode":          demo_mode,
            "cached":             False,

            "translation_note":   ""
        }

        if Config.ENABLE_CACHE and self.cache:
            self.cache.set(cache_key, result)

        return result

    @staticmethod
    def _cache_key(file_bytes: bytes, filename: str, lang_hint) -> str:
        h = hashlib.md5(file_bytes, usedforsecurity=False).hexdigest()
        return f"layer1:{filename}:{lang_hint}:{h[:12]}"

    @staticmethod
    def _error_result(filename: str, error: str) -> dict:
        return {
            "source_file":        filename,
            "success":            False,
            "error":              error,
            "original_text":      "",
            "pii_redacted_text":  "",
            "english_text":       "",
            "legal_context":      [],
            "retrieval_count":    0,
            "extraction_method":  "none",
            "page_count":         0,
            "char_count":         0,
            "detected_language":  "unknown",
            "language_name":      "Unknown",
            "lang_confidence":    0.0,
            "pii_found":          [],
            "pii_count":          0,
            "pii_summary":        "",
            "processing_time_s":  0,
            "demo_mode":          False,
            "cached":             False,
        }
    
    @staticmethod
    def adjust_risk(text):
        text = text.lower()

        if "penalty" in text or "fine" in text:
            return "High"
        if "terminate" in text or "termination" in text:
            return "High"
        if "must" in text or "shall" in text:
            return "Medium"

        return "Low"
        