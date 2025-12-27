"""

1. Create a new folder. 
2. Save TTS over there. 


"""

import os
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs.play import play, save
from pathlib import Path

import time

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


if not os.path.exists(os.path.join(PROJECT_ROOT, 'audio')):
    os.mkdir(os.path.join(PROJECT_ROOT, 'audio'))

elevenlabs = ElevenLabs(
  api_key=os.getenv("ELEVENLABS_API_KEY"),
)

audio = elevenlabs.text_to_dialogue.convert(
    inputs=[
        {
            "text": "Welcome everyone, we’ve got a fascinating rapid clash unfolding here between the steady, patient self_service. ",
            "voice_id": "PdJQAOWyIMAQwD7gQcSc",
        }
    ]
)

# play(audio, use_ffmpeg = False)



def get_filename():
    """
    Sample return text: 'Sat_Dec_27_002210_2025'
    """

    current_time = time.asctime()
    
    return current_time.replace(' ', '_').replace(':', '')



file_name = get_filename()

save(audio, os.path.join(PROJECT_ROOT,'audio' , file_name + ".mp3"))
