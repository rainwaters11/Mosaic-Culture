"""DALL-E image generation service"""
import os
from openai import OpenAI

class ImageService:
    def __init__(self):
        self.client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))

    def generate_image(self, prompt: str, size: str = "1024x1024") -> str:
        """
        Generate an image using DALL-E based on the prompt
        Returns the URL of the generated image
        """
        try:
            response = self.client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size=size,
                quality="standard",
                n=1,
            )
            return response.data[0].url
        except Exception as e:
            print(f"Error generating image: {str(e)}")
            return None
