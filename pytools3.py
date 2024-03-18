from flask import Flask, request, render_template, redirect, url_for, flash, jsonify, send_from_directory, session
import pandas as pd
from fuzzywuzzy import process
from werkzeug.utils import secure_filename
import json
import os
import re
from google.cloud import bigquery

app = Flask(__name__)

app.secret_key = 'your_secret_key'

# Create Index Page
@app.route('/')
def index():
	return render_template('index.html')

# Create Index Page
@app.route('/about')
def about():
	return render_template('about.html')

# Create Keyword Page
@app.route('/key_tool')
def key_tool():
	return render_template('key_tool.html')


#Create Custom Error Code Page

# This Page Doesnt Exist
@app.errorhandler(404)
def page_not_found(e):
	return render_template('404.html'), 404

# Internal Server Error
@app.errorhandler(500)
def page_not_found(e):
	return render_template('500.html'), 500

#Brand Filter
@app.route('/brand_filter', methods=['GET', 'POST'])
def brand_filter():
    results = []  # This will store tuples of (keyword, "Brand"/"Non-Brand")
    if request.method == 'POST':
        list1 = request.form['list1'].lower().split('\n')
        list2 = set(request.form['list2'].lower().split('\n'))  # Convert list2 to set for faster lookups
        for phrase in list1:
            # Check if any brand is in the phrase, mark as 'Brand' if found, else 'Non-Brand'
            match_status = 'Non-Brand'
            for brand in list2:
                if brand in phrase:
                    match_status = 'Brand'
                    break  # Stop searching once a brand is found
            results.append((phrase, match_status))

    return render_template('brand_filter.html', results=results)

# Start code for BigQuery Upload Functionality

# Set Google Cloud credentials and project ID
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'semrush-test-417203-50a0755e0493.json'
client = bigquery.Client()

@app.route('/data_upload')
def data_upload():
    return render_template('data_upload.html')

@app.route('/data_upload/uploader', methods=['POST'])
def data_upload_uploader():
    if request.method == 'POST':
        f = request.files['file']
        df = pd.read_csv(f)
        
        # Ensure there's a date column in df, add or convert here if necessary

        # Clean up column names to meet BigQuery requirements
        df.columns = [re.sub(r'[^a-zA-Z0-9_]', '_', col) for col in df.columns]

        dataset_id = 'semrush_data_one'
        table_id = 'your_table_id'
        table_ref = f"{client.project}.{dataset_id}.{table_id}"
        
        job_config = bigquery.LoadJobConfig()
        job_config.write_disposition = bigquery.WriteDisposition.WRITE_APPEND  # Append to the table
        job_config.autodetect = True  # Auto-detect the schema
        
        job = client.load_table_from_dataframe(df, table_ref, job_config=job_config)
        job.result()  # Wait for the job to complete
        
        return 'File uploaded and data appended to BigQuery successfully'


# Connecting to BigQuery, a form to input the json connect file, and forms to connect to the right dataset and table
# Directory for storing uploaded credentials
# Ensure this directory exists and is not publicly accessible
credentials_dir = '/credentials'
os.makedirs(credentials_dir, exist_ok=True)

@app.route('/connect', methods=['GET', 'POST'])
def connect():
    if request.method == 'POST':
        if 'credentials_file' in request.files:
            file = request.files['credentials_file']
            if file and file.filename:
                filename = secure_filename(file.filename)
                filepath = os.path.join(credentials_dir, filename)
                file.save(filepath)
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = filepath
                flash('Google Cloud credentials set successfully.', 'success')
            else:
                flash('No credentials file provided.', 'error')
        else:
            dataset_id = request.form.get('dataset_id')
            table_id = request.form.get('table_id')
            if dataset_id and table_id:
                try:
                    client = bigquery.Client()
                    dataset_ref = client.dataset(dataset_id)
                    table_ref = dataset_ref.table(table_id)
                    # Attempt to fetch the table (will raise NotFound if table doesn't exist)
                    client.get_table(table_ref)
                    flash(f'Connected to dataset: {dataset_id}, and table ID: {table_id}.', 'success')
                except Exception as e:
                    flash(f'Error connecting to dataset: {dataset_id}, and table ID: {table_id}. Details: {str(e)}', 'error')
            else:
                flash('Dataset ID and Table ID must be provided.', 'error')

    return render_template('connect.html')


#Display the data that we are connected to
@app.route('/display_data', methods=['POST'])
def display_data():
    # Assume dataset_id and table_id are globally available or retrieve them appropriately
    global dataset_id, table_id
    table_ref = f"{client.project}.{dataset_id}.{table_id}"

    # Query to select the first 10 rows of the table
    query = f"SELECT * FROM `{table_ref}` LIMIT 10"
    query_job = client.query(query)  # Make an API request

    # Convert the query result to a pandas DataFrame
    df = query_job.to_dataframe()

    # Convert DataFrame to HTML table for rendering
    df_html = df.to_html(classes='data', index=False)

    # Pass the HTML table to the template
    return render_template('display_data.html', table=df_html)


if __name__ == '__main__':
    app.run(debug=True)