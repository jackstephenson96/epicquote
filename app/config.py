import os

base_dir = os.path.abspath(os.path.dirname(__file__))
postgres_local_base = 'postgresql://postgres@localhost/'
database_name = 'epicquote'


class BaseConfig:
    """
    Base application configuration
    """
    app.config['SECRET_KEY'] = 'hardtoguessstring'
    # app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get('DATABASE_URL') or "postgresql://localhost/epicquotes" # TODO 364: You should edit this to correspond to the database name YOURUNIQNAMEHW4db and create the database of that name (with whatever your uniqname is; for example, my database would be jczettaHW4db). You may also need to edit the database URL further if your computer requires a password for you to run this.
    app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['FRAZEAPI'] = 'f28271b7-fb0c-456e-8bf3-1b3a1fc2306c'

