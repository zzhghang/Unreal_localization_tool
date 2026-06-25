#!/usr/bin/env python3
"""
Translation Server using deep-translator
A simple Flask server that provides Google Translate via deep-translator library
"""

# Install dependencies first
import subprocess
import sys

try:
    from flask import Flask, request, jsonify
    from flask_cors import CORS
    from deep_translator import GoogleTranslator
except ImportError:
    print("Installing dependencies...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "flask", "flask-cors", "deep-translator"])
    from flask import Flask, request, jsonify
    from flask_cors import CORS
    from deep_translator import GoogleTranslator

import json
import re

app = Flask(__name__)
CORS(app)  # Enable CORS for all origins

# Language mapping (our code -> Google code)
LANG_MAPPING = {
    'zh-CN': 'zh-CN',
    'ja': 'ja',
    'ko': 'ko',
    'fr': 'fr',
    'de': 'de',
    'es': 'es',
    'ru': 'ru',
    'pt': 'pt',
    'it': 'it',
    'pl': 'pl',
    'tr': 'tr',
    'nl': 'nl',
}

# Patterns for protected content
PROTECTED_PATTERNS = [
    (r'(<[^>]*>)', 'TAG'),               # HTML/XML tags: <warning>, </warning>, <>, </>
    (r'(\\n\\n|\\n|\\t)', 'ESC'),       # Escape sequences
    (r'(\{\{[^}]+\}\})', 'VAR'),        # Variables: {{var}}
    (r'(%[sd]|[%\d]+\$[sd])', 'FMT'),   # Format specifiers: %s, %d
]


def protect_tags(text):
    """Replace protected patterns with placeholders"""
    placeholders = []
    protected_text = text
    
    for pattern, ptype in PROTECTED_PATTERNS:
        def replace_match(match):
            placeholder = f"<<<{ptype}_{len(placeholders)}>>>"
            placeholders.append({
                'placeholder': placeholder,
                'content': match.group(0),
                'type': ptype
            })
            return placeholder
        
        protected_text = re.sub(pattern, replace_match, protected_text)
    
    return protected_text, placeholders


def restore_tags(translated_text, placeholders):
    """Restore protected content from placeholders"""
    result = translated_text
    
    # Sort by placeholder index in descending order to avoid replacement issues
    sorted_placeholders = sorted(placeholders, key=lambda x: int(x['placeholder'].split('_')[1].replace('>>>', '')), reverse=True)
    
    for ph in sorted_placeholders:
        placeholder = ph['placeholder']
        content = ph['content']
        
        # Try exact match first
        if placeholder in result:
            result = result.replace(placeholder, content)
        else:
            # Handle case where Google Translate might have changed the placeholder
            # Try case-insensitive match
            import re as regex
            pattern = regex.escape(placeholder).replace(r'\<\<\<', r'<<<').replace(r'\_\d+\>', r'_\d+>>>')
            # More flexible pattern to match variations like <<<TAG_0>>> or <<<tag_0>>>
            flexible_pattern = r'<<<[^>]*_' + regex.escape(placeholder.split('_')[1].replace('>>>', '')) + r'>>>'
            result = regex.sub(flexible_pattern, content, result, flags=regex.IGNORECASE)
    
    return result


@app.route('/translate', methods=['POST'])
def translate():
    """Translate text to target language"""
    try:
        data = request.get_json()
        texts = data.get('texts', [])
        target_lang = data.get('target_lang', 'zh-CN')
        
        if not texts:
            return jsonify({'error': 'No texts provided'}), 400
        
        # Map language code
        google_lang = LANG_MAPPING.get(target_lang, target_lang)
        
        # Create translator
        translator = GoogleTranslator(source='auto', target=google_lang)
        
        # Translate each text
        results = []
        for text in texts:
            if not text or not text.strip():
                results.append(text)
                continue
            
            # Protect tags
            protected_text, placeholders = protect_tags(text)
            
            # Skip if only protected content (no actual text to translate)
            remaining_text = protected_text.strip()
            # Remove all placeholders to check if there's real content
            for ph in placeholders:
                remaining_text = remaining_text.replace(ph['placeholder'], '')
            remaining_text = remaining_text.strip()
            
            if not remaining_text:
                results.append(text)
                continue
            
            try:
                # Translate
                translated = translator.translate(protected_text)
                
                # Restore tags
                restored = restore_tags(translated, placeholders)
                results.append(restored)
                
            except Exception as e:
                print(f"Translation error for '{text}': {e}")
                results.append(text)  # Fallback to original
        
        return jsonify({
            'translations': results,
            'target_lang': target_lang
        })
        
    except Exception as e:
        print(f"Server error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/languages', methods=['GET'])
def get_languages():
    """Get supported languages"""
    return jsonify({
        'languages': LANG_MAPPING
    })


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    print("=" * 50)
    print("Translation Server")
    print("=" * 50)
    print("\nStarting server on http://localhost:5000")
    print("Press Ctrl+C to stop\n")
    
    app.run(host='0.0.0.0', port=5000, debug=False)
