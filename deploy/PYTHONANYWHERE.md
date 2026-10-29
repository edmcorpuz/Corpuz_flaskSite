# Lecture 07: PythonAnywhere deployment

Target: https://EzekielADDUCorpuz.pythonanywhere.com/

This is a **shared classroom CRUD demo**, not a private account-based task manager.
Visitors can edit the same items. Do not store sensitive information.

## Before switching

A free PythonAnywhere account has one web app. This replaces the current WSGI
application on that domain, but does not delete the Django project or database.
Record the current Web-tab virtualenv, source directory, working directory, and
static mappings so they can be restored if needed.

Check the **Python version shown on the Web tab**. Use that same version below.
This account's Web app uses **Python 3.13**; the commands below match it.
The local project uses Python 3.12, and the test suite passes on both versions.
PythonAnywhere supplies its own interpreters; do not install a new one there.

## PythonAnywhere Bash console

For the first clone:

```bash
cd ~
git clone https://github.com/edmcorpuz/Corpuz_flaskSite.git flask_site
cd ~/flask_site
PYTHON_VERSION=3.13 bash deploy/pythonanywhere_setup.sh
```

If the Web tab says another supported version, replace `3.13` with that version.
If `~/flask_site` already contains this repository, do not clone over it:

```bash
cd ~/flask_site
git status --short
# Stop and preserve any local changes before continuing.
git pull --ff-only origin main
PYTHON_VERSION=3.13 bash deploy/pythonanywhere_setup.sh
```

The script uses `mkvirtualenv` / `workon flaskENV`, installs requirements, runs
tests, creates a persistent secret outside Git, and backs up the old WSGI file
before replacing it. It aborts if the existing Flask environment uses the wrong
Python version. The Django virtualenv is never modified.

## Web tab (required)

Use your exact PythonAnywhere username/capitalization for filesystem paths.
For this account:

| Setting | Value |
| --- | --- |
| Source code | `/home/EzekielADDUCorpuz/flask_site` |
| Working directory | `/home/EzekielADDUCorpuz/flask_site` |
| Virtualenv | `/home/EzekielADDUCorpuz/.virtualenvs/flaskENV` |
| Static URL | `/static/` |
| Static directory | `/home/EzekielADDUCorpuz/flask_site/static` |

Update an existing Django `/static/` mapping instead of creating a duplicate.
The setup script prints paths based on your actual home directory; prefer those
if your account's spelling differs. Enable **Force HTTPS** (the production session
cookie is HTTPS-only). Click **Reload** after changing the settings.

Do not run `flask run` in a console to host the site. PythonAnywhere imports
`app as application` from the Web tab's WSGI file.

## Verify before submitting

- `/`: styled workspace, empty state or existing items.
- Create an item, edit it, search for it, cancel a deletion, then confirm deletion.
- `/hello` and `/hello/Ezekiel`: template-based greeting.
- `/static/css/test.css`: returns CSS, not an old Django 404.
- Check on a narrow/mobile viewport.

Submit **https://EzekielADDUCorpuz.pythonanywhere.com/** only after those checks pass.

If an error appears, open the Web tab's error log. Check the Python version,
virtualenv, WSGI path, and requirements. A blank or old page means the WSGI
configuration or reload is still wrong.

## Updates

```bash
cd ~/flask_site
git pull --ff-only origin main
workon flaskENV
python -m pip install -r requirements.txt
```

Then click **Reload**. The persistent secret and SQLite data survive pulls/reloads.
Only rerun the setup script if the WSGI configuration needs reinstalling.

## Rollback

The setup script prints the backup path under
`~/.config/flask_site/backups/`. Copy that specific backup back to the WSGI
filename printed by the script, restore the previous Web-tab settings you recorded,
and click Reload. Do not copy a backup into the public Git repository.
