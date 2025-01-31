"""Story generation service using OpenAI API"""
import logging
import os
from typing import Optional, Dict
from openai import OpenAI
from services.sensitivity_service import SensitivityService

logger = logging.getLogger(__name__)

class StoryService:
    def __init__(self):
        self.client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
        self.sensitivity_service = SensitivityService()

    def generate_story(self, title: str, theme: str, region: str) -> Optional[Dict[str, str]]:
        """
        Generate a cultural story based on user input using OpenAI
        Returns a dictionary containing the generated story and image prompt
        """
        try:
            # Craft a detailed system prompt for cultural storytelling
            system_prompt = (
                "You are an expert cultural storyteller with deep knowledge of global traditions, "
                "customs, and narratives. Your stories are:"
                "\n- Culturally authentic and sensitive"
                "\n- Rich in traditional elements and symbolism"
                "\n- Engaging and emotionally resonant"
                "\n- Educational about cultural practices"
                "\n- Respectful of cultural heritage"
            )

            # Create a structured user prompt for story generation
            story_prompt = self._create_story_prompt(title, theme, region)

            # Generate the main story using GPT
            story_response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": story_prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )

            story_content = story_response.choices[0].message.content

            # Check for cultural sensitivity
            sensitivity_result = self.sensitivity_service.check_content(
                story_content,
                {"theme": theme, "region": region, "title": title}
            )

            if sensitivity_result.get("has_issues"):
                logger.warning("Cultural sensitivity issues detected")
                # If there are issues, try to generate a more culturally appropriate version
                improved_story = self._regenerate_with_sensitivity_feedback(
                    story_content, sensitivity_result, title, theme, region
                )
                if improved_story:
                    story_content = improved_story

            # Generate prompts for other media
            image_prompt = self._generate_image_prompt(story_content, theme, region)
            audio_prompt = self._generate_audio_prompt(story_content)

            return {
                "content": story_content,
                "image_prompt": image_prompt,
                "audio_prompt": audio_prompt,
                "sensitivity_analysis": sensitivity_result.get("analysis")
            }

        except Exception as e:
            logger.error(f"Error generating story: {str(e)}")
            return None

    def _regenerate_with_sensitivity_feedback(
        self, original_content: str, sensitivity_result: Dict, 
        title: str, theme: str, region: str
    ) -> Optional[str]:
        """Attempt to regenerate story with sensitivity feedback"""
        try:
            import json
            analysis = json.loads(sensitivity_result["analysis"])

            feedback_prompt = (
                "The previous story had some cultural sensitivity concerns:\n"
                f"{analysis.get('improvement_suggestions', '')}\n\n"
                "Please generate a new version that addresses these issues while "
                "maintaining the core narrative elements."
            )

            response = self.client.chat.completions.create(
                model="gpt-4",  # Using GPT-4 for better cultural awareness
                messages=[
                    {"role": "system", "content": "You are a cultural sensitivity expert and storyteller."},
                    {"role": "user", "content": original_content},
                    {"role": "assistant", "content": feedback_prompt}
                ],
                max_tokens=1000,
                temperature=0.6
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Error regenerating story: {str(e)}")
            return None

    def _create_story_prompt(self, title: str, theme: str, region: str) -> str:
        """Create a detailed prompt for story generation"""
        theme_prompts = {
            "Traditions": "Focus on age-old customs, rituals, and their significance.",
            "Festivals": "Describe the vibrant celebrations, their origins, and community involvement.",
            "Food": "Explore culinary traditions, family recipes, and the stories behind them.",
            "Art": "Detail the artistic expressions, craftsmanship, and their cultural meaning.",
            "Music": "Weave in traditional instruments, songs, and their role in society.",
            "Folklore": "Share myths, legends, and their lessons for modern times."
        }

        region_context = {
            "Asia": "rich in ancient wisdom and philosophical traditions",
            "Africa": "vibrant with oral traditions and community celebrations",
            "Europe": "steeped in historical folklore and seasonal festivities",
            "Americas": "diverse with indigenous wisdom and cultural fusion",
            "Oceania": "connected to nature and maritime traditions"
        }

        base_prompt = (
            f"Create an engaging cultural story about '{title}' "
            f"set in {region}, {region_context.get(region, '')}. "
            f"Theme focus: {theme_prompts.get(theme, theme)}.\n\n"
            "Requirements:\n"
            "1. Begin with a strong cultural hook\n"
            "2. Include authentic cultural elements and traditions\n"
            "3. Weave in local customs and beliefs naturally\n"
            "4. Create emotional resonance through cultural details\n"
            "5. Conclude with cultural wisdom or learning\n"
            "Length: 300-500 words."
        )

        return base_prompt

    def _generate_image_prompt(self, story: str, theme: str, region: str) -> str:
        """Generate an optimized image prompt based on the story"""
        try:
            prompt_response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Create detailed, culturally accurate image prompts for DALL-E. "
                            "Focus on visual elements, colors, and cultural symbols."
                        )
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Create a vivid, culturally appropriate image prompt for this story from {region} "
                            f"about {theme}:\n{story[:200]}..."
                        )
                    }
                ],
                max_tokens=100,
                temperature=0.6
            )

            return prompt_response.choices[0].message.content

        except Exception as e:
            logger.error(f"Error generating image prompt: {str(e)}")
            return "Error generating image prompt"

    def _generate_audio_prompt(self, story: str) -> str:
        """Generate an enhanced prompt for audio narration"""
        try:
            prompt_response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Create voice direction prompts for audio narration. "
                            "Focus on emotional tone, pacing, and cultural pronunciation."
                        )
                    },
                    {
                        "role": "user",
                        "content": f"Create narration directions for this story:\n{story[:200]}..."
                    }
                ],
                max_tokens=100,
                temperature=0.6
            )

            return prompt_response.choices[0].message.content

        except Exception as e:
            logger.error(f"Error generating audio prompt: {str(e)}")
            return "Error generating audio prompt"