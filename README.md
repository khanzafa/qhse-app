## **Introduction**

**HCCA AI Vision Project : QHSE Monitoring & Object Detection Platform** is a project developed for the Human Resources Management System (HRMS) at PT. Salam Pacific Indonesia Lines. Its purpose is to manage employee safety reports, identification, and investigation processes. Additionally, the project features a chatbot to assist with managing system information and procedures.

## **Installation**

> Note: use `virtualenv` or `conda` for better practice. You can install it by using `pip install virtualenv` or `conda install -c conda-forge mamba`. This project developed using `Python 3.12.3`

Steps to install the project:

1. Clone this repository `git clone https://github.com/khanzafa/qhse-app.git` or click `Clone or Download` button and then click `Download ZIP`

2. Install requirements

   ```bash
   pip install -r requirements.txt
   ```

3. Set the environment variable. Make a new file `.env` and fill it with the following code:

   ```env
   # PostgreSQL database configuration for development
   DATABASE_URL=postgresql://postgres:YOUR_POSTGRES_PASSWORD@localhost/
   YOUR_DATABASE_NAME

   # Secret key for Flask, Generated from `sk.py`
   SECRET_KEY=YOUR_SECRET

   # Mail setup
   # Tutorial link https://mailtrap.io/blog/flask-send-email-gmail/
   MAIL_USERNAME='mail@gmail.com'
   MAIL_PASSWORD='password'
   ```

4. Prepare the database

   ```bash
   python flask db init
   python flask db migrate
   python flask upgrade
   ```

5. Run the project

   ```bash
    flask run
   ```
