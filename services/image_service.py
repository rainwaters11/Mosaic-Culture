"""DALL-E image generation service"""
import logging
import os
import time
from typing import Optional
from openai import OpenAI

logger = logging.getLogger(__name__)

class ImageService:
    def __init__(self):
        self.client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
        self.max_retries = 3
        self.retry_delay = 2  # seconds

    def generate_image(self, prompt: str, size: str = "1024x1024", style: str = "vivid") -> Optional[str]:
        """
        Generate an image using DALL-E based on the prompt
        Args:
            prompt: The description of the image to generate
            size: Image size (256x256, 512x512, or 1024x1024)
            style: Image style ('vivid' or 'natural')
        Returns the URL of the generated image
        """
        enhanced_prompt = self._enhance_prompt(prompt)
        retries = 0

        while retries < self.max_retries:
            try:
                logger.debug(f"Attempting to generate image (attempt {retries + 1}/{self.max_retries})")
                logger.debug(f"Using prompt: {enhanced_prompt}")

                response = self.client.images.generate(
                    model="dall-e-3",
                    prompt=enhanced_prompt,
                    size=size,
                    quality="hd",
                    style=style,
                    n=1,
                )

                if response.data:
                    logger.info("Successfully generated image")
                    return response.data[0].url

                logger.error("No image data in response")
                return None

            except Exception as e:
                logger.error(f"Error generating image (attempt {retries + 1}/{self.max_retries}): {str(e)}")
                retries += 1
                if retries < self.max_retries:
                    time.sleep(self.retry_delay)
                    continue
                return None

    def _enhance_prompt(self, prompt: str) -> str:
        """
        Enhance the user's prompt to generate better images
        """
        # Add details to make the image more vivid and culturally appropriate
        enhanced = (
            f"{prompt} "
            "Create a high-quality, detailed illustration with cultural sensitivity "
            "and authentic representation. Use rich colors and meaningful symbols "
            "relevant to the story's context. Focus on artistic composition "
            "and cultural accuracy. Ensure the style is photorealistic and "
            "maintains cultural authenticity."
        )
        return enhanced[:1000]  # DALL-E has a prompt length limit