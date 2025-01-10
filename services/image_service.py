"""DALL-E image generation service"""
import logging
import os
import time
from typing import Optional, Dict, Union
from openai import OpenAI

logger = logging.getLogger(__name__)

class ImageService:
    def __init__(self):
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            logger.error("OPENAI_API_KEY environment variable is not set")
            raise ValueError("OPENAI_API_KEY environment variable is not set")

        self.client = OpenAI(api_key=api_key)
        self.max_retries = 3
        self.retry_delay = 2  # seconds
        self.base_delay = 2  # Base delay for exponential backoff

    def generate_image(self, prompt: str, size: str = "1024x1024", style: str = "vivid") -> Dict[str, Union[bool, str]]:
        """
        Generate an image using DALL-E based on the prompt
        Args:
            prompt: The description of the image to generate
            size: Image size (256x256, 512x512, or 1024x1024)
            style: Image style ('vivid' or 'natural')
        Returns a dictionary with success status and either image URL or error message
        """
        enhanced_prompt = self._enhance_prompt(prompt)
        retries = 0
        last_error = None

        while retries < self.max_retries:
            try:
                logger.debug(f"Attempting to generate image (attempt {retries + 1}/{self.max_retries})")
                logger.debug(f"Using prompt: {enhanced_prompt}")

                response = self.client.images.generate(
                    model="dall-e-3",
                    prompt=enhanced_prompt,
                    size=size,
                    quality="standard",  # Using standard quality for faster response
                    style=style,
                    n=1,
                )

                if response.data:
                    logger.info("Successfully generated image")
                    return {
                        "success": True,
                        "url": response.data[0].url
                    }

                logger.error("No image data in response")
                return {
                    "success": False,
                    "error": "No image data returned from the API"
                }

            except Exception as e:
                last_error = str(e)
                logger.error(f"Error generating image (attempt {retries + 1}/{self.max_retries}): {last_error}")
                retries += 1

                if retries < self.max_retries:
                    # Exponential backoff with jitter
                    delay = min(300, self.base_delay * (2 ** retries) + (time.time() % 1))
                    logger.info(f"Retrying in {delay:.2f} seconds...")
                    time.sleep(delay)
                    continue

        return {
            "success": False,
            "error": f"Failed to generate image after {self.max_retries} attempts. Last error: {last_error}"
        }

    def _enhance_prompt(self, prompt: str) -> str:
        """
        Enhance the user's prompt to generate better images
        """
        # Create a more focused and detailed prompt
        enhanced = (
            f"{prompt} "
            "Create this scene with attention to detail and cultural authenticity. "
            "Use rich, vibrant colors that reflect the story's atmosphere. "
            "Maintain photorealistic quality while emphasizing artistic composition. "
            "Include culturally appropriate elements and symbolism."
        )
        return enhanced[:1000]  # DALL-E has a prompt length limit