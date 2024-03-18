from flask import Flask, request, render_template, redirect, url_for
import pandas as pd
from fuzzywuzzy import process
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/'

def find_similar_column_names(column_names):
    similarity_threshold = 80
    potential_groupings = {}

    for column_name in column_names:
        matches = process.extract(column_name, column_names, limit=None)
        for match in matches:
            matched_name, score = match[0], match[1]
            if score >= similarity_threshold and column_name != matched_name:
                if column_name in potential_groupings:
                    potential_groupings[column_name].add(matched_name)
                else:
                    potential_groupings[column_name] = {matched_name}
    return potential_groupings

@app.route('/card_sorting', methods=['GET', 'POST'])
def card_sorting():
    if request.method == 'POST':
        if 'file' not in request.files:
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            return redirect(request.url)
        if file:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Process the uploaded Excel file
            xls = pd.ExcelFile(filepath)
            data = xls.parse(xls.sheet_names[0]) # Assuming data is in the first sheet
            column_names = data.columns.tolist()
            
            # Find similar column names
            similar_columns = find_similar_column_names(column_names)
            
            # Implement functionality to review similar_columns or return them to the template
            
            # Placeholder redirect, you might want to return a template with similar_columns
            return redirect(url_for('card_sorting'))
    else:
        # Render the upload form for GET requests
        return render_template('card_sort.html')

if __name__ == '__main__':
    app.run(debug=True)
