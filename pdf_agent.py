#!/usr/bin/env python3
"""
AI Agent for converting Markdown files (README.md) into IEEE-style Research Papers
Output: IEEE-formatted DOCX + PDF, then emailed to recipient.
"""

import os
import sys
import json
import logging
import smtplib
import subprocess
import argparse
from pathlib import Path
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from docx import Document
import openai

# ----------------------------------------------------------------
# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("pdf_agent.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ----------------------------------------------------------------
class PDFAgent:
    """AI Agent for Markdown → IEEE Word + PDF + Email"""

    def __init__(self, config_file="config.json"):
        self.config = self.load_config(config_file)
        if self.config.get('openai', {}).get('api_key'):
            openai.api_key = self.config['openai']['api_key']

    # ----------------------------------------------------------------
    def load_config(self, config_file: str):
        """Load configuration settings"""
        default_config = {
            "email": {
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "username": "",
                "password": "",
                "from_email": "",
                "to_email": ""
            },
            "openai": {
                "api_key": "",
                "model": "gpt-4o-mini",
                "temperature": 0.3,
                "max_tokens": 4000
            },
            "output": {
                "directory": "output"
            }
        }
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                cfg = json.load(f)
            for k, v in default_config.items():
                if k not in cfg:
                    cfg[k] = v
            return cfg
        else:
            with open(config_file, 'w') as f:
                json.dump(default_config, f, indent=4)
            logger.warning("Created default config.json; please fill it in.")
            return default_config

    # ----------------------------------------------------------------
    def send_email(self, attachment_path: str, subject="IEEE Paper Generated"):
        """Send PDF via email"""
        try:
            e = self.config['email']
            if not all([e['username'], e['password'], e['to_email']]):
                logger.warning("Incomplete email configuration.")
                return False

            msg = MIMEMultipart()
            msg['From'] = e['from_email'] or e['username']
            msg['To'] = e['to_email']
            msg['Subject'] = subject
            msg.attach(MIMEText("Please find attached your IEEE formatted paper.", 'plain'))

            with open(attachment_path, 'rb') as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f'attachment; filename={Path(attachment_path).name}')
                msg.attach(part)

            server = smtplib.SMTP(e['smtp_server'], e['smtp_port'])
            server.starttls()
            server.login(e['username'], e['password'])
            server.sendmail(msg['From'], msg['To'], msg.as_string())
            server.quit()
            logger.info(f"Emailed {attachment_path} to {e['to_email']}")
            return True
        except Exception as ex:
            logger.error(f"Email failed: {ex}")
            return False

    # ----------------------------------------------------------------
    def refine_to_ieee_style(self, markdown_text: str):
        """Use OpenAI to convert Markdown content to IEEE-style sections"""
        try:
            if not self.config['openai']['api_key']:
                return {"error": "OpenAI API key not set"}

            prompt = f"""
            You are an expert IEEE research paper writer.
            Convert the following Markdown text into a properly structured IEEE-style paper
            with these sections:
            - Abstract
            - Keywords
            - Introduction
            - Methodology
            - Results and Discussion
            - Conclusion

            Ensure it follows IEEE tone, academic language, and clarity.
            Markdown text:
            {markdown_text}
            """

            client = openai.OpenAI(api_key=openai.api_key)
            resp = client.chat.completions.create(
                model=self.config['openai']['model'],
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.config['openai']['max_tokens'],
                temperature=self.config['openai']['temperature']
            )
            refined = resp.choices[0].message.content
            return {"content": refined}
        except Exception as e:
            logger.error(f"OpenAI refinement failed: {e}")
            return {"error": str(e)}

    # ----------------------------------------------------------------
    def fill_ieee_template(self, ieee_text: str, template_path="Conference-template-A4.docx"):
        """Fill IEEE Word template with AI-generated content"""
        try:
            if not os.path.exists(template_path):
                logger.error(f"Template file not found: {template_path}")
                return None

            doc = Document(template_path)
            sections = ["Abstract", "Keywords", "Introduction", "Methodology", "Results", "Conclusion"]
            content = {s: "" for s in sections}

            # Extract each section
            current = None
            for line in ieee_text.splitlines():
                for sec in sections:
                    if sec.lower() in line.lower():
                        current = sec
                        break
                else:
                    if current:
                        content[current] += line + "\n"

            # Replace placeholders
            for p in doc.paragraphs:
                txt = p.text.lower()
                if "abstract" in txt:
                    p.text = "Abstract—" + content.get("Abstract", "")
                elif "index terms" in txt or "keywords" in txt:
                    p.text = "Keywords—" + content.get("Keywords", "")
                elif "introduction" in txt:
                    p.text = "I. Introduction\n" + content.get("Introduction", "")
                elif "methodology" in txt:
                    p.text = "II. Methodology\n" + content.get("Methodology", "")
                elif "results" in txt:
                    p.text = "III. Results and Discussion\n" + content.get("Results", "")
                elif "conclusion" in txt:
                    p.text = "IV. Conclusion\n" + content.get("Conclusion", "")

            out_dir = Path(self.config['output']['directory'])
            out_dir.mkdir(parents=True, exist_ok=True)

            out_docx = out_dir / "IEEE_Generated_Paper.docx"
            doc.save(str(out_docx))

            # Convert DOCX → PDF
            pdf_out = out_dir / "IEEE_Generated_Paper.pdf"
            try:
                # Try to use soffice directly first
                subprocess.run(["soffice", "--headless", "--convert-to", "pdf", str(out_docx), "--outdir", str(out_dir)], check=True)
                logger.info(f"Generated PDF: {pdf_out}")
            except Exception:
                try:
                    # Try with full path to LibreOffice
                    subprocess.run(["C:\\Program Files\\LibreOffice\\program\\soffice.exe", "--headless", "--convert-to", "pdf", str(out_docx), "--outdir", str(out_dir)], check=True)
                    logger.info(f"Generated PDF: {pdf_out}")
                except Exception:
                    logger.warning("LibreOffice not found. Sending DOCX instead of PDF.")
                    pdf_out = out_docx

            return str(pdf_out)
        except Exception as e:
            logger.error(f"Error filling IEEE template: {e}")
            return None

    # ----------------------------------------------------------------
    def process_markdown(self, input_file: str):
        """Full process: Markdown → IEEE DOCX/PDF"""
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                md = f.read()
            logger.info(f"Processing Markdown file: {input_file}")

            ieee_data = self.refine_to_ieee_style(md)
            if 'error' in ieee_data:
                logger.error(ieee_data['error'])
                return False
            
            # Check if content exists
            if 'content' not in ieee_data or not ieee_data['content']:
                logger.error("No content returned from refinement.")
                return False

            pdf_result = self.fill_ieee_template(ieee_data['content'])
            if not pdf_result:
                logger.error("Failed to generate IEEE document.")
                return False
            pdf_path = pdf_result

            logger.info("IEEE Paper successfully created.")
            return True
        except Exception as e:
            logger.error(f"Markdown processing error: {e}")
            return False

    # ----------------------------------------------------------------
    def process_file(self, input_file: str, use_overleaf=False, send_email=True, trigger_n8n=True, email_recipient=None):
        """Process file with academic formatting (Pandoc only)"""
        try:
            # For now, we'll use the existing markdown processing
            # In a more complete implementation, this would handle different file types
            
            # Read the input file
            with open(input_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Save content to a temporary markdown file if needed
            temp_file = input_file
            
            # Process the file as markdown
            result = self.process_markdown(temp_file)
            
            # If processing was successful and we need to send email
            if result and send_email:
                # Find the generated PDF
                output_dir = Path(self.config['output']['directory'])
                pdf_files = list(output_dir.glob('*.pdf'))
                latest_pdf = max(pdf_files, key=os.path.getctime) if pdf_files else None
                
                if latest_pdf:
                    # Use the provided email recipient or fall back to config
                    if email_recipient:
                        # Temporarily update the config for this send operation
                        original_recipient = self.config['email']['to_email']
                        self.config['email']['to_email'] = email_recipient
                        self.send_email(str(latest_pdf), subject="Your Converted PDF is Ready ✅")
                        # Restore original recipient
                        self.config['email']['to_email'] = original_recipient
                    else:
                        self.send_email(str(latest_pdf), subject="Your Converted PDF is Ready ✅")
            
            return result
        except Exception as e:
            logger.error(f"File processing error: {e}")
            return False

    # ----------------------------------------------------------------
    def process_file_with_refinement(self, input_file: str, journal_style: str = "formal", use_overleaf=False, send_email=True, trigger_n8n=True, email_recipient=None):
        """Process file with academic writing refinement"""
        try:
            # Read the input file
            with open(input_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Detect file type
            file_type = 'latex' if input_file.endswith(('.tex', '.latex')) else 'markdown'
            
            # Refine the content
            refinement = self.refine_academic_writing(content, file_type, journal_style)
            if 'error' in refinement:
                logger.error(refinement['error'])
                return False
            
            # Check if refined content exists
            if 'refined_content' not in refinement or not refinement['refined_content']:
                logger.error("No refined content returned from refinement.")
                return False
            
            # Save refined content to a temporary file
            temp_dir = Path(self.config['output']['directory'])
            temp_dir.mkdir(parents=True, exist_ok=True)
            temp_file = temp_dir / f"refined_{Path(input_file).name}"
            
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(refinement['refined_content'])
            
            # Process the refined file
            result = self.process_file(str(temp_file), use_overleaf, send_email, trigger_n8n, email_recipient)
            return result
        except Exception as e:
            logger.error(f"File processing with refinement error: {e}")
            return False

    # ----------------------------------------------------------------
    def refine_academic_writing(self, content: str, file_type: str, journal_style: str = "formal"):
        """Refine academic writing using OpenAI"""
        try:
            if not self.config['openai']['api_key']:
                return {"error": "OpenAI API key not set"}

            style_prompts = {
                "formal": "Ensure formal academic tone with proper structure and clarity.",
                "ieee": "Convert to IEEE journal style with technical precision and structure."
            }
            
            style_prompt = style_prompts.get(journal_style, style_prompts["formal"])
            
            prompt = f"""
            Refine the following {file_type} content into {journal_style} academic style:
            
            {style_prompt}
            
            Content:
            {content}
            """

            client = openai.OpenAI(api_key=openai.api_key)
            resp = client.chat.completions.create(
                model=self.config['openai']['model'],
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.config['openai']['max_tokens'],
                temperature=self.config['openai']['temperature']
            )
            refined = resp.choices[0].message.content
            return {"refined_content": refined}
        except Exception as e:
            logger.error(f"OpenAI refinement failed: {e}")
            return {"error": str(e)}

# ----------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Convert Markdown → IEEE Paper (PDF + Email)")
    parser.add_argument("input", help="Path to Markdown file (.md)")
    parser.add_argument("--config", default="config.json", help="Path to config.json")
    args = parser.parse_args()

    agent = PDFAgent(args.config)
    if Path(args.input).suffix.lower() not in ['.md', '.markdown']:
        logger.error("Only Markdown (.md) files are supported.")
        sys.exit(1)

    success = agent.process_markdown(args.input)
    sys.exit(0 if success else 1)

# ----------------------------------------------------------------
if __name__ == "__main__":
    main()
