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
        # Base URL for RunwayML API updated with correct endpoint
        self.api_url = "https://api.runwayml.com/v1"
        self.is_available = bool(self.api_key)

        if not self.is_available:
            logger.error("RUNWAYML_API_KEY environment variable is not set")
        else:
            logger.info("Video service initialized successfully")

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

            # Prepare the request payload according to RunwayML's format
            payload = {
                "prompt": prompt,
                "mode": "text-to-video",
                "parameters": {
                    "duration": duration,
                    "fps": 30,
                    "guidance_scale": 7.5,
                    "steps": 50,
                    "seed": -1  # Random seed
                }
            }

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }

            # Make the API request to inference endpoint
            endpoint = f"{self.api_url}/inference"
            logger.info(f"Requesting video generation for story: {title}")
            logger.debug(f"Using endpoint: {endpoint}")

            response = requests.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=30  # Add timeout for the request
            )

            # Log the response status and content for debugging
            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response content: {response.text[:200]}...")  # Log first 200 chars

            if response.status_code == 200:
                video_data = response.json()
                if 'output' in video_data and 'video_url' in video_data['output']:
                    logger.info(f"Successfully generated video for story: {title}")
                    return {
                        "success": True,
                        "video_url": video_data['output']['video_url'],
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
                error_msg = "Invalid API key or authentication error"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg
                }
            elif response.status_code == 429:
                error_msg = "Rate limit exceeded"
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