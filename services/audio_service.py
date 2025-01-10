"""ElevenLabs audio generation service"""
import os
from elevenlabs import generate, set_api_key

class AudioService:
    def __init__(self):
        self.api_key = os.environ.get('ELEVENLABS_API_KEY')
        if self.api_key:
            set_api_key(self.api_key)

    def generate_audio(self, text: str, voice_name: str = "Bella") -> bytes:
        """
        Generate audio from text using ElevenLabs API
        Returns audio bytes that can be saved to a file
        """
        try:
            if not self.api_key:
                raise ValueError("ElevenLabs API key not set")

            # Generate audio using the specified voice name
            audio = generate(
                text=text,
                voice=voice_name,
            )

            return audio
        except Exception as e:
            print(f"Error generating audio: {str(e)}")
            return None