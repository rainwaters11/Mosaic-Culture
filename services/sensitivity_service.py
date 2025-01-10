"""Cultural sensitivity checking service using OpenAI API"""
import logging
import os
from typing import Dict, List, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)

class SensitivityService:
    def __init__(self):
        self.client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))

    def check_content(self, content: str, context: Dict[str, str]) -> Dict[str, any]:
        """
        Check content for cultural sensitivity issues
        Args:
            content: The text content to check
            context: Dictionary containing context like region, theme, etc.
        Returns:
            Dictionary containing sensitivity analysis results
        """
        try:
            logger.debug("Starting sensitivity check")
            system_prompt = (
                "You are a cultural sensitivity expert with deep knowledge of global cultures, "
                "traditions, and social norms. Analyze the following content for:"
                "\n1. Cultural appropriation"
                "\n2. Stereotyping"
                "\n3. Misrepresentation of traditions"
                "\n4. Inappropriate language or terminology"
                "\n5. Historical inaccuracies"
                "\nProvide specific feedback and suggestions for improvement."
            )

            user_prompt = self._create_analysis_prompt(content, context)
            
            response = self.client.chat.completions.create(
                model="gpt-4",  # Using GPT-4 for better cultural understanding
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )

            analysis = response.choices[0].message.content
            logger.info("Completed sensitivity analysis")
            return {
                "analysis": analysis,
                "has_issues": self._determine_severity(analysis)
            }

        except Exception as e:
            logger.error(f"Error in sensitivity check: {str(e)}")
            return {
                "error": "Failed to complete sensitivity analysis",
                "has_issues": True
            }

    def _create_analysis_prompt(self, content: str, context: Dict[str, str]) -> str:
        """Create a detailed prompt for sensitivity analysis"""
        return (
            f"Analyze this content about {context.get('theme', 'unknown theme')} "
            f"from {context.get('region', 'unknown region')}:\n\n"
            f"{content}\n\n"
            "Provide analysis in JSON format with the following structure:\n"
            "{\n"
            '  "overall_rating": 1-10 (10 being most culturally sensitive),\n'
            '  "issues": [\n'
            "    {\n"
            '      "type": "issue category",\n'
            '      "description": "detailed description",\n'
            '      "suggestion": "how to fix"\n'
            "    }\n"
            "  ],\n"
            '  "positive_aspects": [\n'
            '    "list of culturally authentic elements"\n'
            "  ],\n"
            '  "improvement_suggestions": "overall suggestions for improvement"\n'
            "}"
        )

    def _determine_severity(self, analysis: str) -> bool:
        """
        Determine if the content has significant sensitivity issues
        Returns True if there are major concerns
        """
        try:
            import json
            result = json.loads(analysis)
            # Consider it an issue if rating is below 7 or if there are any critical issues
            return (
                result.get("overall_rating", 0) < 7 or
                any(issue.get("type", "").lower() in ["critical", "severe", "major"] 
                    for issue in result.get("issues", []))
            )
        except Exception as e:
            logger.error(f"Error parsing sensitivity analysis: {str(e)}")
            return True
