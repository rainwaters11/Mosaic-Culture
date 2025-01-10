"""Cultural context analysis service using OpenAI API"""
import logging
import os
from typing import Dict, List, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)

class CulturalContextService:
    def __init__(self):
        self.client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))

    def analyze_context(self, content: str, region: str, theme: str) -> Dict[str, any]:
        """
        Analyze cultural context and provide detailed insights
        Args:
            content: The story content to analyze
            region: The cultural region
            theme: The story theme
        Returns:
            Dictionary containing cultural analysis and insights
        """
        try:
            logger.debug("Starting cultural context analysis")
            system_prompt = (
                "You are a cultural anthropologist and historian specializing in "
                "global cultural traditions and practices. Analyze the following content "
                "and provide detailed cultural insights about:"
                "\n1. Historical Context"
                "\n2. Cultural Significance"
                "\n3. Traditional Elements"
                "\n4. Modern Relevance"
                "\n5. Related Cultural Practices"
                "\nProvide academic yet accessible insights."
            )

            user_prompt = self._create_analysis_prompt(content, region, theme)
            
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )

            analysis = response.choices[0].message.content
            logger.info("Completed cultural context analysis")
            return {
                "success": True,
                "analysis": analysis
            }

        except Exception as e:
            logger.error(f"Error in cultural context analysis: {str(e)}")
            return {
                "success": False,
                "error": "Failed to complete cultural analysis"
            }

    def _create_analysis_prompt(self, content: str, region: str, theme: str) -> str:
        """Create a detailed prompt for cultural analysis"""
        return (
            f"Analyze this {theme.lower()} story from {region} with cultural context:\n\n"
            f"{content}\n\n"
            "Provide analysis in JSON format with the following structure:\n"
            "{\n"
            '  "historical_context": {\n'
            '    "period": "relevant historical period",\n'
            '    "significance": "historical significance",\n'
            '    "key_events": ["related historical events"]\n'
            "  },\n"
            '  "cultural_elements": {\n'
            '    "traditions": ["relevant traditions"],\n'
            '    "symbols": ["cultural symbols"],\n'
            '    "practices": ["related practices"]\n'
            "  },\n"
            '  "modern_relevance": {\n'
            '    "contemporary_significance": "current importance",\n'
            '    "preservation_status": "how it\'s maintained today",\n'
            '    "challenges": ["challenges in preserving this culture"]\n'
            "  },\n"
            '  "related_practices": [\n'
            '    {\n'
            '      "name": "practice name",\n'
            '      "description": "brief description",\n'
            '      "region": "where it\'s practiced"\n'
            '    }\n'
            "  ],\n"
            '  "learn_more": [\n'
            '    "suggested topics for further learning"\n'
            "  ]\n"
            "}"
        )

    def get_learning_resources(self, content: str, region: str) -> List[Dict[str, str]]:
        """
        Get suggested learning resources about the cultural elements
        Returns list of relevant topics and resources
        """
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a cultural education specialist. Suggest learning "
                            "resources about cultural elements mentioned in the content."
                        )
                    },
                    {
                        "role": "user",
                        "content": f"Suggest learning resources about cultural elements in this content from {region}:\n{content}"
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )

            resources = response.choices[0].message.content
            return {
                "success": True,
                "resources": resources
            }

        except Exception as e:
            logger.error(f"Error getting learning resources: {str(e)}")
            return {
                "success": False,
                "error": "Failed to get learning resources"
            }
