"""ElevenLabs audio generation service"""
import logging
import os
import requests
from typing import Optional

logger = logging.getLogger(__name__)

class AudioService:
    def __init__(self):
        self.api_key = os.environ.get('ELEVENLABS_API_KEY')
        self.base_url = "https://api.elevenlabs.io/v1"

    def generate_audio(self, text: str, voice_name: str = "Bella") -> Optional[bytes]:
        """
        Generate audio from text using ElevenLabs API
        Args:
            text: The text to convert to speech
            voice_name: The name of the voice to use
        Returns the audio data as bytes
        """
        if not self.api_key:
            logger.error("ElevenLabs API key not found")
            return None

        try:
            logger.debug(f"Generating audio with voice: {voice_name}")

            # Get voice ID for the requested voice name
            voice_id = self._get_voice_id(voice_name)
            if not voice_id:
                logger.error(f"Voice '{voice_name}' not found")
                return None

            # Generate audio using the ElevenLabs API
            url = f"{self.base_url}/text-to-speech/{voice_id}"
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.api_key
            }
            data = {
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": 0.75,
                    "similarity_boost": 0.75
                }
            }

            response = requests.post(url, json=data, headers=headers)
            if response.status_code == 200:
                logger.info("Successfully generated audio")
                return response.content
            else:
                logger.error(f"Error from ElevenLabs API: {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error generating audio: {str(e)}")
            return None

    def _get_voice_id(self, voice_name: str) -> Optional[str]:
        """Get the voice ID for a given voice name"""
        try:
            url = f"{self.base_url}/voices"
            headers = {"xi-api-key": self.api_key}
            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                voices = response.json().get("voices", [])
                for voice in voices:
                    if voice["name"].lower() == voice_name.lower():
                        return voice["voice_id"]
            return None
        except Exception as e:
            logger.error(f"Error fetching voices: {str(e)}")
            return None

    def get_available_voices(self) -> list:
        """
        Get a list of available voices
        Returns a list of voice names
        """
        try:
            if not self.api_key:
                return ["Bella", "Antoni", "Arnold", "Adam", "Domi", "Elli", "Josh"]

            url = f"{self.base_url}/voices"
            headers = {"xi-api-key": self.api_key}
            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                voices = response.json().get("voices", [])
                return [voice["name"] for voice in voices]

            logger.error(f"Error from ElevenLabs API: {response.text}")
            return ["Bella", "Antoni", "Arnold", "Adam", "Domi", "Elli", "Josh"]

        except Exception as e:
            logger.error(f"Error fetching voices: {str(e)}")
            return ["Bella", "Antoni", "Arnold", "Adam", "Domi", "Elli", "Josh"]