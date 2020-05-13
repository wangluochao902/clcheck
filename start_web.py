from web.server.app import app
import os
os.environ['ENV'] = 'development'
DEBUG=True

app.run(debug=DEBUG, port=5000)
