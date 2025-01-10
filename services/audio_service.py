"""Google Cloud Text-to-Speech audio generation service"""
import logging
import os
from typing import Dict, Union
from google.cloud import texttospeech

logger = logging.getLogger(__name__)

class AudioService:
    def __init__(self):
        """Initialize the audio service with proper error handling"""
        self.project_id = os.environ.get('GOOGLE_CLOUD_PROJECT')
        self.credentials_json = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
        self.is_available = False
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize the Google Cloud Text-to-Speech client with better error handling"""
        try:
            if not self.project_id:
                logger.warning("GOOGLE_CLOUD_PROJECT environment variable is not set")
                return

            if not self.credentials_json:
                logger.warning("GOOGLE_APPLICATION_CREDENTIALS environment variable is not set")
                return

            # Initialize the client - this will use the GOOGLE_APPLICATION_CREDENTIALS env var
            self.client = texttospeech.TextToSpeechClient()

            # Test connection by listing voices
            self.client.list_voices()
            self.is_available = True
            logger.info("Google Cloud Text-to-Speech service initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Google Cloud Text-to-Speech: {str(e)}")
            self.is_available = False

    def generate_audio(self, text: str, voice_name: str = None) -> Dict[str, Union[bool, bytes, str]]:
        """Generate audio from text using Google Cloud Text-to-Speech"""
        if not self.is_available:
            return {
                "success": False,
                "error": "Google Cloud Text-to-Speech service is not available. Please ensure GOOGLE_CLOUD_PROJECT and GOOGLE_APPLICATION_CREDENTIALS are properly set."
            }

        if not text:
            return {"success": False, "error": "No text provided"}

        try:
            # Configure the synthesis input
            synthesis_input = texttospeech.SynthesisInput(text=text)

            # Build the voice request
            voice = texttospeech.VoiceSelectionParams(
                language_code="en-US",
                ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
            )

            # Select the type of audio file
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3
            )

            # Perform the text-to-speech request
            response = self.client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )

            return {
                "success": True,
                "audio_data": response.audio_content,
                "content_type": "audio/mpeg"
            }

        except Exception as e:
            error_msg = f"Error generating audio: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    def generate_soundtrack(self, story_content: str, region: str, theme: str) -> Dict[str, Union[bool, bytes, str]]:
        """Generate a dynamic soundtrack based on story content and context"""
        if not self.is_available:
            return {
                "success": False,
                "error": "Google Cloud Text-to-Speech service is not available"
            }

        try:
            # Generate a text prompt for soundtrack generation
            prompt = self._generate_soundtrack_prompt(region, theme)

            # Use different voice parameters for soundtrack generation
            synthesis_input = texttospeech.SynthesisInput(ssml=prompt)

            voice = texttospeech.VoiceSelectionParams(
                language_code="en-US",
                name="en-US-Neural2-D",  # Using a deep voice for soundtrack
                ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
            )

            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                effects_profile_id=["large-home-entertainment-class-device"],
                speaking_rate=0.85,  # Slower rate for soundtrack
                pitch=-2.0  # Lower pitch for ambient sound
            )

            response = self.client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )

            return {
                "success": True,
                "audio_data": response.audio_content,
                "content_type": "audio/mpeg"
            }

        except Exception as e:
            error_msg = f"Error generating soundtrack: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    def _generate_soundtrack_prompt(self, region: str, theme: str) -> str:
        """Generate an SSML prompt for soundtrack creation"""
        return (
            '<speak>'
            '<break time="500ms"/>'
            f'<prosody rate="slow" pitch="-2st">'
            f'♪ Creating ambient music for {region} {theme}. '
            'Gentle atmospheric sounds and harmonies. '
            'Soft melodic elements for storytelling background.'
            '</prosody>'
            '<break time="500ms"/>'
            '</speak>'
        )