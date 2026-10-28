# InternShield AI — Login-enabled version

## What changed
- Added email/password registration and login using Supabase Auth.
- Passwords are handled by Supabase Auth, not stored in this app's files.
- Review history is stored in Supabase and queried by the signed-in user.
- Added logout.
- Kept the existing InternShield offer analysis and Groq chat.

## Local setup
1. Install Python 3.10+ (or use the Python version you already use for this project).
2. Create and activate a virtual environment.
3. Install dependencies: `pip install -r requirements.txt`
4. Create a `.env` file based on `.env.example`.
5. In Supabase, create a project and copy its project URL and publishable/anon key.
6. Run `supabase_setup.sql` in Supabase SQL Editor.
7. In Supabase Authentication settings, configure email confirmation as you prefer.
8. Add your Groq API key to `.env`.
9. Run: `streamlit run app.py`

## Deploy to Streamlit Community Cloud
1. Push these project files to a GitHub repository. Do not upload `.env`.
2. Create an app at https://share.streamlit.io/ and select the repository and `app.py`.
3. In Streamlit app Settings → Secrets, add:
   ```
   GROQ_API_KEY = "your-groq-api-key"
   GROQ_MODEL = "openai/gpt-oss-20b"
   SUPABASE_URL = "https://your-project.supabase.co"
   SUPABASE_ANON_KEY = "your-supabase-publishable-or-anon-key"
   ```
4. Deploy, then test registration, email confirmation if enabled, login, saving reviews, and logout.

## Important
- Use the Supabase publishable/anon key in this app, never the service-role key.
- Do not commit `.env` or real API keys.
- This code has not been connected to your Supabase project or live-deployed yet.
