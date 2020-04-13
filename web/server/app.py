import re
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from flask_bootstrap import Bootstrap
import bashlex
from clchecker.visitor import Visitor
from clchecker.checker import CLchecker
from clchecker.store import Store, Command


# instantiate the app
app = Flask(__name__)
Bootstrap(app)
app.config.from_object(__name__)
LOGGER = app.logger

store = Store(db='clchecker')
clchecker = CLchecker(store)
VISITOR = Visitor(clchecker, logger=LOGGER)

# enable CORS
CORS(app, resources={r'/clcheck/*': {'origins': '*'}})


@app.route('/clcheck/', methods=['GET', 'POST'])
def clcheck():
    ori_code = request.json['code']
    code = ori_code.replace('\r\n', '\n').replace('\r', '\n')
    print(code.encode('utf-8'))
    markers, command_range = VISITOR.start(code)
    return jsonify({"error": {"code": ori_code, "markers": markers}, "commandRange": command_range})


@app.route('/clcheck/explain/', methods=['GET', 'POST'])
def explain():
    command_name, key = request.json['commandName'], request.json['key']
    explanation = VISITOR.find_explanation(command_name, key)
    if explanation:
        explanation = "```python\n" + explanation + '\n```'
    else:
        explanation = ''
    print(explanation, 'this is the explanation')
    return jsonify({"explanation": explanation})
