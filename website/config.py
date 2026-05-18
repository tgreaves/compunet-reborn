import os

COMPUNET_API_URL = os.environ.get('COMPUNET_API_URL', 'http://localhost:6403')
COMPUNET_API_KEY = os.environ.get('COMPUNET_API_KEY', '')
POSTMARK_API_KEY = os.environ.get('POSTMARK_API_KEY', '')
SECRET_KEY = os.environ.get('WEBSITE_SECRET_KEY', 'dev-secret-change-me')
BASE_URL = os.environ.get('WEBSITE_BASE_URL', 'http://localhost:5000')
PENDING_FILE = os.environ.get('WEBSITE_PENDING_FILE',
                              os.path.join(os.path.dirname(__file__), 'pending.json'))
