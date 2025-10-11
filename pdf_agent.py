#!/usr/bin/env python3
"""
AI Agent for converting LaTeX and Markdown files to PDF
Supports pandoc, Overleaf, n8n integration, and email functionality
"""

import os
import sys
import json
import logging
import smtplib
import subprocess
import requests
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional, Dict, List, Tuple
import argparse
from datetime import datetime
import openai

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pdf_agent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PDFAgent:
    """AI Agent for PDF conversion and email distribution"""
    
    def __init__(self, config_file: str = "config.json"):
        """Initialize the PDF Agent with configuration"""
        self.config = self.load_config(config_file)
        self.supported_formats = ['.md', '.markdown', '.tex', '.latex']
        
        # Initialize OpenAI
        if self.config.get('openai', {}).get('api_key'):
            openai.api_key = self.config['openai']['api_key']
        
    def load_config(self, config_file: str) -> Dict:
        """Load configuration from JSON file"""
        default_config = {
            "pandoc": {
                "engine": "xelatex",
                "template": None,
                "options": ["--standalone", "--toc"]
            },
            "overleaf": {
                "api_url": "https://www.overleaf.com/api/v1",
                "api_key": "",
                "project_id": ""
            },
            "email": {
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "username": "",
                "password": "",
                "from_email": "",
                "to_email": ""
            },
            "n8n": {
                "webhook_url": "",
                "api_key": ""
            },
            "openai": {
                "api_key": "",
                "model": "gpt-4o-mini",
                "temperature": 0.3,
                "max_tokens": 4000
            },
            "output": {
                "directory": "output",
                "filename_template": "{original_name}_{timestamp}.pdf"
            }
        }
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                # Merge with defaults
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
            except Exception as e:
                logger.error(f"Error loading config: {e}")
                return default_config
        else:
            # Create default config file
            with open(config_file, 'w') as f:
                json.dump(default_config, f, indent=4)
            logger.info(f"Created default config file: {config_file}")
            return default_config
    
    def detect_file_type(self, file_path: str) -> Optional[str]:
        """Detect if file is LaTeX or Markdown based on extension and content"""
        path = Path(file_path)
        extension = path.suffix.lower()
        
        if extension in ['.tex', '.latex']:
            return 'latex'
        elif extension in ['.md', '.markdown']:
            return 'markdown'
        else:
            # Try to detect by content
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read(1000)  # Read first 1000 chars
                    if '\\documentclass' in content or '\\begin{document}' in content:
                        return 'latex'
                    elif content.startswith('#') or '##' in content:
                        return 'markdown'
            except Exception as e:
                logger.error(f"Error reading file {file_path}: {e}")
        
        return None
    
    def convert_with_pandoc(self, input_file: str, output_file: str, file_type: str) -> bool:
        """Convert file to PDF using pandoc"""
        try:
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            # Build pandoc command
            cmd = ['pandoc', input_file, '-o', output_file]
            
            # Add engine and options based on file type
            if file_type == 'latex':
                cmd.extend(['--pdf-engine', self.config['pandoc']['engine']])
            else:  # markdown
                cmd.extend(['--pdf-engine', self.config['pandoc']['engine']])
            
            # Add additional options
            for option in self.config['pandoc']['options']:
                cmd.append(option)
            
            # Add template if specified
            if self.config['pandoc']['template']:
                cmd.extend(['--template', self.config['pandoc']['template']])
            
            logger.info(f"Running pandoc command: {' '.join(cmd)}")
            
            # Execute pandoc with proper encoding
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            
            if result.returncode == 0:
                logger.info(f"Successfully converted {input_file} to {output_file}")
                return True
            else:
                logger.error(f"Pandoc conversion failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error during pandoc conversion: {e}")
            return False
    
    def convert_with_overleaf(self, input_file: str, output_file: str) -> bool:
        """Convert LaTeX file using Overleaf API"""
        try:
            if not self.config['overleaf']['api_key']:
                logger.warning("Overleaf API key not configured, skipping Overleaf conversion")
                return False
            
            # Read LaTeX content
            with open(input_file, 'r', encoding='utf-8') as f:
                latex_content = f.read()
            
            # Prepare Overleaf API request
            headers = {
                'Authorization': f'Bearer {self.config["overleaf"]["api_key"]}',
                'Content-Type': 'application/json'
            }
            
            # Compile project
            compile_url = f"{self.config['overleaf']['api_url']}/projects/{self.config['overleaf']['project_id']}/compile"
            
            response = requests.post(compile_url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                # Download compiled PDF
                pdf_url = response.json().get('pdf_url')
                if pdf_url:
                    pdf_response = requests.get(pdf_url)
                    if pdf_response.status_code == 200:
                        with open(output_file, 'wb') as f:
                            f.write(pdf_response.content)
                        logger.info(f"Successfully converted with Overleaf: {output_file}")
                        return True
            
            logger.error(f"Overleaf conversion failed: {response.text}")
            return False
            
        except Exception as e:
            logger.error(f"Error during Overleaf conversion: {e}")
            return False
    
    def send_email(self, pdf_file: str, subject: str = "PDF Document") -> bool:
        """Send PDF via email"""
        try:
            if not all([self.config['email']['username'], 
                       self.config['email']['password'], 
                       self.config['email']['to_email']]):
                logger.warning("Email configuration incomplete, skipping email")
                return False
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.config['email']['from_email'] or self.config['email']['username']
            msg['To'] = self.config['email']['to_email']
            msg['Subject'] = subject
            
            # Add body
            body = f"Please find the attached PDF document generated from {Path(pdf_file).stem}"
            msg.attach(MIMEText(body, 'plain'))
            
            # Attach PDF
            with open(pdf_file, 'rb') as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename= {Path(pdf_file).name}'
                )
                msg.attach(part)
            
            # Send email
            server = smtplib.SMTP(self.config['email']['smtp_server'], 
                                self.config['email']['smtp_port'])
            server.starttls()
            server.login(self.config['email']['username'], 
                        self.config['email']['password'])
            text = msg.as_string()
            server.sendmail(msg['From'], msg['To'], text)
            server.quit()
            
            logger.info(f"Email sent successfully to {self.config['email']['to_email']}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False
    
    def trigger_n8n_workflow(self, pdf_file: str, metadata: Dict) -> bool:
        """Trigger n8n workflow with PDF file"""
        try:
            if not self.config['n8n']['webhook_url']:
                logger.warning("n8n webhook URL not configured, skipping n8n trigger")
                return False
            
            # Prepare payload
            payload = {
                'pdf_file': pdf_file,
                'metadata': metadata,
                'timestamp': datetime.now().isoformat()
            }
            
            headers = {}
            if self.config['n8n']['api_key']:
                headers['Authorization'] = f"Bearer {self.config['n8n']['api_key']}"
            
            response = requests.post(
                self.config['n8n']['webhook_url'],
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info("n8n workflow triggered successfully")
                return True
            else:
                logger.error(f"n8n workflow failed: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error triggering n8n workflow: {e}")
            return False
    
    def refine_academic_writing(self, content: str, file_type: str, journal_style: str = "formal") -> Dict:
        """Use OpenAI to refine writing into formal, academic-journal style language"""
        try:
            if not self.config.get('openai', {}).get('api_key'):
                logger.warning("OpenAI API key not configured, skipping writing refinement")
                return {"error": "OpenAI API key not configured"}
            
            # Define academic writing style prompts based on journal style
            style_prompts = {
                "formal": """
                Refine this text into formal, academic-journal style language. Focus on:
                1. Using precise, scholarly vocabulary
                2. Maintaining objective, third-person perspective
                3. Employing passive voice where appropriate
                4. Ensuring proper academic sentence structure
                5. Adding appropriate academic transitions and connectors
                6. Maintaining consistency in terminology
                7. Ensuring proper academic tone and register
                """,
                "ieee": """
                Refine this text for IEEE journal/conference style. Focus on:
                1. IEEE-specific terminology and conventions
                2. Technical precision and clarity
                3. Proper use of technical abbreviations
                4. IEEE citation and reference formatting
                5. Formal engineering writing style
                6. Clear problem statement and methodology
                """,
                "acm": """
                Refine this text for ACM journal/conference style. Focus on:
                1. ACM-specific terminology and conventions
                2. Computer science writing standards
                3. Clear algorithmic descriptions
                4. Proper use of technical terminology
                5. ACM citation and reference formatting
                6. Formal computer science writing style
                """,
                "springer": """
                Refine this text for Springer journal style. Focus on:
                1. Springer-specific formatting requirements
                2. Scientific writing standards
                3. Clear methodology and results presentation
                4. Proper scientific terminology
                5. Springer citation and reference formatting
                6. Formal scientific writing style
                """,
                "elsevier": """
                Refine this text for Elsevier journal style. Focus on:
                1. Elsevier-specific formatting requirements
                2. Medical/scientific writing standards
                3. Clear methodology and results presentation
                4. Proper scientific terminology
                5. Elsevier citation and reference formatting
                6. Formal scientific writing style
                """,
                "nature": """
                Refine this text for Nature journal style. Focus on:
                1. Nature-specific formatting requirements
                2. High-impact scientific writing standards
                3. Clear, concise scientific communication
                4. Proper scientific terminology
                5. Nature citation and reference formatting
                6. Formal, prestigious scientific writing style
                """
            }
            
            # Get the appropriate style prompt
            style_prompt = style_prompts.get(journal_style, style_prompts["formal"])
            
            # Create the full prompt
            full_prompt = f"""
            {style_prompt}
            
            Please refine the following {file_type} content while maintaining the original structure and formatting:
            
            {content}
            
            Return the refined content in the same format ({file_type}) with improved academic writing style.
            """
            
            # Get OpenAI configuration
            openai_config = self.config.get('openai', {})
            model = openai_config.get('model', 'gpt-4o-mini')
            temperature = openai_config.get('temperature', 0.3)
            max_tokens = openai_config.get('max_tokens', 4000)
            
            # Call OpenAI API
            client = openai.OpenAI(api_key=openai.api_key)
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system", 
                        "content": f"You are an expert academic writing assistant specializing in {journal_style} journal formatting and formal academic writing standards."
                    },
                    {
                        "role": "user", 
                        "content": full_prompt
                    }
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            refined_content = response.choices[0].message.content
            
            return {
                "refined_content": refined_content,
                "journal_style": journal_style,
                "file_type": file_type,
                "timestamp": datetime.now().isoformat(),
                "model_used": model,
                "tokens_used": response.usage.total_tokens if response.usage else None
            }
            
        except Exception as e:
            logger.error(f"Error refining academic writing: {e}")
            return {"error": str(e)}
    
    def process_file_with_refinement(self, input_file: str, journal_style: str = "formal", 
                                   use_overleaf: bool = False, send_email: bool = True, 
                                   trigger_n8n: bool = True) -> bool:
        """Process file with OpenAI writing refinement"""
        try:
            # Read the original content
            with open(input_file, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            # Detect file type
            file_type = self.detect_file_type(input_file)
            if not file_type:
                logger.error(f"Unsupported file type: {input_file}")
                return False
            
            # Refine the writing
            logger.info(f"Refining academic writing for {file_type} file with {journal_style} style...")
            refinement_result = self.refine_academic_writing(original_content, file_type, journal_style)
            
            if 'error' in refinement_result:
                logger.error(f"Writing refinement failed: {refinement_result['error']}")
                return False
            
            # Create refined file
            input_path = Path(input_file)
            refined_filename = f"refined_{input_path.stem}_{journal_style}{input_path.suffix}"
            refined_filepath = os.path.join(os.path.dirname(input_file), refined_filename)
            
            with open(refined_filepath, 'w', encoding='utf-8') as f:
                f.write(refinement_result['refined_content'])
            
            logger.info(f"Writing refined and saved to: {refined_filepath}")
            
            # Process the refined file
            return self.process_file(refined_filepath, use_overleaf, send_email, trigger_n8n)
            
        except Exception as e:
            logger.error(f"Error processing file with refinement: {e}")
            return False
    
    def process_file(self, input_file: str, use_overleaf: bool = False, 
                    send_email: bool = True, trigger_n8n: bool = True) -> bool:
        """Main processing function"""
        try:
            # Validate input file
            if not os.path.exists(input_file):
                logger.error(f"Input file not found: {input_file}")
                return False
            
            # Detect file type
            file_type = self.detect_file_type(input_file)
            if not file_type:
                logger.error(f"Unsupported file type: {input_file}")
                return False
            
            logger.info(f"Processing {file_type} file: {input_file}")
            
            # Generate output filename
            input_path = Path(input_file)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = self.config['output']['filename_template'].format(
                original_name=input_path.stem,
                timestamp=timestamp
            )
            output_file = os.path.join(self.config['output']['directory'], output_filename)
            
            # Convert to PDF
            success = False
            if file_type == 'latex' and use_overleaf:
                success = self.convert_with_overleaf(input_file, output_file)
                if not success:
                    logger.info("Overleaf conversion failed, falling back to pandoc")
                    success = self.convert_with_pandoc(input_file, output_file, file_type)
            else:
                success = self.convert_with_pandoc(input_file, output_file, file_type)
            
            if not success:
                logger.error("PDF conversion failed")
                return False
            
            # Prepare metadata
            metadata = {
                'input_file': input_file,
                'output_file': output_file,
                'file_type': file_type,
                'conversion_method': 'overleaf' if (file_type == 'latex' and use_overleaf) else 'pandoc',
                'timestamp': timestamp
            }
            
            # Send email if requested
            if send_email:
                subject = f"PDF Document: {input_path.stem}"
                self.send_email(output_file, subject)
            
            # Trigger n8n workflow if requested
            if trigger_n8n:
                self.trigger_n8n_workflow(output_file, metadata)
            
            logger.info(f"Successfully processed {input_file} -> {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing file {input_file}: {e}")
            return False
    
    def process_directory(self, directory: str, **kwargs) -> List[bool]:
        """Process all supported files in a directory"""
        results = []
        directory_path = Path(directory)
        
        if not directory_path.exists():
            logger.error(f"Directory not found: {directory}")
            return results
        
        # Find all supported files
        files = []
        for ext in self.supported_formats:
            files.extend(directory_path.glob(f"*{ext}"))
        
        logger.info(f"Found {len(files)} files to process in {directory}")
        
        for file_path in files:
            result = self.process_file(str(file_path), **kwargs)
            results.append(result)
        
        return results

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='AI Agent for PDF conversion')
    parser.add_argument('input', help='Input file or directory path')
    parser.add_argument('--config', default='config.json', help='Configuration file path')
    parser.add_argument('--overleaf', action='store_true', help='Use Overleaf for LaTeX conversion')
    parser.add_argument('--no-email', action='store_true', help='Skip email sending')
    parser.add_argument('--no-n8n', action='store_true', help='Skip n8n workflow trigger')
    parser.add_argument('--directory', action='store_true', help='Process entire directory')
    
    args = parser.parse_args()
    
    # Initialize agent
    agent = PDFAgent(args.config)
    
    # Process input
    if args.directory:
        results = agent.process_directory(
            args.input,
            use_overleaf=args.overleaf,
            send_email=not args.no_email,
            trigger_n8n=not args.no_n8n
        )
        success_count = sum(results)
        total_count = len(results)
        logger.info(f"Processed {success_count}/{total_count} files successfully")
    else:
        success = agent.process_file(
            args.input,
            use_overleaf=args.overleaf,
            send_email=not args.no_email,
            trigger_n8n=not args.no_n8n
        )
        if success:
            logger.info("File processed successfully")
        else:
            logger.error("File processing failed")
            sys.exit(1)

if __name__ == "__main__":
    main()
