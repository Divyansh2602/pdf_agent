# PDF Agent: AI-Powered Document Conversion

## Abstract

This paper presents the PDF Agent, an intelligent AI-driven tool for converting LaTeX and Markdown files into PDF format. Utilizing advanced technologies such as Pandoc, Overleaf, and n8n automation, the PDF Agent streamlines document conversion and distribution processes.

## Introduction

The proliferation of digital documents necessitates efficient conversion tools that support multiple formats. The PDF Agent addresses this need by leveraging existing technologies to convert LaTeX (.tex) and Markdown (.md) files into PDF format. This paper outlines the features, methodology, and results of implementing the PDF Agent, emphasizing its automation capabilities and integration with email services.

## Methodology

### Features

The PDF Agent incorporates several key features:

- **Multi-format Support**: Converts LaTeX and Markdown files to PDF.
- **Multiple Conversion Engines**: Utilizes Pandoc with XeLaTeX for reliable conversions and the Overleaf API for advanced LaTeX processing.
- **Email Integration**: Automatically distributes converted PDFs via email.
- **n8n Workflow Automation**: Triggers automated workflows for enhanced processing.
- **Comprehensive Logging**: Maintains detailed logs for monitoring and debugging.
- **Configurable Settings**: Employs a JSON-based configuration for customization.

### Prerequisites

The following software is required for installation:

- Python 3.7 or higher
- Pandoc
- A LaTeX distribution (MiKTeX, TeX Live, or MacTeX)

Optional integrations include an Overleaf account, an n8n instance for workflow automation, and an SMTP email service (e.g., Gmail, Outlook).

### Installation

1. Clone or download the project files.
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Install Pandoc:
   - Windows: Download from [pandoc.org](https://pandoc.org/installing.html)
   - macOS: `brew install pandoc`
   - Linux: `sudo apt-get install pandoc`
4. Install a LaTeX distribution:
   - Windows: [MiKTeX](https://miktex.org/)
   - macOS: [MacTeX](https://www.tug.org/mactex/)
   - Linux: `sudo apt-get install texlive-xetex`

### Configuration

The configuration file `config.json` must be edited to include user-specific settings, including Pandoc options, Overleaf API credentials, email settings, and n8n webhook details.

### Usage

The PDF Agent can be invoked via command line with various options:

- Convert a single file:
  ```bash
  python pdf_agent.py paper.md
  ```
- Convert a LaTeX file using Overleaf:
  ```bash
  python pdf_agent.py document.tex --overleaf
  ```
- Process an entire directory:
  ```bash
  python pdf_agent.py ./documents --directory
  ```

## Results

The PDF Agent successfully converts documents while providing detailed logs for monitoring. It supports both Markdown and LaTeX formats, ensuring versatility in document processing. The integration with email services allows for seamless distribution of converted PDFs.

### Logging and Error Handling

The agent features comprehensive error handling, including file validation, conversion fallbacks, and email delivery confirmations. Logs are generated for all operations, categorized by severity (INFO, WARNING, ERROR).

## Conclusion

The PDF Agent demonstrates a robust solution for converting LaTeX and Markdown files to PDF format. Its integration with automation tools and email services enhances productivity and simplifies document management. Future work may involve expanding the range of supported formats and improving error handling mechanisms.

## Acknowledgments

This project is open-source and available under the MIT License. Contributions are welcome, and users are encouraged to report issues or suggest enhancements.

## References

- [Pandoc Documentation](https://pandoc.org)
- [Overleaf API Documentation](https://www.overleaf.com)
- [n8n Workflow Automation](https://n8n.io)

---

**Note**: The PDF Agent is designed for extensibility, allowing users to integrate additional conversion engines, email providers, or workflow automations as needed.