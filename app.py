#!/usr/bin/env python3
"""
AI PDF Agent - Web Interface
A modern web interface for the PDF conversion agent with update notifications
"""

import os
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename
import threading
import time
import openai
from dotenv import load_dotenv

from pdf_agent import PDFAgent

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

socketio = SocketIO(app, cors_allowed_origins="*")

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('output', exist_ok=True)

# Global variables for session management
sessions = {}
agent = PDFAgent()

# Initialize OpenAI from agent config
if agent.config.get('openai', {}).get('api_key'):
    openai.api_key = agent.config['openai']['api_key']
else:
    openai.api_key = os.getenv('OPENAI_API_KEY')

# Update notifications system
UPDATE_NOTIFICATIONS = [
    {
        "id": "v1.1.0", 
        "title": "Enhanced File Processing",
        "message": "Improved file upload and conversion processing with better error handling and status updates.",
        "type": "success",
        "date": "25-10-2025",
        "dismissible": True
    },
    {
        "id": "v1.0.0",
        "title": "Initial Release",
        "message": "Welcome to the AI PDF Agent! Convert LaTeX and Markdown files to PDF with advanced formatting options.",
        "type": "info",
        "date": "13-10-2025",
        "dismissible": False
    }
]

# Allowed file extensions
ALLOWED_EXTENSIONS = {'.md', '.markdown', '.tex', '.latex'}

# Academic journal templates and configurations
JOURNAL_TEMPLATES = {
    'ieee': {
        'name': 'IEEE Conference/Journal',
        'template': 'ieee-template.tex',
        'pandoc_options': ['--template', 'ieee-template.tex', '--csl', 'ieee.csl'],
        'description': 'IEEE format for conferences and journals'
    }
}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS

def get_session_id():
    """Generate a unique session ID"""
    return str(uuid.uuid4())

def get_session(session_id):
    """Get or create a session"""
    if session_id not in sessions:
        sessions[session_id] = {
            'id': session_id,
            'created_at': datetime.now(),
            'files': [],
            'status': 'active',
            'academic_analysis': {},
            'journal_recommendations': [],
            'dismissed_updates': []
        }
    return sessions[session_id]

def analyze_academic_content(content, file_type):
    """Use OpenAI to analyze academic content and provide recommendations"""
    try:
        if not openai.api_key:
            return {"error": "OpenAI API key not configured"}
        
        prompt = f"""
        Analyze this {file_type} academic document and provide:
        1. Document type (research paper, conference paper, journal article, etc.)
        2. Suggested journal templates (IEEE)
        3. Content structure analysis
        4. Missing elements (abstract, keywords, references, etc.)
        5. Formatting recommendations
        6. Academic writing improvements
        
        Content:
        {content[:4000]}  # Limit content to avoid token limits
        """
        
        client = openai.OpenAI(api_key=openai.api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert academic writing assistant specializing in journal formatting and academic publishing standards."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.3
        )
        
        return {
            "analysis": response.choices[0].message.content,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"OpenAI analysis error: {e}")
        return {"error": str(e)}

def get_journal_recommendations(content, file_type):
    """Get journal template recommendations based on content analysis"""
    try:
        if not openai.api_key:
            return {"error": "OpenAI API key not configured"}
        
        prompt = f"""
        Based on this {file_type} academic content, recommend the most suitable journal templates from:
        - IEEE (for computer science, engineering)
        
        Provide:
        1. Top 1 recommended template
        2. Reasoning for the recommendation
        3. Specific formatting requirements
        
        Content:
        {content}
        """
        
        client = openai.OpenAI(api_key=openai.api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert in academic publishing and journal formatting standards."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=800,
            temperature=0.3
        )
        
        return {
            "recommendations": response.choices[0].message.content,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Journal recommendation error: {e}")
        return {"error": str(e)}

def enhance_academic_content(content, file_type, journal_template):
    """Use OpenAI to enhance academic content for specific journal format"""
    try:
        if not openai.api_key:
            return {"error": "OpenAI API key not configured"}
        
        template_info = JOURNAL_TEMPLATES.get(journal_template, {})
        
        prompt = f"""
        Enhance this {file_type} academic content for {template_info.get('name', journal_template)} format:
        
        1. Ensure proper academic structure
        2. Add missing sections if needed (abstract, keywords, etc.)
        3. Improve academic writing style
        4. Ensure proper citation format
        5. Add appropriate LaTeX formatting for {journal_template}
        
        Current content:
        {content}
        
        Return the enhanced content in the same format ({file_type}).
        """
        
        client = openai.OpenAI(api_key=openai.api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": f"You are an expert academic writing assistant specializing in {template_info.get('name', journal_template)} formatting."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.3
        )
        
        return {
            "enhanced_content": response.choices[0].message.content,
            "template_used": journal_template,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Content enhancement error: {e}")
        return {"error": str(e)}

def refine_academic_writing(content, file_type, journal_style="formal"):
    """Use OpenAI to refine writing into formal, academic-journal style language"""
    try:
        if not openai.api_key:
            return {"error": "OpenAI API key not configured"}
        
        # Use the agent's refinement method
        agent_instance = PDFAgent()
        return agent_instance.refine_academic_writing(content, file_type, journal_style)
    
    except Exception as e:
        logger.error(f"Writing refinement error: {e}")
        return {"error": str(e)}

@app.route('/')
def index():
    """Main chat interface"""
    return render_template('index.html')

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Handle file uploads"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        session_id = request.form.get('session_id', get_session_id())
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Add to session
            session = get_session(session_id)
            session['files'].append({
                'filename': filename,
                'original_name': file.filename,
                'filepath': filepath,
                'uploaded_at': datetime.now().isoformat(),
                'status': 'uploaded'
            })
            
            return jsonify({
                'success': True,
                'filename': filename,
                'session_id': session_id,
                'message': f'File {file.filename} uploaded successfully'
            })
        else:
            return jsonify({'error': 'Invalid file type. Only .md, .markdown, .tex, .latex files are allowed'}), 400
    
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/convert', methods=['POST'])
def convert_file():
    """Convert uploaded file to PDF"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        filename = data.get('filename')
        options = data.get('options', {})
        
        if not session_id or not filename:
            return jsonify({'error': 'Session ID and filename required'}), 400
        
        session = get_session(session_id)
        file_info = None
        
        # Find the file in session
        for file in session['files']:
            if file['filename'] == filename:
                file_info = file
                break
        
        if not file_info:
            return jsonify({'error': 'File not found in session'}), 404
        
        # Update file status
        file_info['status'] = 'processing'
        
        # Start conversion in background
        thread = threading.Thread(
            target=process_conversion,
            args=(session_id, file_info, options)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Conversion started',
            'session_id': session_id
        })
    
    except Exception as e:
        logger.error(f"Conversion error: {e}")
        return jsonify({'error': str(e)}), 500

def process_conversion(session_id, file_info, options):
    """Process file conversion in background"""
    try:
        # Emit status update
        socketio.emit('conversion_status', {
            'session_id': session_id,
            'filename': file_info['filename'],
            'status': 'processing',
            'message': 'Starting conversion...'
        })
        
        # Convert file
        success = agent.process_file(
            file_info['filepath'],
            use_overleaf=options.get('use_overleaf', False),
            send_email=options.get('send_email', True),
            trigger_n8n=options.get('trigger_n8n', True)
        )
        
        if success:
            # Find the generated PDF
            output_dir = agent.config['output']['directory']
            pdf_files = list(Path(output_dir).glob('*.pdf'))
            latest_pdf = max(pdf_files, key=os.path.getctime) if pdf_files else None
            
            file_info['status'] = 'completed'
            file_info['pdf_path'] = str(latest_pdf) if latest_pdf else None
            file_info['completed_at'] = datetime.now().isoformat()
            
            socketio.emit('conversion_status', {
                'session_id': session_id,
                'filename': file_info['filename'],
                'status': 'completed',
                'message': 'Conversion completed successfully!',
                'pdf_path': str(latest_pdf) if latest_pdf else None
            })
        else:
            file_info['status'] = 'failed'
            file_info['error'] = 'Conversion failed'
            
            socketio.emit('conversion_status', {
                'session_id': session_id,
                'filename': file_info['filename'],
                'status': 'failed',
                'message': 'Conversion failed. Check logs for details.'
            })
    
    except Exception as e:
        logger.error(f"Background conversion error: {e}")
        file_info['status'] = 'failed'
        file_info['error'] = str(e)
        
        socketio.emit('conversion_status', {
            'session_id': session_id,
            'filename': file_info['filename'],
            'status': 'failed',
            'message': f'Conversion error: {str(e)}'
        })

@app.route('/api/download/<path:filename>')
def download_file(filename):
    """Download converted PDF file"""
    try:
        file_path = os.path.join('output', filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        logger.error(f"Download error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/session/<session_id>')
def get_session_info(session_id):
    """Get session information"""
    session = get_session(session_id)
    return jsonify(session)

@app.route('/api/updates')
def get_updates():
    """Get available updates"""
    return jsonify(UPDATE_NOTIFICATIONS)

@app.route('/api/updates/dismiss', methods=['POST'])
def dismiss_update():
    """Dismiss an update notification"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        update_id = data.get('update_id')
        
        if not session_id or not update_id:
            return jsonify({'error': 'Session ID and update ID required'}), 400
        
        session = get_session(session_id)
        if update_id not in session['dismissed_updates']:
            session['dismissed_updates'].append(update_id)
        
        return jsonify({'success': True})
    
    except Exception as e:
        logger.error(f"Update dismiss error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/config', methods=['GET', 'POST'])
def handle_config():
    """Get or update configuration"""
    if request.method == 'GET':
        return jsonify(agent.config)
    else:
        try:
            new_config = request.get_json()
            # Update agent config
            agent.config.update(new_config)
            # Save to file
            with open('config.json', 'w') as f:
                json.dump(agent.config, f, indent=4)
            return jsonify({'success': True, 'message': 'Configuration updated'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

@app.route('/api/analyze', methods=['POST'])
def analyze_content():
    """Analyze academic content using OpenAI"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        filename = data.get('filename')
        
        if not session_id or not filename:
            return jsonify({'error': 'Session ID and filename required'}), 400
        
        session = get_session(session_id)
        file_info = None
        
        # Find the file in session
        for file in session['files']:
            if file['filename'] == filename:
                file_info = file
                break
        
        if not file_info:
            return jsonify({'error': 'File not found in session'}), 404
        
        # Read file content
        with open(file_info['filepath'], 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Detect file type
        file_type = 'latex' if file_info['filepath'].endswith(('.tex', '.latex')) else 'markdown'
        
        # Analyze content
        analysis = analyze_academic_content(content, file_type)
        
        # Get journal recommendations
        recommendations = get_journal_recommendations(content, file_type)
        
        # Store analysis in session
        session['academic_analysis'][filename] = analysis
        session['journal_recommendations'] = recommendations
        
        return jsonify({
            'success': True,
            'analysis': analysis,
            'recommendations': recommendations
        })
    
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/enhance', methods=['POST'])
def enhance_content():
    """Enhance academic content for specific journal format"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        filename = data.get('filename')
        journal_template = data.get('journal_template', 'ieee')
        
        if not session_id or not filename:
            return jsonify({'error': 'Session ID and filename required'}), 400
        
        session = get_session(session_id)
        file_info = None
        
        # Find the file in session
        for file in session['files']:
            if file['filename'] == filename:
                file_info = file
                break
        
        if not file_info:
            return jsonify({'error': 'File not found in session'}), 404
        
        # Read file content
        with open(file_info['filepath'], 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Detect file type
        file_type = 'latex' if file_info['filepath'].endswith(('.tex', '.latex')) else 'markdown'
        
        # Enhance content
        enhancement = enhance_academic_content(content, file_type, journal_template)
        
        if 'error' in enhancement:
            return jsonify(enhancement), 500
        
        # Save enhanced content
        enhanced_filename = f"enhanced_{file_info['filename']}"
        enhanced_filepath = os.path.join(app.config['UPLOAD_FOLDER'], enhanced_filename)
        
        with open(enhanced_filepath, 'w', encoding='utf-8') as f:
            f.write(enhancement['enhanced_content'])
        
        # Add enhanced file to session
        session['files'].append({
            'filename': enhanced_filename,
            'original_name': f"Enhanced_{file_info['original_name']}",
            'filepath': enhanced_filepath,
            'uploaded_at': datetime.now().isoformat(),
            'status': 'uploaded',
            'enhanced_from': filename,
            'journal_template': journal_template
        })
        
        return jsonify({
            'success': True,
            'enhanced_filename': enhanced_filename,
            'enhancement': enhancement
        })
    
    except Exception as e:
        logger.error(f"Enhancement error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/templates', methods=['GET'])
def get_journal_templates():
    """Get available journal templates"""
    return jsonify(JOURNAL_TEMPLATES)

@app.route('/api/refine-writing', methods=['POST'])
def refine_writing():
    """Refine academic writing using OpenAI"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        filename = data.get('filename')
        journal_style = data.get('journal_style', 'formal')
        
        if not session_id or not filename:
            return jsonify({'error': 'Session ID and filename required'}), 400
        
        session = get_session(session_id)
        file_info = None
        
        # Find the file in session
        for file in session['files']:
            if file['filename'] == filename:
                file_info = file
                break
        
        if not file_info:
            return jsonify({'error': 'File not found in session'}), 404
        
        # Read file content
        with open(file_info['filepath'], 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Detect file type
        file_type = 'latex' if file_info['filepath'].endswith(('.tex', '.latex')) else 'markdown'
        
        # Refine writing
        refinement = refine_academic_writing(content, file_type, journal_style)
        
        if 'error' in refinement:
            return jsonify(refinement), 500
        
        # Check if refined content exists
        if 'refined_content' not in refinement or not refinement['refined_content']:
            return jsonify({'error': 'No refined content returned'}), 500
        
        # Save refined content
        refined_filename = f"refined_{file_info['filename']}"
        refined_filepath = os.path.join(app.config['UPLOAD_FOLDER'], refined_filename)
        
        with open(refined_filepath, 'w', encoding='utf-8') as f:
            f.write(refinement['refined_content'])
        
        # Add refined file to session
        session['files'].append({
            'filename': refined_filename,
            'original_name': f"Refined_{file_info['original_name']}",
            'filepath': refined_filepath,
            'uploaded_at': datetime.now().isoformat(),
            'status': 'uploaded',
            'refined_from': filename,
            'journal_style': journal_style
        })
        
        return jsonify({
            'success': True,
            'refined_filename': refined_filename,
            'refinement': refinement
        })
    
    except Exception as e:
        logger.error(f"Writing refinement error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/convert-with-refinement', methods=['POST'])
def convert_with_refinement():
    """Convert file to PDF with writing refinement"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        filename = data.get('filename')
        journal_style = data.get('journal_style', 'formal')
        options = data.get('options', {})
        
        if not session_id or not filename:
            return jsonify({'error': 'Session ID and filename required'}), 400
        
        session = get_session(session_id)
        file_info = None
        
        # Find the file in session
        for file in session['files']:
            if file['filename'] == filename:
                file_info = file
                break
        
        if not file_info:
            return jsonify({'error': 'File not found in session'}), 404
        
        # Update file status
        file_info['status'] = 'processing'
        
        # Start refinement and conversion in background
        thread = threading.Thread(
            target=process_refinement_conversion,
            args=(session_id, file_info, journal_style, options)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Refinement and conversion started',
            'session_id': session_id,
            'journal_style': journal_style
        })
    
    except Exception as e:
        logger.error(f"Refinement conversion error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/convert-academic', methods=['POST'])
def convert_academic():
    """Convert file to PDF with academic journal formatting"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        filename = data.get('filename')
        journal_template = data.get('journal_template', 'ieee')
        options = data.get('options', {})
        
        if not session_id or not filename:
            return jsonify({'error': 'Session ID and filename required'}), 400
        
        session = get_session(session_id)
        file_info = None
        
        # Find the file in session
        for file in session['files']:
            if file['filename'] == filename:
                file_info = file
                break
        
        if not file_info:
            return jsonify({'error': 'File not found in session'}), 404
        
        # Update file status
        file_info['status'] = 'processing'
        
        # Start academic conversion in background
        thread = threading.Thread(
            target=process_academic_conversion,
            args=(session_id, file_info, journal_template, options)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Academic conversion started',
            'session_id': session_id,
            'journal_template': journal_template
        })
    
    except Exception as e:
        logger.error(f"Academic conversion error: {e}")
        return jsonify({'error': str(e)}), 500

def process_refinement_conversion(session_id, file_info, journal_style, options):
    """Process file with writing refinement and conversion in background"""
    try:
        # Emit status update
        socketio.emit('conversion_status', {
            'session_id': session_id,
            'filename': file_info['filename'],
            'status': 'processing',
            'message': f'Refining writing with {journal_style} style...'
        })
        
        # Process file with refinement
        success = agent.process_file_with_refinement(
            file_info['filepath'],
            journal_style=journal_style,
            use_overleaf=options.get('use_overleaf', False),
            send_email=options.get('send_email', True),
            trigger_n8n=options.get('trigger_n8n', True),
            email_recipient=options.get('email_recipient', None)
        )
        
        if success:
            # Find the generated PDF
            output_dir = agent.config['output']['directory']
            pdf_files = list(Path(output_dir).glob('*.pdf'))
            latest_pdf = max(pdf_files, key=os.path.getctime) if pdf_files else None
            
            file_info['status'] = 'completed'
            file_info['pdf_path'] = str(latest_pdf) if latest_pdf else None
            file_info['completed_at'] = datetime.now().isoformat()
            file_info['journal_style'] = journal_style
            
            socketio.emit('conversion_status', {
                'session_id': session_id,
                'filename': file_info['filename'],
                'status': 'completed',
                'message': f'Successfully refined and converted with {journal_style} style!',
                'pdf_path': str(latest_pdf) if latest_pdf else None,
                'journal_style': journal_style
            })
        else:
            file_info['status'] = 'failed'
            file_info['error'] = 'Refinement and conversion failed'
            
            socketio.emit('conversion_status', {
                'session_id': session_id,
                'filename': file_info['filename'],
                'status': 'failed',
                'message': 'Refinement and conversion failed. Check logs for details.'
            })
    
    except Exception as e:
        logger.error(f"Background refinement conversion error: {e}")
        file_info['status'] = 'failed'
        file_info['error'] = str(e)
        
        socketio.emit('conversion_status', {
            'session_id': session_id,
            'filename': file_info['filename'],
            'status': 'failed',
            'message': f'Refinement conversion error: {str(e)}'
        })

def process_academic_conversion(session_id, file_info, journal_template, options):
    """Process academic file conversion in background"""
    try:
        # Emit status update
        socketio.emit('conversion_status', {
            'session_id': session_id,
            'filename': file_info['filename'],
            'status': 'processing',
            'message': f'Converting to {journal_template.upper()} format...'
        })
        
        # Get template configuration
        template_config = JOURNAL_TEMPLATES.get(journal_template, {})
        
        # Convert file with academic formatting (using Pandoc only)
        success = agent.process_file(
            file_info['filepath'],
            use_overleaf=False,  # Disable Overleaf since API is not available
            send_email=options.get('send_email', True),
            trigger_n8n=options.get('trigger_n8n', True)
        )
        
        if success:
            # Find the generated PDF
            output_dir = agent.config['output']['directory']
            pdf_files = list(Path(output_dir).glob('*.pdf'))
            latest_pdf = max(pdf_files, key=os.path.getctime) if pdf_files else None
            
            file_info['status'] = 'completed'
            file_info['pdf_path'] = str(latest_pdf) if latest_pdf else None
            file_info['completed_at'] = datetime.now().isoformat()
            file_info['journal_template'] = journal_template
            
            socketio.emit('conversion_status', {
                'session_id': session_id,
                'filename': file_info['filename'],
                'status': 'completed',
                'message': f'Successfully converted to {journal_template.upper()} format!',
                'pdf_path': str(latest_pdf) if latest_pdf else None,
                'journal_template': journal_template
            })
        else:
            file_info['status'] = 'failed'
            file_info['error'] = 'Academic conversion failed'
            
            socketio.emit('conversion_status', {
                'session_id': session_id,
                'filename': file_info['filename'],
                'status': 'failed',
                'message': 'Academic conversion failed. Check logs for details.'
            })
    
    except Exception as e:
        logger.error(f"Background academic conversion error: {e}")
        file_info['status'] = 'failed'
        file_info['error'] = str(e)
        
        socketio.emit('conversion_status', {
            'session_id': session_id,
            'filename': file_info['filename'],
            'status': 'failed',
            'message': f'Academic conversion error: {str(e)}'
        })

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info('Client connected')
    emit('connected', {'message': 'Connected to PDF Agent'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info('Client disconnected')

if __name__ == '__main__':
    logger.info("Starting PDF Agent Web Interface...")
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
