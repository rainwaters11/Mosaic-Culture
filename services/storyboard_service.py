import os
import logging
import openai
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class StoryboardService:
    def __init__(self):
        self.client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        if not self.client.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")

    def generate_scene_descriptions(self, story_content: str, num_scenes: int = 5) -> List[str]:
        """Generate scene descriptions for storyboard panels"""
        try:
            prompt = f"""Break down this story into {num_scenes} key visual scenes. 
            For each scene, provide a detailed description that could be used to generate an illustration:

            Story: {story_content}

            Format: Return only the scene descriptions, one per line."""

            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a storyboard artist specializing in cultural storytelling."},
                    {"role": "user", "content": prompt}
                ]
            )

            scenes = response.choices[0].message.content.strip().split('\n')
            return [scene.strip() for scene in scenes if scene.strip()]

        except Exception as e:
            logger.error(f"Error generating scene descriptions: {str(e)}")
            return []

    def generate_storyboard_images(self, scene_descriptions: List[str]) -> List[Dict[str, str]]:
        """Generate images for each scene description using DALL-E"""
        storyboard_panels = []

        try:
            for scene in scene_descriptions:
                response = self.client.images.generate(
                    prompt=f"Create a storyboard panel illustration for this scene: {scene}",
                    n=1,
                    size="512x512"
                )

                storyboard_panels.append({
                    "description": scene,
                    "image_url": response.data[0].url
                })

            return storyboard_panels

        except Exception as e:
            logger.error(f"Error generating storyboard images: {str(e)}")
            return []

    def create_storyboard(self, story_content: str, num_scenes: int = 5) -> Optional[List[Dict[str, str]]]:
        """Create a complete storyboard with scenes and illustrations"""
        try:
            # Generate scene descriptions
            scene_descriptions = self.generate_scene_descriptions(story_content, num_scenes)
            if not scene_descriptions:
                return None

            # Generate images for each scene
            storyboard = self.generate_storyboard_images(scene_descriptions)
            if not storyboard:
                return None

            return storyboard

        except Exception as e:
            logger.error(f"Error creating storyboard: {str(e)}")
            return None