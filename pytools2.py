from flask import Flask, render_template, request

app = Flask(__name__)

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
    result = None
    if request.method == 'POST':
        list1 = request.form['list1'].lower().split('\n')
        list2 = request.form['list2'].lower().split('\n')
        found_brands = []

        for phrase in list1:
            for brand in list2:
                if brand in phrase:
                    found_brands.append(brand)
        
        result = "Found Brands: " + ", ".join(set(found_brands)) if found_brands else "No brands found."

    return render_template('brand_filter.html', result=result)

if __name__ == '__main__':
    app.run(debug=True)