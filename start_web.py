import os
os.environ['MONGO_URI'] = 'localhost'
os.environ['ENV'] = 'production'
os.environ['ORIGINS'] = '*'
from web.server.app import app
DEBUG=True

app.run(debug=DEBUG, port=5000)
