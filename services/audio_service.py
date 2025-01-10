"""ElevenLabs audio generation service"""
import logging
import os
from typing import Dict, List, Optional, Union
import requests

logger = logging.getLogger(__name__)

class AudioService:
    def __init__(self):
        self.api_key = os.environ.get('ELEVENLABS_API_KEY')
        self.base_url = "https://api.elevenlabs.io/v1"
        self.default_voice = "Aria"  # Changed from Bella to Aria
        self.is_available = False
        self.available_voices = [] # Initialize available_voices
        self._check_availability()

    def _check_availability(self):
        """Check if the service is available by verifying the API key"""
        if not self.api_key:
            logger.warning("ELEVENLABS_API_KEY environment variable is not set")
            return

        try:
            # Add proper authorization header
            headers = {"xi-api-key": self.api_key}
            response = requests.get(
                f"{self.base_url}/voices",
                headers=headers
            )

            if response.status_code == 200:
                self.is_available = True
                logger.info("ElevenLabs service is available")
                # Store available voices for later use
                self.available_voices = [voice['name'] for voice in response.json().get("voices", [])]
                logger.info(f"Available voices: {', '.join(self.available_voices)}")

                # Verify default voice exists
                if self.default_voice not in self.available_voices:
                    self.default_voice = self.available_voices[0] if self.available_voices else None
                    logger.warning(f"Default voice not found, using {self.default_voice}")
            else:
                error_msg = response.json() if response.text else "No error details available"
                logger.warning(f"ElevenLabs service not available. Status code: {response.status_code}, Error: {error_msg}")
        except Exception as e:
            logger.error(f"Error checking ElevenLabs service: {str(e)}")

    def _get_voice_id(self, voice_name: str) -> str | None:
        """Get the voice ID for a given voice name"""
        if not voice_name:
            return None

        try:
            headers = {"xi-api-key": self.api_key}
            response = requests.get(f"{self.base_url}/voices", headers=headers)

            if response.status_code == 200:
                voices = response.json().get("voices", [])
                for voice in voices:
                    if voice["name"].lower() == voice_name.lower():
                        return voice["voice_id"]

                logger.warning(f"Voice '{voice_name}' not found in available voices")
                return None

            logger.error(f"Error fetching voices: {response.text}")
            return None

        except Exception as e:
            logger.error(f"Error fetching voices: {str(e)}")
            return None

    def generate_audio(self, text: str, voice_name: str | None = None) -> Dict[str, Union[bool, bytes, str]]:
        """
        Generate audio from text using ElevenLabs API
        Args:
            text: The text to convert to speech
            voice_name: Optional voice name to use (defaults to self.default_voice)
        Returns:
            Dictionary containing success status and either audio data or error message
        """
        if not self.is_available:
            return {
                "success": False, 
                "error": "ElevenLabs service is not available. Please check your API key."
            }

        if not text:
            return {"success": False, "error": "No text provided"}

        try:
            # Use provided voice or default
            voice_name = voice_name or self.default_voice

            # Verify voice exists
            if voice_name not in self.available_voices:
                logger.warning(f"Requested voice '{voice_name}' not found. Available voices: {', '.join(self.available_voices)}")
                voice_name = self.default_voice
                logger.info(f"Falling back to default voice: {voice_name}")

            # Get voice ID for the requested voice name
            voice_id = self._get_voice_id(voice_name)
            if not voice_id:
                return {"success": False, "error": f"Voice '{voice_name}' not found"}

            # Prepare the request
            url = f"{self.base_url}/text-to-speech/{voice_id}"
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.api_key
            }

            # Log the request being made
            logger.debug(f"Making request to ElevenLabs API: {url}")
            logger.debug(f"Using voice: {voice_name} (ID: {voice_id})")

            data = {
                "text": text,
                "model_id": "eleven_monolingual_v1",
                "voice_settings": {
                    "stability": 0.75,
                    "similarity_boost": 0.75
                }
            }

            # Make the API request with proper error handling
            response = requests.post(url, json=data, headers=headers)

            # Log response status
            logger.debug(f"ElevenLabs API response status: {response.status_code}")

            if response.status_code == 200:
                logger.info(f"Successfully generated audio with voice: {voice_name}")
                return {
                    "success": True,
                    "audio_data": response.content,
                    "content_type": response.headers.get('Content-Type', 'audio/mpeg')
                }
            else:
                error_msg = f"Error from ElevenLabs API: {response.text}"
                logger.error(error_msg)
                return {"success": False, "error": error_msg}

        except Exception as e:
            error_msg = f"Error generating audio: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    def get_available_voices(self) -> Dict[str, Union[bool, List[str], str]]:
        """Get a list of available voices"""
        if not self.is_available:
            return {
                "success": False,
                "error": "ElevenLabs service is not available",
                "voices": []
            }

        try:
            headers = {"xi-api-key": self.api_key}
            response = requests.get(f"{self.base_url}/voices", headers=headers)

            if response.status_code == 200:
                voices = response.json().get("voices", [])
                voice_list = [voice["name"] for voice in voices]
                return {"success": True, "voices": voice_list}

            return {
                "success": False,
                "error": f"Error fetching voices: {response.text}",
                "voices": []
            }

        except Exception as e:
            error_msg = f"Error fetching voices: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "voices": []
            }
    def generate_soundtrack(self, story_content: str, region: str, theme: str) -> Dict[str, Union[bool, bytes, str]]:
        """
        Generate a dynamic soundtrack based on story content and cultural context
        Args:
            story_content: The story text
            region: Cultural region (e.g., 'Asia', 'Africa')
            theme: Story theme (e.g., 'Traditions', 'Festivals')
        Returns:
            Dictionary containing success status and either audio data or error message
        """
        if not self.is_available:
            return {
                "success": False,
                "error": "ElevenLabs service is not available. Please check your API key."
            }

        try:
            # Determine appropriate musical style and elements
            style, mood = self._analyze_musical_context(story_content, region, theme)

            # Generate soundtrack prompt
            prompt = self._generate_soundtrack_prompt(style, mood)

            # Use a specialized voice for background music generation
            voice_name = "Antoni"  # Antoni voice works well for musical content

            # Generate the soundtrack using the audio generation method
            audio_result = self.generate_audio(prompt, voice_name)

            # Return the raw audio data if successful
            if audio_result["success"]:
                return {
                    "success": True,
                    "audio_data": audio_result["audio_data"],
                    "content_type": audio_result["content_type"]
                }
            else:
                return {
                    "success": False,
                    "error": audio_result.get("error", "Failed to generate soundtrack")
                }

        except Exception as e:
            logger.error(f"Error generating soundtrack: {str(e)}")
            return {"success": False, "error": str(e)}

    def _analyze_musical_context(self, content: str, region: str, theme: str) -> tuple[str, str]:
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