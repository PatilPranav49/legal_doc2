from pipeline import LegalDocPipeline

pipeline = LegalDocPipeline()

def extract_using_pipeline(file_bytes, filename):
    try:
        result = pipeline.process_bytes(
            file_bytes,
            filename,
            language_hint=None
        )

        return result   # 🔥 DIRECT RETURN

    except Exception as e:
        return {
            "error": str(e)
        }