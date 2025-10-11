# PDF Agent - AI-Powered Document Conversion

An intelligent AI agent that converts LaTeX and Markdown files to PDF using pandoc, Overleaf, n8n automation, and email distribution.

## Features

- 🔄 **Multi-format Support**: Converts LaTeX (.tex) and Markdown (.md) files to PDF
- 🛠️ **Multiple Conversion Engines**: 
  - Pandoc with XeLaTeX for reliable conversion
  - Overleaf API for advanced LaTeX processing
- 📧 **Email Integration**: Automatically sends converted PDFs via email
- 🔗 **n8n Workflow**: Triggers automated workflows for advanced processing
- 📊 **Comprehensive Logging**: Detailed logs for monitoring and debugging
- ⚙️ **Configurable**: JSON-based configuration for easy customization

## Prerequisites

### Required Software
- Python 3.7+
- Pandoc
- LaTeX distribution (MiKTeX, TeX Live, or MacTeX)

### Optional Integrations
- Overleaf account (for advanced LaTeX processing)
- n8n instance (for workflow automation)
- SMTP email service (Gmail, Outlook, etc.)

## Installation

1. **Clone or download the project files**
2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Pandoc**:
   - Windows: Download from [pandoc.org](https://pandoc.org/installing.html)
   - macOS: `brew install pandoc`
   - Linux: `sudo apt-get install pandoc`

4. **Install LaTeX**:
   - Windows: [MiKTeX](https://miktex.org/)
   - macOS: [MacTeX](https://www.tug.org/mactex/)
   - Linux: `sudo apt-get install texlive-xetex`

## Configuration

1. **Edit `config.json`** with your settings:

```json
{
    "pandoc": {
        "engine": "xelatex",
        "template": null,
        "options": ["--standalone", "--toc", "--number-sections"]
    },
    "overleaf": {
        "api_url": "https://www.overleaf.com/api/v1",
        "api_key": "your_overleaf_api_key",
        "project_id": "your_project_id"
    },
    "email": {
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "username": "your_email@gmail.com",
        "password": "your_app_password",
        "from_email": "your_email@gmail.com",
        "to_email": "recipient@example.com"
    },
    "n8n": {
        "webhook_url": "https://your-n8n-instance.com/webhook/pdf-process",
        "api_key": "your_n8n_api_key"
    },
    "output": {
        "directory": "output",
        "filename_template": "{original_name}_{timestamp}.pdf"
    }
}
```

2. **Email Setup** (Gmail example):
   - Enable 2-factor authentication
   - Generate an App Password
   - Use the App Password in the config

3. **Overleaf Setup** (optional):
   - Get API key from Overleaf account settings
   - Create a project and get the project ID

4. **n8n Setup** (optional):
   - Import the provided `n8n_workflow.json`
   - Configure webhook URL and credentials

## Usage

### Basic Usage

```bash
# Convert a single file
python pdf_agent.py paper.md

# Convert with Overleaf (for LaTeX files)
python pdf_agent.py document.tex --overleaf

# Process entire directory
python pdf_agent.py ./documents --directory

# Skip email sending
python pdf_agent.py paper.md --no-email

# Skip n8n workflow
python pdf_agent.py paper.md --no-n8n
```

### Command Line Options

- `input`: Input file or directory path
- `--config`: Configuration file path (default: config.json)
- `--overleaf`: Use Overleaf for LaTeX conversion
- `--no-email`: Skip email sending
- `--no-n8n`: Skip n8n workflow trigger
- `--directory`: Process entire directory

### Examples

```bash
# Convert markdown to PDF and email
python pdf_agent.py "My Document.md"

# Convert LaTeX using Overleaf
python pdf_agent.py "research_paper.tex" --overleaf

# Process all files in a directory
python pdf_agent.py "./papers" --directory

# Custom configuration
python pdf_agent.py "document.md" --config "my_config.json"
```

## n8n Workflow

The included n8n workflow (`n8n_workflow.json`) provides:

1. **Webhook Trigger**: Receives PDF processing requests
2. **Conversion Method Check**: Routes to appropriate processor
3. **Overleaf Integration**: Compiles LaTeX documents
4. **PDF Download**: Retrieves converted files
5. **Email Sending**: Distributes PDFs via email
6. **Slack Notifications**: Sends status updates
7. **Database Logging**: Records conversion history

### Importing the Workflow

1. Open your n8n instance
2. Go to Workflows → Import from File
3. Select `n8n_workflow.json`
4. Configure credentials and webhook URLs
5. Activate the workflow

## File Structure

```
pdf-agent/
├── pdf_agent.py          # Main AI agent script
├── config.json           # Configuration file
├── n8n_workflow.json     # n8n workflow definition
├── requirements.txt      # Python dependencies
├── README.md            # This file
├── output/              # Generated PDF files
└── pdf_agent.log        # Log file
```

## Supported File Types

- **Markdown**: `.md`, `.markdown`
- **LaTeX**: `.tex`, `.latex`

## Error Handling

The agent includes comprehensive error handling:

- File validation and type detection
- Conversion fallback (Overleaf → Pandoc)
- Email delivery confirmation
- Detailed logging for debugging
- Graceful failure handling

## Logging

Logs are written to both console and `pdf_agent.log` file:

- INFO: Normal operations
- WARNING: Non-critical issues
- ERROR: Conversion or delivery failures

## Troubleshooting

### Common Issues

1. **Pandoc not found**:
   - Ensure Pandoc is installed and in PATH
   - Test with: `pandoc --version`

2. **LaTeX errors**:
   - Install complete LaTeX distribution
   - Check for missing packages

3. **Email sending fails**:
   - Verify SMTP settings
   - Check app password for Gmail
   - Ensure 2FA is enabled

4. **Overleaf API errors**:
   - Verify API key and project ID
   - Check project permissions

### Debug Mode

Enable detailed logging by modifying the logging level in `pdf_agent.py`:

```python
logging.basicConfig(level=logging.DEBUG)
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is open source and available under the MIT License.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the logs
3. Create an issue with detailed information

---

**Note**: This agent is designed to be flexible and extensible. You can easily add new conversion engines, email providers, or workflow integrations by extending the base classes.
