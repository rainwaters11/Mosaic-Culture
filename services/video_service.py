"""Video generation service"""
import os
import logging
from typing import Optional, Dict, Union
import requests

logger = logging.getLogger(__name__)

class VideoService:
    def __init__(self):
        """Initialize video generation service"""
        self.api_key = os.environ.get('RUNWAYML_API_KEY')
        self.api_url = "https://api.runwayml.com/v1/videos/generate"  # Example API endpoint
        self.is_available = bool(self.api_key)
        
        if not self.is_available:
            logger.error("RUNWAYML_API_KEY environment variable is not set")
        else:
            logger.info("Video service initialized successfully")

    def generate_video(self, title: str, description: str, duration: int = 15) -> Dict[str, Union[bool, str]]:
        """
        Generate a video based on story content
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
            # Prepare the request payload
            payload = {
                "title": title,
                "description": description,
                "duration": duration
            }
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            # Make the API request
            logger.info(f"Requesting video generation for story: {title}")
            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers
            )

            if response.status_code == 200:
                video_data = response.json()
                logger.info(f"Successfully generated video for story: {title}")
                return {
                    "success": True,
                    "video_url": video_data["video_url"],
                    "content_type": "video/mp4"
                }
            else:
                error_msg = f"Failed to generate video: {response.text}"
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
