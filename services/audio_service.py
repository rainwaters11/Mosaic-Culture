"""ElevenLabs audio generation service"""
import logging
import os
import requests
from typing import Optional, Dict, Tuple

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

    def generate_soundtrack(self, story_content: str, region: str, theme: str) -> Optional[bytes]:
        """
        Generate a dynamic soundtrack based on story content and cultural context
        Args:
            story_content: The story text
            region: Cultural region (e.g., 'Asia', 'Africa')
            theme: Story theme (e.g., 'Traditions', 'Festivals')
        Returns the audio data as bytes
        """
        try:
            # Determine appropriate musical style and elements
            style, mood = self._analyze_musical_context(story_content, region, theme)

            # Generate soundtrack prompt
            prompt = self._generate_soundtrack_prompt(style, mood)

            # Use a specialized voice for background music generation
            voice_name = "Antoni"  # Antoni voice works well for musical content

            # Generate the soundtrack
            soundtrack_data = self.generate_audio(prompt, voice_name)
            if soundtrack_data:
                logger.info("Successfully generated soundtrack")
                return soundtrack_data

            logger.error("Failed to generate soundtrack")
            return None

        except Exception as e:
            logger.error(f"Error generating soundtrack: {str(e)}")
            return None

    def _analyze_musical_context(self, content: str, region: str, theme: str) -> Tuple[str, str]:
        """Analyze story content to determine appropriate musical style and mood"""
        # Map regions to traditional musical styles
        regional_styles = {
            'Asia': ['traditional asian', 'zen meditation', 'oriental orchestra'],
            'Africa': ['african drums', 'tribal rhythm', 'savanna ambience'],
            'Europe': ['classical orchestra', 'folk ensemble', 'medieval ballad'],
            'Americas': ['indigenous flutes', 'latin rhythm', 'americana'],
            'Oceania': ['didgeridoo ambient', 'island drums', 'pacific sounds']
        }

        # Map themes to moods
        theme_moods = {
            'Traditions': 'ceremonial and dignified',
            'Festivals': 'celebratory and joyful',
            'Food': 'warm and inviting',
            'Art': 'creative and flowing',
            'Music': 'rhythmic and melodic',
            'Folklore': 'mysterious and enchanting'
        }

        # Select style based on region and theme
        style = regional_styles.get(region, ['world music'])[0]
        mood = theme_moods.get(theme, 'neutral and balanced')

        return style, mood

    def _generate_soundtrack_prompt(self, style: str, mood: str) -> str:
        """Generate a prompt for soundtrack creation"""
        return (
            f"<speak><break time='500ms'/>"
            f"<prosody rate='slow' pitch='+0st'>"
            f"♪ Creating {style} music that feels {mood}. "
            "Using traditional instruments and natural harmonies. "
            "The melody should be gentle and suitable for storytelling background. "
            "Starting with soft notes, building gradually, maintaining cultural authenticity. "
            "Including rhythmic patterns and melodic elements typical of the style. "
            "Keeping the volume moderate and the pace steady. ♪"
            "</prosody>"
            "<break time='500ms'/></speak>"
        )

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
        """Get a list of available voices"""
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