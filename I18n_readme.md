# Internationalization (i18n) Guide

## Overview
The Xsens Sensor Data Collection application supports bilingual operation:
- **Chinese (中文)** - Default language
- **English** - Secondary language

## Quick Start

### 1. Install Dependencies
```bash
pip install flask-babel
```

### 2. Compile Translations
```bash
# Option 1: Using Python script (cross-platform)
python compile_translations.py

# Option 2: Using bash script (Linux/Mac)
bash compile_translations.sh
```

### 3. Run the Application
```bash
python app.py
```

The application will start with Chinese as the default language. Users can switch to English using the language selector in the navigation bar.

## Language Switching

### In the Web Interface
1. Click the language dropdown in the top-right corner of the navigation bar
2. Select your preferred language:
   - **中文 (Chinese)** 
   - **English**
3. The page will reload with the selected language

### Programmatically
```python
from flask import session
session['language'] = 'zh'  # Chinese
session['language'] = 'en'  # English
```

## File Structure

```
.
├── app.py                              # Flask app with Babel configuration
├── babel.cfg                           # Babel configuration
├── compile_translations.py             # Python script to compile translations
├── compile_translations.sh             # Bash script to compile translations
│
├── translations/                       # Translation files directory
│   ├── zh/                            # Chinese translations
│   │   └── LC_MESSAGES/
│   │       ├── messages.po            # Chinese translation source
│   │       └── messages.mo            # Compiled Chinese translations
│   │
│   └── en/                            # English translations
│       └── LC_MESSAGES/
│           ├── messages.po            # English translation source
│           └── messages.mo            # Compiled English translations
│
└── templates/                         # HTML templates with translations
    ├── base.html                      # Base template with language switcher
    ├── index.html
    ├── measure.html
    └── history.html
```

## Adding New Translations

### 1. Update Translation Files

Edit the `.po` files:
- **Chinese**: `translations/zh/LC_MESSAGES/messages.po`
- **English**: `translations/en/LC_MESSAGES/messages.po`

Format:
```po
msgid "English text"
msgstr "中文文本"
```

### 2. Compile Translations

After editing `.po` files, compile them:
```bash
python compile_translations.py
```

This creates `.mo` files which Flask-Babel uses at runtime.

### 3. Use Translations in Templates

In Jinja2 templates:
```html
<!-- Simple translation -->
<h1>{{ _('Home') }}</h1>

<!-- Translation with variables -->
<p>{{ _('Welcome, %(name)s!', name=user.name) }}</p>

<!-- Translation in attributes -->
<button title="{{ _('Click here') }}">{{ _('Submit') }}</button>
```

### 4. Use Translations in Python Code

In Flask routes/functions:
```python
from flask_babel import gettext

# Simple translation
message = gettext('Measurement complete')

# Translation with variables
message = gettext('Found %(count)d records', count=10)
```

## Configuration

### Default Language
Set in `app.py`:
```python
app.config['BABEL_DEFAULT_LOCALE'] = 'zh'  # Default to Chinese
```

### Supported Languages
Currently supported:
- `zh` - Chinese (中文)
- `en` - English

To add more languages:
1. Create new directory: `translations/{lang_code}/LC_MESSAGES/`
2. Create `messages.po` file
3. Update `compile_translations.py`
4. Add to language switcher in `base.html`

## Translation Coverage

### Fully Translated Sections:
- ✅ Navigation menu
- ✅ Main dashboard
- ✅ Measurement page
- ✅ Historical data page
- ✅ Gyro bias calibration modal
- ✅ Status messages
- ✅ Form labels and buttons
- ✅ Error messages

### Not Translated:
- ❌ Console output (technical logs)
- ❌ File names
- ❌ Database field names
- ❌ API responses (JSON)

## Troubleshooting

### Translations Not Showing
1. **Check `.mo` files exist**:
   ```bash
   ls translations/zh/LC_MESSAGES/messages.mo
   ls translations/en/LC_MESSAGES/messages.mo
   ```

2. **Recompile translations**:
   ```bash
   python compile_translations.py
   ```

3. **Clear browser cache and reload**

4. **Check language is set**:
   ```python
   from flask import session
   print(session.get('language'))  # Should be 'zh' or 'en'
   ```

### Language Not Switching
1. **Check session is enabled**:
   - Ensure `SECRET_KEY` is set in `app.py`
   - Browser cookies must be enabled

2. **Check JavaScript console for errors**:
   - Open browser DevTools (F12)
   - Look for errors in Console tab

3. **Verify API endpoint works**:
   ```bash
   curl -X POST http://localhost:5000/api/set_language \
     -H "Content-Type: application/json" \
     -d '{"language":"en"}'
   ```

## Development Workflow

### 1. Extract New Strings
```bash
pybabel extract -F babel.cfg -o messages.pot .
```

### 2. Update Existing Translations
```bash
pybabel update -i messages.pot -d translations
```

### 3. Edit Translation Files
Edit `.po` files in `translations/{lang}/LC_MESSAGES/`

### 4. Compile Translations
```bash
python compile_translations.py
```

### 5. Test
Restart the Flask app and test both languages

## Best Practices

1. **Use Translation Keys**: Always use English text as `msgid`
   ```html
   <!-- Good -->
   {{ _('Start Measurement') }}
   
   <!-- Bad -->
   {{ _('开始测量') }}
   ```

2. **Avoid Hardcoded Text**: Don't put user-facing text directly in templates
   ```html
   <!-- Good -->
   <h1>{{ _('Welcome') }}</h1>
   
   <!-- Bad -->
   <h1>Welcome</h1>
   ```

3. **Context for Ambiguous Words**: Add comments for translators
   ```po
   # Button label for submitting a form
   msgid "Submit"
   msgstr "提交"
   
   # Verb meaning to give in or surrender
   msgid "Submit"
   msgstr "屈服"
   ```

4. **Test Both Languages**: Always test the application in both languages

5. **Keep Translations Short**: UI space is limited, especially for buttons

## API Integration

The language preference is stored in the session and persists across page loads.

### JavaScript Integration
```javascript
// Get current language
const lang = document.documentElement.lang;  // 'zh' or 'en'

// Change language via API
fetch('/api/set_language', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ language: 'en' })
})
.then(response => response.json())
.then(data => {
    if (data.success) {
        location.reload();  // Reload to apply new language
    }
});
```

## License
This internationalization implementation is part of the Xsens Sensor Data Collection System.