import os
import json
from tools.multimodal_tool import extract_pdf_content, transcribe_voice

# Use absolute paths for absolute certainty
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_PATH = os.path.join(BASE_DIR, "tools", "test_data", "Example_Medical_Report.pdf")
AUDIO_PATH = os.path.join(BASE_DIR, "tools", "test_data", "sample_voice.wav")

def test():
    print(f"Testing PDF: {PDF_PATH}")
    pdf_res = extract_pdf_content(PDF_PATH)
    print(f"PDF Result keys: {pdf_res.keys()}")
    if "error" in pdf_res:
        print(f"PDF ERROR: {pdf_res['error']}")
    else:
        print("PDF SUCCESS")
        print(f"Full Text sample: {pdf_res.get('full_text', '')[:100]}...")

    print(f"\nTesting Audio: {AUDIO_PATH}")
    audio_res = transcribe_voice(AUDIO_PATH)
    print(f"Audio Result keys: {audio_res.keys()}")
    if "error" in audio_res:
        print(f"AUDIO ERROR: {audio_res['error']}")
    else:
        print("AUDIO SUCCESS")
        print(f"Transcript sample: {audio_res.get('transcript', '')[:100]}...")

if __name__ == "__main__":
    test()
