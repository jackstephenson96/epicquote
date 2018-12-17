import os
import requests
import json
from flask import Flask, render_template, session, redirect, request, url_for, flash
from flask_script import Manager, Shell
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, FileField, PasswordField, BooleanField, SelectMultipleField, ValidationError, RadioField, FieldList, FormField
from wtforms.validators import Required, Length, Email, Regexp, EqualTo
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, MigrateCommand
from werkzeug.security import generate_password_hash, check_password_hash

# Imports for login management
from flask_login import LoginManager, login_required, logout_user, login_user, UserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash

# Imports for helper functions
# import python_amazon_simple_product_api as AmazonAPI
testQuotes = [{'quote':"test quote 1", 'author': 'author 1'},
			  {'quote':"test quote 2", 'author': 'author 2'},
			  {'quote':"test quote 3", 'author': 'author 3'},
			  {'quote':"test quote 4", 'author': 'author 4'},
			  {'quote':"test quote 5", 'author': 'author 5'}]

# Application configurations
app = Flask(__name__)
app.debug = True
app.use_reloader = True
app.config['SECRET_KEY'] = 'hardtoguessstring'
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get('DATABASE_URL') or "postgresql://localhost/epicquote" # TODO 364: You should edit this to correspond to the database name YOURUNIQNAMEHW4db and create the database of that name (with whatever your uniqname is; for example, my database would be jczettaHW4db). You may also need to edit the database URL further if your computer requires a password for you to run this.
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['FRAZEAPI'] = 'f28271b7-fb0c-456e-8bf3-1b3a1fc2306c'
app.config['HEROKU_ON'] = os.environ.get('HEROKU')


'''TODO:
[ ] save quotes in database
[ ] add collection template, route, view, form (lol)
[ ] connect quotes with collection
'''


# App addition setups
manager = Manager(app)
db = SQLAlchemy(app)
migrate = Migrate(app, db)
manager.add_command('db', MigrateCommand)

# Login configurations setup
login_manager = LoginManager()
login_manager.session_protection = 'strong'
login_manager.login_view = 'login'
login_manager.init_app(app) # set up login manager




########################
######## Models ########
######################## 
quotecollection = db.Table('quotecollection',
	db.Column('collection_id', db.Integer, db.ForeignKey('collection.id')),
	db.Column('quote_id', db.Integer, db.ForeignKey('quote.id')),
	db.UniqueConstraint('collection_id', 'quote_id', name='collection_id_quote_id')
)

# Special model for users to log in
class User(UserMixin, db.Model):
	__tablename__ = "user"
	id = db.Column(db.Integer, primary_key=True)
	# first = db.Column(db.String(64))
	# last = db.Column(db.String(64))
	username = db.Column(db.String(255), unique=True, index=True)
	email = db.Column(db.String(64), unique=True, index=True)
	password_hash = db.Column(db.String(128))
	
	@property
	def password(self):
		raise AttributeError('password is not a readable attribute')

	@password.setter
	def password(self, password):
		self.password_hash = generate_password_hash(password)

	def verify_password(self, password):
		return check_password_hash(self.password_hash, password)

## DB load function
## Necessary for behind the scenes login manager that comes with flask_login capabilities! Won't run without this.
@login_manager.user_loader
def load_user(user_id):
	return User.query.get(int(user_id)) # returns User object or None


class Quote(db.Model):
	__tablename__ = "quote"
	# TODO 364: Add code for the Gif model such that it has the following fields:
	id = db.Column(db.Integer, primary_key=True)
	quote = db.Column(db.String(128))
	author_name = db.Column(db.String(128))
	author_id = db.Column(db.Integer, db.ForeignKey("author.id"))
	## RELATIONSHIP?
	def __repr__(self):
		return "{} @ {}".format(self.quote,self.author_name)

class Author(db.Model):
	__tablename__ = "author"
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(128))
	quotes = db.relationship('Quote', backref='author', lazy='dynamic')


class Collection(db.Model):
	__tablename__ = 'collection'
	id = db.Column(db.Integer, primary_key=True)
	user_id = db.Column(db.Integer, db.ForeignKey("user.id")) 
	quotes = db.relationship(
		'Quote',
		secondary=quotecollection,
		backref=db.backref('collection',lazy='dynamic'),lazy='dynamic')


########################
######## Forms #########
########################

class RegistrationForm(FlaskForm):
	# first = StringField('First Name:', validators=[Required(), Length(1,64)])
	# last = StringField('Last Name:', validators=[Required(), Length(1,64)])
	email = StringField('Email:', validators=[Required(),Length(1,64),Email()])
	username = StringField('Username:',validators=[Required(),Length(1,64),Regexp('^[A-Za-z][A-Za-z0-9_.]*$',0,'Usernames must have only letters, numbers, dots or underscores')])
	password = PasswordField('Password:',validators=[Required(),EqualTo('password2',message="Passwords must match")])
	password2 = PasswordField("Confirm Password:",validators=[Required()])
	submit = SubmitField('Register User')

	#Additional checking methods for the form
	def validate_email(self,field):
		if User.query.filter_by(email=field.data).first():
			raise ValidationError('Email already registered.')

	def validate_username(self,field):
		if User.query.filter_by(username=field.data).first():
			raise ValidationError('Username already taken')

class LoginForm(FlaskForm):
	username = StringField('Username')
	email = StringField('Email', validators=[Required(), Length(1,64), Email()])
	password = PasswordField('Password', validators=[Required()])
	remember_me = BooleanField('Keep me logged in')
	submit = SubmitField('Log In')

class QuoteSearchForm(FlaskForm):
	keyword = StringField('Quote Keyword: ', validators=[Required(), Length(1,256)])
	submit = SubmitField('Search')
	## How to have button pop up after asking to save? in search results prob

class CustomSelect(FlaskForm):
	choice = BooleanField("Not")


class QuoteSelectForm(FlaskForm):
	selects = FieldList(FormField(CustomSelect))
	save = SubmitField('Save Selected Quotes to Collection')
	# additem
	#https://stackoverflow.com/questions/43811779/use-many-submit-buttons-in-the-same-form

# class CollectionForm(FlaskForm):
class DeleteButton(FlaskForm):
	submit = SubmitField('Delete')

########################
### Helper functions ###
########################

# def getAMZNlink():

def getQuote(query):
	'''
	q: the query, encoded form.
	lang: language used. English(en), French(fr), Spanish(es), German(de), Italian(it), Portugese(pt) supported.
	page: page number (use that to implement pagination:1,2,etc). [Maximum is 10. If needed, you may ask for more].
	highlight: [yes/no] - choose 'yes' to highlight the query in the search result.
	key: your API key.
	'''

	key = 'f28271b7-fb0c-456e-8bf3-1b3a1fc2306c'
	url = 'https://fraze.it/api/famous/{}/en/1/no/{}'.format(query, key)
	r = requests.get(url, headers={'Accept': 'application/json'})
	try:
		quotes = [{'quote':q['phrase'], 'author':q['author']} for q in json.loads(r.text)['results'][:5]]
	except Exception:
		quotes = []
		flash("Uh oh! Out of API requests for today")

	return quotes
	## Add error handling



def get_or_create_quote(db_session, q, author_id):
	quote = db_session.query(Quote).filter_by(quote=q['quote']).first()
	if quote:
		return quote
	else:
		newquote = Quote(quote=str(q['quote']), author_name=str(q['author']), author_id=author_id)
		db_session.add(newquote)
		db_session.commit()
		return newquote

def get_or_create_author(db_session, q):
	author = db_session.query(Author).filter_by(name=q['author']).first()
	if author:
		return author
	else:
		author = Author(name=q['author'])
		db_session.add(author)
		db_session.commit()
		return author

def get_or_create_collection(db_session, user, quotes=None):
	addquotes = []
	collection = db_session.query(Collection).filter_by(user_id=user.id).first()
	if not collection:
		collection = Collection(user_id=user.id, quotes=[])
	if quotes != None:
		for quote in quotes:
			try:
				if quote not in collection.quotes:
					collection.quotes.append(quote)
					db_session.add(collection)
					db.session.commit()
					return collection
				else:
					flash('Quote already added')
			except Exception as e:
				print('EXCEPTION', e)

	else:
		return collection


########################
#### View functions ####
########################

## Error handling routes
@app.errorhandler(404)
def page_not_found(e):
	return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
	return render_template('500.html'), 500


## Login-related routes - provided
@app.route('/login',methods=["GET","POST"])
def login():
	form = LoginForm()
	if form.validate_on_submit():
		user = User.query.filter_by(email=form.email.data).first()
		if user is not None and user.verify_password(form.password.data):
			login_user(user, form.remember_me.data)
			return redirect(request.args.get('next') or url_for('index'))
		flash('Invalid email or password.')
	return render_template('login.html',form=form)

@app.route('/logout')
@login_required
def logout():
	logout_user()
	flash('You have been logged out')
	return redirect(url_for('index'))

@app.route('/register',methods=["GET", "POST"])
def register():
	form = RegistrationForm()
	if form.validate_on_submit():
		user = User(username=form.username.data, email=form.email.data, password=form.password.data)
		db.session.add(user)
		db.session.commit()
		flash('You can now log in!')
		return redirect(url_for('login'))
	return render_template('register.html',form=form)

@app.route('/secret')
@login_required
def secret():
	return "Only authenticated users can do this! Try to log in or contact the site admin."

@app.route('/', methods=['GET', 'POST'])
def index():
	return render_template('index.html', user=current_user)

@app.route('/search', methods=['GET', 'POST'])
def search():
	form = QuoteSearchForm()
	if form.validate_on_submit():
		if request.method == 'POST':

			return redirect(url_for('search_results', keyword=form.keyword.data))
	return render_template('search.html', form=form)

@app.route('/search_results/<keyword>', methods=['GET', 'POST'])
def search_results(keyword):
	form = QuoteSelectForm()
	# quotes = testQuotes
	quotes = getQuote(keyword)

	if form.validate_on_submit():
		# quotes = getQuote(keyword)
		if request.method == 'POST':
			quotesOut = []
			for idx, q in enumerate(quotes):

				if form.selects.data[idx]['choice'] == True:
					author = get_or_create_author(db.session, q=q)
					quote = get_or_create_quote(db.session, q=q, author_id=author.id)
					quotesOut.append(quote)

			collection = get_or_create_collection(db.session, current_user, quotes=quotesOut)
			return(redirect(url_for('mycollection')))
	else:
		form.selects.entries = []
		for i in quotes:
			form.selects.append_entry()
	return render_template('search_results.html', form=form, keyword=keyword, quotes=quotes)

@app.route('/mycollection', methods=['GET', 'POST'])
def mycollection():
	form = DeleteButton()
	collection = get_or_create_collection(db.session, user=current_user)
	if request.method == 'POST':
		flash('Quotes added!')	
	return render_template('mycollection.html', form=form, quotes=collection.quotes)


@app.route('/delete/<quote_id>',methods=["GET","POST"])
def delete(quote_id):
	form = DeleteButton()

	collection = db.session.query(Collection).filter_by(user_id = current_user.id).first()
	quote = db.session.query(Quote).filter_by(id = quote_id).first()
	collection.quotes.remove(quote)
	flash("Quote removed ~ ID: {}".format(quote_id))

	return(redirect(url_for('mycollection')))

@app.route('/all_authors', methods=['GET'])
def all_authors():
	authors = Author.query.all()
	if request.method == "GET":
		return render_template('all_authors.html', authors=authors)

@app.route('/all_quotes', methods=['GET'])
def all_quotes():
	quotes = Quote.query.all()
	if request.method == "GET":
		return render_template('all_quotes.html', quotes=quotes)


if __name__ == '__main__':
	db.create_all()
	manager.run()
