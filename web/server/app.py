from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from flask_bootstrap import Bootstrap
import bashlex
from web.server.utils import Visitor
from clchecker.checker import CLchecker
from clchecker.store import Store, Command

# configuration
DEBUG = True

# instantiate the app
app = Flask(__name__)
Bootstrap(app)
app.config.from_object(__name__)
LOGGER = app.logger

store = Store(db='clchecker_test')
clchecker = CLchecker(store)
VISITOR = Visitor(clchecker, logger=LOGGER)

# enable CORS
CORS(app, resources={r'/clcheck/*': {'origins': '*'}})


@app.route('/clcheck/', methods=['GET', 'POST'])
def clcheck():
    ori_code = request.json['code']
    code = ori_code.replace('\r\n', '\n').replace('\r', '\n')
    print(code.encode('utf-8'))
    markers = VISITOR.start(code)
    print(markers)
    return jsonify({"code": ori_code, "markers": markers})


if __name__ == '__main__':
    app.run(debug=DEBUG, port=5000)
