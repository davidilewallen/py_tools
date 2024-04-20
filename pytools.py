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

# Folder to temporarily store uploaded files
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limit uploads to 16MB


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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


@app.route('/upload-csv', methods=['GET', 'POST'])
def upload_csv():
    if request.method == 'POST':
        # Check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            # Now that we have the file, let's append it to the BigQuery table
            try:
                append_csv_to_bigquery(filepath)
                flash('File successfully uploaded and appended to BigQuery table.')
            except Exception as e:
                flash(f'An error occurred: {e}')
            finally:
                os.remove(filepath)  # Clean up the uploaded file
            return redirect(url_for('upload_csv'))
    return '''
    <!doctype html>
    <title>Upload new CSV</title>
    <h1>Upload new CSV to append to BigQuery</h1>
    <form method=post enctype=multipart/form-data>
      <input type=file name=file>
      <input type=submit value=Upload>
    </form>
    '''
#new keyword categorizer
@app.route('/keycat', methods=['GET', 'POST'])
def categorize_keywords():
    if request.method == 'POST':
        keywords = request.form['keywords'].strip().split('\n')
        brand_terms_1 = request.form['brand_terms_1'].strip().split('\n')
        main_brand_term_1 = request.form['main_brand_term_1'].strip()
        brand_terms_2 = request.form['brand_terms_2'].strip().split('\n')
        main_brand_term_2 = request.form['main_brand_term_2'].strip()
        category_terms = request.form['category_terms'].strip().split('\n')
        brand_match_threshold_1 = int(request.form['brand_match_threshold_1'])
        brand_match_threshold_2 = int(request.form['brand_match_threshold_2'])
        category_match_threshold = int(request.form['category_match_threshold'])

        results = []
        for keyword in keywords:
            result = analyze_keyword(keyword, brand_terms_1, main_brand_term_1, brand_terms_2, main_brand_term_2, category_terms, brand_match_threshold_1, brand_match_threshold_2, category_match_threshold)
            results.append(result)

        return render_template('keycat.html', results=results)
    else:
        return render_template('keycat.html')

def analyze_keyword(keyword, brand_terms_1, main_brand_term_1, brand_terms_2, main_brand_term_2, category_terms, threshold1, threshold2, category_threshold):
    result = {
        'keyword': keyword,
        'brand_category': 'non-brand',
        'matched_brand_term': 'N/A',
        'matched_category_terms': []
    }
    
    if is_address_like(keyword):
        result['brand_category'] = 'brand'
        result['matched_brand_term'] = 'address'
    elif is_phone_number_like(keyword):
        result['brand_category'] = 'brand'
        result['matched_brand_term'] = 'phone number'
    elif is_sku_like(keyword):
        result['brand_category'] = 'brand'
        result['matched_brand_term'] = 'SKU'
    else:
        # Check against fuzzy match criteria
        if find_fuzzy_match(keyword, brand_terms_1, threshold1):
            result['brand_category'] = 'brand'
            result['matched_brand_term'] = main_brand_term_1
        elif find_fuzzy_match(keyword, brand_terms_2, threshold2):
            result['brand_category'] = 'brand'
            result['matched_brand_term'] = main_brand_term_2

    # Determine category matches
    matched_categories = [term for term in category_terms if find_fuzzy_match(keyword, [term], category_threshold)]
    if matched_categories:
        result['matched_category_terms'] = ', '.join(matched_categories)

    return result



def is_phone_number_like(keyword):
    # Use bool to ensure the return type is explicitly boolean
    return bool(re.search(r'\b(\(\d{3}\) |\d{3}-)\d{3}-\d{4}\b', keyword))

def is_address_like(keyword):
    # Use bool to ensure the return type is explicitly boolean
    return bool(re.search(r'\d+\s+\w+\s+(street|st|avenue|ave|road|rd|boulevard|blvd|drive|dr|lane|ln)\b', keyword, re.IGNORECASE))

def is_sku_like(keyword):
    # Already returns a boolean value
    return any(re.search('[a-zA-Z]', segment) and re.search('[0-9]', segment) for segment in re.findall(r'\b[a-zA-Z0-9]{4,14}\b', keyword))


def find_fuzzy_match(keyword, terms, match_threshold):
    best_match, score = process.extractOne(keyword, terms)
    return score >= match_threshold

def analyze_keyword(keyword, brand_terms_1, main_brand_term_1, brand_terms_2, main_brand_term_2, category_terms, threshold1, threshold2, category_threshold):
    result = {
        'keyword': keyword,
        'brand_category': 'non-brand',
        'matched_brand_term': 'N/A',
        'matched_category_terms': []
    }
    
    # Always check for addresses, phone numbers, and SKUs
    if is_address_like(keyword):
        result['brand_category'] = 'brand'
        result['matched_brand_term'] = 'address'
    elif is_phone_number_like(keyword):
        result['brand_category'] = 'brand'
        result['matched_brand_term'] = 'phone number'
    elif is_sku_like(keyword):
        result['brand_category'] = 'brand'
        result['matched_brand_term'] = 'SKU'
    else:
        # Continue with fuzzy matching for brands
        if find_fuzzy_match(keyword, brand_terms_1, threshold1):
            result['brand_category'] = 'brand'
            result['matched_brand_term'] = main_brand_term_1
        elif find_fuzzy_match(keyword, brand_terms_2, threshold2):
            result['brand_category'] = 'brand'
            result['matched_brand_term'] = main_brand_term_2

    # Check category matches using fuzzy matching
    matched_categories = [term for term in category_terms if find_fuzzy_match(keyword, [term], category_threshold)]
    if matched_categories:
        result['matched_category_terms'] = ', '.join(matched_categories)

    return result



if __name__ == '__main__':
    app.run(debug=True)