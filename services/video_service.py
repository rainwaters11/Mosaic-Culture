"""Video generation service using RunwayML"""
import os
import logging
from typing import Optional, Dict, Union
import requests

logger = logging.getLogger(__name__)

class VideoService:
    def __init__(self):
        """Initialize video generation service"""
        self.api_key = os.environ.get('RUNWAYML_API_KEY')
        # Base URL for RunwayML API
        self.api_url = "https://api.runwayml.com"
        self.is_available = bool(self.api_key)

        if not self.is_available:
            logger.error("RUNWAYML_API_KEY environment variable is not set")
        else:
            # Validate API key format
            if not self._validate_api_key():
                logger.error("Invalid RunwayML API key format")
                self.is_available = False
            else:
                logger.info("Video service initialized successfully")

    def _validate_api_key(self) -> bool:
        """Validate the API key format"""
        if not self.api_key:
            return False
        # RunwayML API keys are typically non-empty strings
        return len(self.api_key.strip()) > 0

    def generate_video(self, title: str, description: str, duration: int = 15) -> Dict[str, Union[bool, str]]:
        """
        Generate a video based on story content using RunwayML
        Args:
            title: The title of the story
            description: Story content or description for video generation
            duration: Duration of the video in seconds (default: 15)
        Returns:
            Dictionary containing success status and either video URL or error message
        """
        if not self.is_available:
            return {
                "success": False,
                "error": "Video service is not properly configured"
            }

        try:
            # Format prompt for better video generation
            prompt = f"{title}\n\nDescription: {description}"

            # Prepare the request payload for RunwayML Gen-2 model
            payload = {
                "prompt": prompt,
                "negative_prompt": "",
                "num_frames": duration * 24,  # 24 fps
                "num_steps": 50,
                "guidance_scale": 17.5,
                "width": 1024,
                "height": 576
            }

            headers = {
                "Authorization": f"Key {self.api_key}",  # Updated auth header format
                "Content-Type": "application/json",
                "Accept": "application/json"
            }

            # Make the API request to Gen-2 video generation endpoint
            endpoint = f"{self.api_url}/v1/generations"
            logger.info(f"Requesting video generation for story: {title}")
            logger.debug(f"Using endpoint: {endpoint}")
            logger.debug(f"Request payload: {payload}")

            response = requests.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=120  # Increased timeout for video generation
            )

            # Log the response status and content for debugging
            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response content: {response.text[:200]}...")  # Log first 200 chars

            if response.status_code == 200:
                video_data = response.json()
                if 'artifacts' in video_data and len(video_data['artifacts']) > 0:
                    logger.info(f"Successfully generated video for story: {title}")
                    return {
                        "success": True,
                        "video_url": video_data['artifacts'][0]['uri'],
                        "content_type": "video/mp4"
                    }
                else:
                    error_msg = "Invalid response format from RunwayML API"
                    logger.error(f"{error_msg}. Response: {video_data}")
                    return {
                        "success": False,
                        "error": error_msg
                    }
            elif response.status_code == 401:
                error_msg = "Invalid API key or authentication error. Please verify your RunwayML API key."
                logger.error(f"{error_msg} Response: {response.text}")
                return {
                    "success": False,
                    "error": error_msg
                }
            elif response.status_code == 429:
                error_msg = "Rate limit exceeded. Please try again later."
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