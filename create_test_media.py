import os
import sys

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "reportlab", "gtts"])
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

c = canvas.Canvas('test_referral.pdf', pagesize=letter)
c.drawString(100, 750, 'Patient: John Test')
c.drawString(100, 730, 'Diagnosis: Deep vein thrombosis (I82.409)')
c.drawString(100, 710, 'Procedure requested: 99213 - Office visit')
c.drawString(100, 690, 'Referring physician: Dr. Smith')
c.save()
print('created test_referral.pdf')

try:
    from gtts import gTTS
    tts = gTTS(text="Patient John Test has deep vein thrombosis. I am requesting a venous duplex scan, CPT code 93971.", lang='en')
    tts.save("test_audio.mp3")
    print("created test_audio.mp3")
except Exception as e:
    print(f"Failed to create audio: {e}")
