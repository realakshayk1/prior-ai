import pdfplumber
import os
from faster_whisper import WhisperModel

def extract_pdf_content(file_path: str) -> dict:
    """
    Extracts text content from a clinical PDF file using pdfplumber.
    Returns a dictionary with pages, full_text, and word_count.
    """
    try:
        if not os.path.exists(file_path):
            return {"error": f"File not found: {file_path}"}
            
        pages_content = []
        full_text = ""
        
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                pages_content.append({"page": i + 1, "text": text})
                full_text += text + "\n"
        
        return {
            "pages": pages_content,
            "full_text": full_text.strip(),
            "word_count": len(full_text.split())
        }
    except Exception as e:
        return {"error": f"Failed to extract PDF: {str(e)}"}

def transcribe_voice(file_path: str, model_size: str = "base.en") -> dict:
    """
    Transcribes a voice note using faster-whisper (local).
    Returns a dictionary with transcript, duration, and language.
    """
    try:
        if not os.path.exists(file_path):
            return {"error": f"File not found: {file_path}"}
            
        # Run local transcription
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        
        segments, info = model.transcribe(file_path, beam_size=5)
        
        transcript = ""
        for segment in segments:
            transcript += segment.text + " "
            
        return {
            "transcript": transcript.strip(),
            "duration_seconds": info.duration,
            "language": info.language
        }
    except Exception as e:
        return {"error": f"Failed to transcribe audio: {str(e)}"}

if __name__ == "__main__":
    import sys
    import json
    
    if len(sys.argv) < 2:
        print("Usage: python multimodal_tool.py <pdf_or_wav_path>")
        sys.exit(1)
        
    path = sys.argv[1]
    if path.endswith(".pdf"):
        print(f"Extracting PDF: {path}")
        result = extract_pdf_content(path)
    elif path.endswith((".wav", ".mp3")):
        print(f"Transcribing Audio: {path}")
        result = transcribe_voice(path)
    else:
        print("Unsupported file type.")
        sys.exit(1)
        
    print(json.dumps(result, indent=2))
