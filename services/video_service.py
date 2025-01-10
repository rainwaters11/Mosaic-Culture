"""Video generation service using RunwayML"""
import os
import logging
import time
from typing import Optional, Dict, Union
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

class VideoService:
    def __init__(self):
        """Initialize video generation service"""
        self.api_key = os.environ.get('RUNWAYML_API_KEY')
        self.api_url = "https://api.runway.ml/v1"  # Updated to use api.runway.ml
        self.is_available = bool(self.api_key)

        if not self.is_available:
            logger.error("RUNWAYML_API_KEY environment variable is not set")
            return

        # Configure session with retries
        self.session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504]
        )
        self.session.mount('https://', HTTPAdapter(max_retries=retries))

        try:
            # Validate API key using a test request
            headers = self._get_headers()
            logger.info("Validating RunwayML API key...")

            # Test endpoint that doesn't consume credits
            response = self.session.get(
                f"{self.api_url}/user",
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                logger.info("Video service initialized successfully")
            elif response.status_code == 401:
                logger.error("Invalid RunwayML API key. Please check your credentials.")
                self.is_available = False
            else:
                logger.error(f"Failed to validate RunwayML API key: {response.text}")
                self.is_available = False

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to initialize RunwayML: {str(e)}")
            self.is_available = False

    def _get_headers(self) -> Dict[str, str]:
        """Get headers with proper authentication"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def _validate_request_params(self, title: str, description: str, duration: int) -> Optional[str]:
        """Validate request parameters"""
        if not title or not description:
            return "Title and description are required"
        if duration < 5 or duration > 60:
            return "Duration must be between 5 and 60 seconds"
        return None

    def generate_video(self, title: str, description: str, duration: int = 15) -> Dict[str, Union[bool, str]]:
        """Generate a video based on story content"""
        if not self.is_available:
            return {
                "success": False,
                "error": "Video service is not properly configured. Please check your RunwayML API key."
            }

        # Validate request parameters
        validation_error = self._validate_request_params(title, description, duration)
        if validation_error:
            return {
                "success": False,
                "error": validation_error
            }

        try:
            # Format prompt for better video generation
            prompt = f"{title}\n\nDescription: {description}"

            # Prepare the request payload
            payload = {
                "input": {
                    "prompt": prompt,
                    "num_frames": duration * 24,  # Convert duration to frames
                    "width": 1024,
                    "height": 576,
                    "fps": 24,
                    "guidance_scale": 7.5,
                    "num_inference_steps": 50
                }
            }

            headers = self._get_headers()

            # Make the API request
            logger.info(f"Requesting video generation for story: {title}")
            response = self.session.post(
                f"{self.api_url}/inference",
                json=payload,
                headers=headers,
                timeout=300  # 5 minutes timeout for video generation
            )

            # Log the response for debugging
            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response content: {response.text[:200]}...")

            if response.status_code == 200:
                result = response.json()
                if 'output' in result and 'url' in result['output']:
                    logger.info(f"Successfully generated video for story: {title}")
                    return {
                        "success": True,
                        "video_url": result['output']['url']
                    }
                else:
                    error_msg = "Invalid response format from RunwayML API"
                    logger.error(f"{error_msg}. Response: {result}")
                    return {
                        "success": False,
                        "error": error_msg
                    }
            elif response.status_code == 401:
                error_msg = "Invalid API key or authentication error"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg
                }
            else:
                error_msg = f"Failed to generate video: {response.text}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg
                }

        except requests.exceptions.RequestException as e:
            error_msg = f"Network error while generating video: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
        except Exception as e:
            error_msg = f"Error generating video: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }