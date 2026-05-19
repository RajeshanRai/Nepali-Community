# Deploying nepali_community to PythonAnywhere

This guide covers the deployment steps for `rajeshan.pythonanywhere.com`.

## 1. Upload the project to PythonAnywhere

1. Create an account at https://www.pythonanywhere.com/ and log in.
2. In the **Files** tab, upload your project directory or clone from GitHub.
   - Recommended: clone from a Git repository into `/home/rajeshan/nepali_community`.
   - Alternative: upload a ZIP, extract it into `/home/rajeshan/nepali_community`.

## 2. Create and activate a virtual environment

In the PythonAnywhere **Consoles** tab, start a Bash console and run:

```bash
python3.12 -m venv ~/venvs/rai_community
source ~/venvs/rai_community/bin/activate
python -m pip install --upgrade pip
python -m pip install -r /home/rajeshan/nepali_community/requirements.txt
```

> If Python 3.12 is unavailable, use the highest supported Python 3 version.

## 3. Configure environment variables

This project expects several environment variables for production.

### Use a `.env` file in the project root
Create `/home/rajeshan/nepali_community/.env` with values like:

```env
SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=rajeshan.pythonanywhere.com
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=you@example.com
EMAIL_HOST_PASSWORD=supersecret
DEFAULT_FROM_EMAIL=you@example.com
COMMUNITY_NAME=Nepali Community of Vancouver
ANNUAL_DONATION_GOAL=60000
```

### Alternative: set variables in the WSGI file
If you do not want a `.env` file, set values inside the WSGI file before Django loads.

## 4. Configure the Web app on PythonAnywhere

1. Go to the **Web** tab.
2. Create a new web app or edit the existing one.
3. Select the same Python version as your virtualenv.
4. Set the WSGI configuration file to point to `/home/rajeshan/nepali_community/nepali_community/wsgi.py`.
5. In the **Virtualenv** field, enter `/home/rajeshan/venvs/rai_community`.

## 5. Configure static and media file mappings

In the **Static files** section, add:

- URL `/static/` → Directory `/home/rajeshan/nepali_community/staticfiles`
- URL `/media/` → Directory `/home/rajeshan/nepali_community/media`

## 6. Collect static files

In Bash (with the virtualenv active):

```bash
cd /home/rajeshan/nepali_community
source ~/venvs/rai_community/bin/activate
python manage.py collectstatic --noinput
```

## 7. Initialize or migrate the database

If this is a fresh deploy:

```bash
python manage.py migrate
python manage.py createsuperuser
```

If you need to preserve existing data, upload `db.sqlite3` to `/home/rajeshan/nepali_community` instead of running migrations on an empty database.

## 8. Reload the web app

In PythonAnywhere, click **Reload** on the Web tab.

## 9. Verify the deployment

Visit:

- https://rajeshan.pythonanywhere.com
- https://rajeshan.pythonanywhere.com/admin/

Check that static assets and media files are served correctly.

## Notes

- `nepali_community/settings.py` has been updated to use `DEBUG=False` by default and read `ALLOWED_HOSTS` from the environment.
- `nepali_community/wsgi.py` has been updated to use a generic project path so it works both locally and on PythonAnywhere.
- `requirements.txt` has been converted to UTF-8 so `pip install -r requirements.txt` works properly.
