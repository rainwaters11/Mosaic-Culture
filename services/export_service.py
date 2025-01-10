import os
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class ExportService:
    def __init__(self):
        self.supported_formats = ['pdf', 'epub', 'txt', 'json']
        self.available_formats = ['txt', 'json']  # Default to basic formats

        # Try to import optional dependencies
        try:
            from weasyprint import HTML, CSS
            self.weasyprint_available = True
            self.available_formats.append('pdf')
        except ImportError:
            logger.warning("WeasyPrint not available. PDF export will be disabled.")
            self.weasyprint_available = False

        try:
            import ebooklib
            from ebooklib import epub
            self.epub_available = True
            self.available_formats.append('epub')
        except ImportError:
            logger.warning("ebooklib not available. EPUB export will be disabled.")
            self.epub_available = False

        logger.info(f"Export service initialized with formats: {', '.join(self.available_formats)}")

    def export_to_pdf(self, story, template_string):
        """Export story to PDF using WeasyPrint"""
        if not self.weasyprint_available:
            logger.error("PDF export attempted but WeasyPrint is not available")
            return None

        try:
            from weasyprint import HTML, CSS
            html = HTML(string=template_string)
            css = CSS(string='''
                body { font-family: Arial, sans-serif; }
                h1 { color: #2C3E50; }
                .story-meta { color: #666; margin: 1em 0; }
                .story-content { line-height: 1.6; }
            ''')
            return html.write_pdf(stylesheets=[css])
        except Exception as e:
            logger.error(f"Error exporting to PDF: {str(e)}")
            return None

    def export_to_epub(self, story):
        """Export story to EPUB format"""
        if not self.epub_available:
            logger.error("EPUB export attempted but ebooklib is not available")
            return None

        try:
            from ebooklib import epub
            book = epub.EpubBook()

            # Set metadata
            book.set_identifier(f'story_{story.id}')
            book.set_title(story.title)
            book.set_language('en')
            book.add_author(story.author.username)

            # Create chapter
            c1 = epub.EpubHtml(title=story.title, file_name='story.xhtml')
            c1.content = f'''
                <h1>{story.title}</h1>
                <div class="story-meta">
                    <p>By: {story.author.username}</p>
                    <p>Region: {story.region}</p>
                    <p>Date: {story.submission_date.strftime('%B %d, %Y')}</p>
                </div>
                <div class="story-content">
                    {story.content}
                </div>
            '''

            book.add_item(c1)
            book.spine = ['nav', c1]
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())

            return epub.write_epub(book, {})
        except Exception as e:
            logger.error(f"Error exporting to EPUB: {str(e)}")
            return None

    def export_to_txt(self, story):
        """Export story to plain text"""
        try:
            text_content = f"""Title: {story.title}
Author: {story.author.username}
Region: {story.region}
Date: {story.submission_date.strftime('%B %d, %Y')}

{story.content}

Tags: {', '.join(tag.name for tag in story.tags)}
            """
            return text_content.encode('utf-8')
        except Exception as e:
            logger.error(f"Error exporting to TXT: {str(e)}")
            return None

    def export_to_json(self, story):
        """Export story to JSON format"""
        try:
            story_dict = {
                'title': story.title,
                'author': story.author.username,
                'content': story.content,
                'region': story.region,
                'submission_date': story.submission_date.isoformat(),
                'tags': [tag.name for tag in story.tags]
            }
            return json.dumps(story_dict, indent=2).encode('utf-8')
        except Exception as e:
            logger.error(f"Error exporting to JSON: {str(e)}")
            return None