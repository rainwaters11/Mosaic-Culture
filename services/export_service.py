"""Service for exporting stories in different formats"""
import os
import tempfile
from weasyprint import HTML, CSS
from ebooklib import epub
import markdown2
from flask import render_template_string

class ExportService:
    def __init__(self):
        self.pdf_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; }
                .story-title { font-size: 24px; margin-bottom: 1em; }
                .story-meta { color: #666; margin-bottom: 1em; }
                .story-content { line-height: 1.6; }
            </style>
        </head>
        <body>
            <h1 class="story-title">{{ story.title }}</h1>
            <div class="story-meta">
                By {{ story.author.username }}
                {% if story.submission_date %}
                on {{ story.submission_date.strftime('%B %d, %Y') }}
                {% endif %}
                <br>
                Region: {{ story.region }}
            </div>
            <div class="story-content">
                {{ story.content }}
            </div>
        </body>
        </html>
        """

    def export_to_pdf(self, story):
        """Export story to PDF format"""
        try:
            # Render the HTML template with the story content
            html_content = render_template_string(self.pdf_template, story=story)
            
            # Create a temporary file for the PDF
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
                # Generate PDF from HTML
                HTML(string=html_content).write_pdf(tmp_file.name)
                return tmp_file.name
        except Exception as e:
            print(f"Error generating PDF: {str(e)}")
            return None

    def export_to_epub(self, story):
        """Export story to EPUB format"""
        try:
            # Create a new EPUB book
            book = epub.EpubBook()
            
            # Set metadata
            book.set_identifier(f'story_{story.id}')
            book.set_title(story.title)
            book.set_language('en')
            book.add_author(story.author.username)
            
            # Create chapter
            chapter = epub.EpubHtml(title=story.title, file_name='story.xhtml')
            chapter.content = f'''
                <h1>{story.title}</h1>
                <p class="meta">By {story.author.username}</p>
                <p class="meta">Region: {story.region}</p>
                <div class="content">{story.content}</div>
            '''
            
            # Add chapter and create spine
            book.add_item(chapter)
            book.spine = ['nav', chapter]
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix='.epub', delete=False) as tmp_file:
                epub.write_epub(tmp_file.name, book)
                return tmp_file.name
        except Exception as e:
            print(f"Error generating EPUB: {str(e)}")
            return None

    def export_to_txt(self, story):
        """Export story to plain text format"""
        try:
            content = f"""
{story.title}
By {story.author.username}
Region: {story.region}

{story.content}
            """
            
            with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tmp_file:
                tmp_file.write(content.encode('utf-8'))
                return tmp_file.name
        except Exception as e:
            print(f"Error generating TXT: {str(e)}")
            return None
