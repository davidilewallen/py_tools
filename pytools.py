from flask import Flask, render_template

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