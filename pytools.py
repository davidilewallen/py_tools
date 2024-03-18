from flask import Flask, request, render_template, redirect, url_for, flash, jsonify, send_from_directory, session
import pandas as pd
from fuzzywuzzy import process
from werkzeug.utils import secure_filename
import json
import os
import re
from google.cloud import bigquery


app = Flask(__name__)



app.secret_key = 'your_very_secret_key'

#app.secret_key = 'your_secret_key'

# Create Index Page
@app.route('/')
def index():
	return render_template('index.html')

# Create Index Page
@app.route('/about')
def about():
	return render_template('about.html')


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




# Connecting to BigQuery, a form to input the json connect file, and forms to connect to the right dataset and table
# Directory for storing uploaded credentials
# Ensure this directory exists and is not publicly accessible
credentials_dir = '/tmp/credentials'
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
                session['dataset_id'] = dataset_id
                session['table_id'] = table_id
                try:
                    client = bigquery.Client()
                    # Fetch the project name from the BigQuery client
                    session['project_name'] = client.project
                    dataset_ref = client.dataset(dataset_id)
                    table_ref = dataset_ref.table(table_id)
                    client.get_table(table_ref)  # This will raise NotFound if the table doesn't exist
                    flash(f'Connected to BigQuery project: \'{client.project}\', Dataset ID: \'{dataset_id}\', and Table: \'{table_id}\'.', 'success')
                except Exception as e:
                    flash(f'Error connecting to dataset: {dataset_id}, and table ID: {table_id}. Details: {str(e)}', 'error')
            else:
                flash('Dataset ID and Table ID must be provided.', 'error')

    # Retrieve connection details from the session for display
    connection_info = {
        'project_name': session.get('project_name'),
        'dataset_id': session.get('dataset_id'),
        'table_id': session.get('table_id')
    }

    # Render the connect.html template with the connection_info context
    return render_template('connect.html', connection_info=connection_info)


#Display the data that we are connected to
@app.route('/display_data', methods=['POST'])
def display_data():
    # Fetch dataset_id and table_id from session
    dataset_id = session.get('dataset_id')
    table_id = session.get('table_id')

    if not dataset_id or not table_id:
        flash('Dataset ID or Table ID is missing. Please connect first.', 'error')
        return redirect(url_for('connect'))

    try:
        # Construct the fully-qualified table reference
        client = bigquery.Client()
        table_ref = f"{client.project}.{dataset_id}.{table_id}"

        # Execute the query to fetch the first 10 rows
        query = f"SELECT * FROM `{table_ref}` LIMIT 10"
        query_job = client.query(query)  # Make an API request

        # Convert the query result to a pandas DataFrame
        df = query_job.to_dataframe()

        # Convert DataFrame to HTML table for rendering
        df_html = df.to_html(classes='data', index=False)
        
        # Render the display_data.html or any template you're using to show the table
        return render_template('display_data.html', table=df_html)

    except Exception as e:
        flash(f'Failed to display data: {str(e)}', 'error')
        return redirect(url_for('connect'))


if __name__ == '__main__':
    app.run(debug=True)