SOCRATIC BENCH — AI/SOFTWARE TERMINOLOGY TUTOR
================================================

OVERVIEW
--------
Socratic Bench is a Flask-based web application that teaches AI and software
engineering terminology through live elicitation rather than direct
explanation. When a user asks about a term (e.g. "What is a token?"), the
application first asks the user what they already understand about it. Based
on the user's response, it affirms correct understanding, corrects gaps or
misconceptions, provides a precise explanation with an example, and follows
up with a question to reinforce learning.

The application uses Groq's free LLM API (Llama 3.3 70B model) for
generating responses.


REQUIREMENTS
------------
- Python 3.10 or newer
- A free Groq API key
- A code editor (VS Code recommended)


STEP 1: VERIFY PYTHON INSTALLATION
-----------------------------------
Open a terminal and run:

    python --version

If a version number is displayed (e.g. Python 3.12.4), proceed to Step 2.

If you see an error such as "Python was not found; run without arguments to
install from the Microsoft Store," Python is not properly installed:

    1. Download the installer from https://www.python.org/downloads/
    2. Run it and check "Add python.exe to PATH" on the first screen
    3. Complete the installation
    4. Close and reopen your terminal
    5. Run "python --version" again to confirm


STEP 2: CREATE A VIRTUAL ENVIRONMENT
-------------------------------------
From the project folder, run:

    python -m venv venv

Activate it:

    Windows PowerShell:   venv\Scripts\Activate.ps1
    Windows cmd.exe:      venv\Scripts\activate.bat
    macOS / Linux:        source venv/bin/activate

Once activated, your terminal prompt will begin with "(venv)".

If PowerShell blocks the activation script with a "running scripts is
disabled" error, run this once and try again:

    Set-ExecutionPolicy -Scope CurrentUser RemoteSigned


STEP 3: INSTALL REQUIRED MODULES
----------------------------------
With the virtual environment active, run:

    pip install -r requirements.txt

This installs three packages: Flask, requests, and python-dotenv.

If requirements.txt is unavailable, install manually:

    pip install Flask requests python-dotenv


STEP 4: OBTAIN A FREE GROQ API KEY
------------------------------------
1. Visit https://console.groq.com/keys
2. Sign up for a free account and log in
3. Click "Create API Key" and copy the generated key


STEP 5: CONFIGURE ENVIRONMENT VARIABLES
------------------------------------------
1. Duplicate the file ".env.example" and rename the copy to ".env"
2. Open ".env" and enter your key:

    GROQ_API_KEY=your_actual_key_here
    GROQ_MODEL=llama-3.3-70b-versatile
    FLASK_SECRET_KEY=any_random_string_here

3. Save the file. ".env" is excluded from version control via .gitignore
   and will not be pushed to GitHub.


STEP 6: RUN THE APPLICATION
------------------------------
With the virtual environment active, run:

    python app.py

Expected output:

    * Running on http://127.0.0.1:5000

Open this address in a browser to use the application.


USAGE
-----
Type a question such as "What is a token?" and submit it. The tutor will ask
what you already understand about the term before giving an answer. Reply
with your own understanding to see the correction and progress tracker
("Concept Ledger") update on the interface.


PUSHING TO GITHUB
------------------
    git init
    git add .
    git commit -m "Socratic AI tutor application"
    git branch -M main
    git remote add origin https://github.com/<your-username>/<repo-name>.git
    git push -u origin main

After pushing, add a collaborator from the repository's GitHub page:
Settings > Collaborators > Add people > enter "gopi-nath-sr" > send invite.
