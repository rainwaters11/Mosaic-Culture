"""Story generation service using OpenAI API"""
import logging
import os
from typing import Optional, Dict
from openai import OpenAI

logger = logging.getLogger(__name__)

class StoryService:
    def __init__(self):
        self.client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))

    def generate_story(self, title: str, theme: str, region: str) -> Optional[Dict[str, str]]:
        """
        Generate a cultural story based on user input using OpenAI
        Returns a dictionary containing the generated story and image prompt
        """
        try:
            # Craft a detailed prompt for story generation
            prompt = (
                f"Create an engaging cultural story about {title} "
                f"themed around {theme} from the {region} region. "
                "The story should be respectful, authentic, and culturally sensitive. "
                "Include traditional elements, customs, or beliefs relevant to the region. "
                "The story should be between 300-500 words."
            )

            # Generate the story using GPT
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a cultural storyteller specializing in authentic, respectful narratives from different regions."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )

            story_content = response.choices[0].message.content

            # Generate an image prompt based on the story
            image_prompt_response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Create a detailed visual prompt for DALL-E to generate an illustration for this story."},
                    {"role": "user", "content": f"Create a vivid, culturally appropriate image prompt for this story: {story_content[:200]}..."}
                ],
                max_tokens=100,
                temperature=0.6
            )

            image_prompt = image_prompt_response.choices[0].message.content

            return {
                "content": story_content,
                "image_prompt": image_prompt
            }

        except Exception as e:
            logger.error(f"Error generating story: {str(e)}")
            return None
