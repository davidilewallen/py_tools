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

# Create User Page
@app.route('/user/<name>')
def user(name):
	return render_template('user.html', user_name=name)