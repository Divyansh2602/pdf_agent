#!/usr/bin/env python3
"""
Simplified AI Agent for converting Markdown/LaTeX files to IEEE format PDF
Supports academic formatting and email delivery
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
    """Simplified AI Agent for file → IEEE format PDF conversion"""

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
            "pandoc": {
                "engine": "xelatex",
                "template": "ieee_template_proper.tex",
                "options": [
                    "--standalone",
                    "--toc",
                    "--number-sections"
                ]
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
    def send_email(self, attachment_path: str, subject="IEEE Document Conversion Complete"):
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
            msg.attach(MIMEText("Please find attached your IEEE formatted document.", 'plain'))

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
    def convert_to_ieee_format(self, input_file: str, output_file: str | None = None) -> str:
        """Convert file to IEEE format PDF using Pandoc"""
        try:
            input_path = Path(input_file)
            if not output_file:
                out_dir = Path(self.config['output']['directory'])
                out_dir.mkdir(parents=True, exist_ok=True)
                output_file = str(out_dir / f"{input_path.stem}_IEEE.pdf")
            
            # Build pandoc command with IEEE specific options
            cmd = ["pandoc", str(input_path), "-o", str(output_file)]
            
            # Add engine
            engine = self.config['pandoc'].get('engine', 'xelatex')
            cmd.extend(["--pdf-engine", engine])
            
            # Add IEEE template if specified
            template = self.config['pandoc'].get('template')
            if template:
                # Check if template exists in current directory
                template_path = Path(template)
                if template_path.exists():
                    cmd.extend(["--template", str(template_path)])
                else:
                    # Check if it's in the current directory
                    local_template = Path.cwd() / template
                    if local_template.exists():
                        cmd.extend(["--template", str(local_template)])
            else:
                # Use default IEEE template if available
                default_template = Path("ieee_template_proper.tex")
                if default_template.exists():
                    cmd.extend(["--template", str(default_template)])
            
            # Add IEEE specific options for proper formatting
            ieee_options = [
                "--standalone",
                "--number-sections",
                "--columns", "72",
                "-V", "geometry:margin=1in",
                "-V", "fontsize=10pt",
                "-V", "documentclass=IEEEtran",
                "-V", "classoption=10pt,conference",
                "--top-level-division=section"
            ]
            cmd.extend(ieee_options)
            
            # Add other options
            options = self.config['pandoc'].get('options', [])
            cmd.extend(options)
            
            logger.info(f"Running pandoc command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"Successfully converted {input_file} to IEEE format PDF: {output_file}")
                return str(output_file)
            else:
                logger.error(f"Pandoc conversion failed: {result.stderr}")
                # Try without template as fallback
                logger.info("Trying conversion without template as fallback...")
                cmd_without_template = [arg for arg in cmd if not arg.startswith("--template")]
                result_fallback = subprocess.run(cmd_without_template, capture_output=True, text=True)
                if result_fallback.returncode == 0:
                    logger.info(f"Successfully converted {input_file} to PDF (without template): {output_file}")
                    return str(output_file)
                else:
                    logger.error(f"Fallback conversion also failed: {result_fallback.stderr}")
                    return ""
                
        except Exception as e:
            logger.error(f"Pandoc conversion error: {e}")
            return ""

    # ----------------------------------------------------------------
    def process_file(self, input_file: str, send_email=True, email_recipient=None):
        """Process file: convert to IEEE format PDF and optionally send via email"""
        try:
            logger.info(f"Processing file for IEEE format: {input_file}")
            
            # Convert file to IEEE format PDF using Pandoc
            pdf_path = self.convert_to_ieee_format(input_file)
            
            if not pdf_path:
                logger.error("Failed to convert file to IEEE format PDF.")
                return False
            
            # Send email if requested
            if send_email:
                # Use provided recipient or fall back to config
                if email_recipient:
                    original_recipient = self.config['email']['to_email']
                    self.config['email']['to_email'] = email_recipient
                    self.send_email(pdf_path, subject="Your IEEE Formatted PDF is Ready")
                    # Restore original recipient
                    self.config['email']['to_email'] = original_recipient
                else:
                    self.send_email(pdf_path, subject="Your IEEE Formatted PDF is Ready")
            
            logger.info("IEEE format file processing completed successfully.")
            return True
            
        except Exception as e:
            logger.error(f"File processing error: {e}")
            return False

    # ----------------------------------------------------------------
    def refine_to_ieee_style(self, content: str, file_type: str):
        """Use OpenAI to convert content to IEEE-style sections"""
        try:
            if not self.config['openai']['api_key']:
                return {"error": "OpenAI API key not set"}

            prompt = f"""
            You are an expert IEEE research paper writer and editor. Convert the following {file_type} text into a formally structured IEEE-style research paper with the exact section layout and formatting rules described below.

            Required Paper Structure:

            Abstract:

            Write a single, cohesive paragraph summarizing the entire paper.

            Do not include the word "Abstract" at the beginning.

            Keywords:

            Provide 3–8 technical keywords separated by commas.

            Do not include the word "Keywords" at the beginning.

            I. INTRODUCTION

            Write a detailed paragraph introducing the topic, background, motivation, and objectives.

            Ensure clarity and academic tone.

            II. METHODOLOGY

            Write a detailed paragraph explaining the methods, techniques, datasets, or approaches used in the research.

            III. RESULTS AND DISCUSSION

            Present key findings, insights, or performance results.

            Include analytical discussion of implications, strengths, and limitations.

            IV. CONCLUSION

            Summarize the major contributions and findings.

            Include remarks on possible future work or open challenges.

            Formatting Rules:

            Do NOT include section headers like "Abstract:" or "Keywords:" in the text — only the content.

            Do NOT include section numbers (I., II., etc.) inside the content paragraphs.

            Each section must be written as a formal, detailed academic paragraph (not bullet points).

            Use technical, IEEE-style English — precise, impersonal, and objective.

            Preserve the technical meaning and flow of the original {file_type} text but improve clarity and grammar.

            Content:
            {content}
            
            IMPORTANT: Your response should ONLY contain the properly formatted IEEE paper content. Do not include any explanations or additional text.
            """
            
            client = openai.OpenAI(api_key=self.config['openai']['api_key'])
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
    def process_with_ieee_refinement(self, input_file: str, send_email=True, email_recipient=None):
        """Process file with IEEE academic writing refinement"""
        try:
            # Read the input file
            with open(input_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Detect file type
            file_type = 'latex' if input_file.endswith(('.tex', '.latex')) else 'markdown'
            
            # Refine the content to IEEE style
            refinement = self.refine_to_ieee_style(content, file_type)
            if 'error' in refinement:
                logger.error(refinement['error'])
                return False
            
            # Check if refined content exists
            if 'content' not in refinement or not refinement['content']:
                logger.error("No content returned from refinement.")
                return False
            
            # Save refined content to a temporary file
            temp_dir = Path(self.config['output']['directory'])
            temp_dir.mkdir(parents=True, exist_ok=True)
            temp_file = temp_dir / f"ieee_{Path(input_file).name}"
            
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(refinement['content'])
            
            # Process the refined file
            result = self.process_file(str(temp_file), send_email, email_recipient)
            return result
        except Exception as e:
            logger.error(f"File processing with IEEE refinement error: {e}")
            return False

    # ----------------------------------------------------------------
    def process_file_with_fallback(self, input_file: str, send_email=True, email_recipient=None, use_ai_refinement=False):
        """Process file with fallback from AI refinement to pandoc if AI fails"""
        try:
            logger.info(f"Processing file: {input_file}")
            
            if use_ai_refinement:
                logger.info("Attempting AI-based IEEE formatting...")
                success = self.process_with_ieee_refinement(input_file, send_email, email_recipient)
                if success:
                    logger.info("AI-based formatting successful!")
                    return True
                else:
                    logger.warning("AI-based formatting failed, falling back to pandoc...")
            
            # Fallback to standard pandoc processing
            logger.info("Using standard pandoc processing...")
            return self.process_file(input_file, send_email, email_recipient)
            
        except Exception as e:
            logger.error(f"File processing with fallback error: {e}")
            return False

# ----------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Convert documents to IEEE format PDF")
    parser.add_argument("input", help="Path to input file (.md, .tex, etc.)")
    parser.add_argument("--config", default="config.json", help="Path to config.json")
    parser.add_argument("--refine", action="store_true", help="Refine to IEEE academic writing")
    parser.add_argument("--no-email", action="store_true", help="Skip email sending")
    args = parser.parse_args()

    agent = PDFAgent(args.config)
    
    if args.refine:
        success = agent.process_with_ieee_refinement(args.input)
    else:
        success = agent.process_file(args.input, send_email=not args.no_email)
    
    sys.exit(0 if success else 1)

# ----------------------------------------------------------------
if __name__ == "__main__":
    main()
