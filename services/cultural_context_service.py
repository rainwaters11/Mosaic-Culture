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
            "Format your analysis covering these aspects:\n"
            "1. Historical Context:\n"
            "   - Time period relevance\n"
            "   - Historical significance\n"
            "   - Key historical events\n\n"
            "2. Cultural Elements:\n"
            "   - Traditional practices\n"
            "   - Cultural symbols\n"
            "   - Customs and rituals\n\n"
            "3. Modern Relevance:\n"
            "   - Contemporary significance\n"
            "   - Current preservation status\n"
            "   - Modern adaptations\n\n"
            "4. Related Cultural Practices:\n"
            "   - Similar traditions\n"
            "   - Regional variations\n"
            "   - Cultural connections\n\n"
            "5. Educational Resources:\n"
            "   - Topics for further study\n"
            "   - Cultural preservation initiatives"
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
                            "resources about cultural elements mentioned in the content. "
                            "Format your response as a list of topics with descriptions."
                        )
                    },
                    {
                        "role": "user",
                        "content": f"Suggest learning resources about cultural elements in this content from {region}:\n{content}"
                    }
                ],
                temperature=0.3
            )

            resources_text = response.choices[0].message.content
            # Parse the text response into a structured format
            resources = [
                {
                    "topic": line.split(":")[0].strip(),
                    "description": line.split(":")[1].strip()
                }
                for line in resources_text.split("\n")
                if ":" in line
            ]

            return resources

        except Exception as e:
            logger.error(f"Error getting learning resources: {str(e)}")
            return []