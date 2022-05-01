import re
import pymongo
from flask import Flask, render_template, request, jsonify, abort
from flask_cors import CORS
# from flask_bootstrap import Bootstrap

import bashlex
from clchecker.visitor import Visitor, create_marker
from clchecker.checker import CLchecker
from clchecker.errors import CLError
from config import MONGO_URI
from clchecker.store import Store, Command
import dockerfile
import os

# instantiate the app
app = Flask(__name__)
# Bootstrap(app)
app.config.from_object(__name__)
logger = app.logger

store = Store(db='clchecker')
clchecker = CLchecker(store)
visitor = Visitor(clchecker, logger=logger)

# enable CORS
CORS(app,
     resources={
         r'/clcheck/*': {
             'origins': os.environ['ORIGINS']
         }
     })

if os.environ['ENV'] != "production":
    import pymongo, pickle
    db = pymongo.MongoClient('localhost')['dockerfiles']
    dockerfile_collection = db['dockerfiles']
    skipped_collection = db['skipped']
    unknown_collection = db['unknown']
    bug_collection = db['bug']
    verified_bug_collection = db['verified_bug']
    with open('dockerfiles/object_ids.pkl', 'rb') as f:
        object_ids = pickle.load(f)
else:
    db = pymongo.MongoClient(MONGO_URI)['dockerfiles']
    verified_bug_collection = db['verified_bug']
    dockerfile_collection = None

@app.route('/')
def home():
    return 'hello clcheck'

@app.route('/checkcode/', methods=['GET', 'POST'])
def checkcode():
    ori_code = request.json['code']
    language = request.json['language']
    code = ori_code.replace('\r\n', '\n').replace('\r', '\n')
    assert language in ('shell',
                        'dockerfile'), 'Only shell or dockerfile is accepted'
    if language == 'dockerfile':
        try:
            dockerfile_commands = dockerfile.parse_string(ori_code)
            for command in dockerfile_commands:
                if command.cmd == 'run':
                    markers, command_range = visitor.start(
                        command.original.split(' ', 1)[-1].strip())
                    if len(markers) > 0:
                        pre_lines = command.start_line - 1
                        # 'run ' takes at least 4 cols
                        pre_cols = 4
                        while command.original[pre_cols] in (' ', '\t'):
                            pre_cols += 1
                            assert pre_cols <= 200, "Should be an error. It is very unlikely to have pre_cols larger than 200"
                        markers, command_range = refine_markers_and_command_range(
                            pre_lines=pre_lines,
                            pre_cols=pre_cols,
                            markers=markers,
                            command_range=command_range)
                        return jsonify({
                            "error": {
                                "code": ori_code,
                                "markers": markers
                            },
                            "commandRange": command_range
                        })
        except:
            pass
        return jsonify({
            "error": {
                "code": ori_code,
                "markers": []
            },
            "commandRange": {}
        })

    else:
        markers, command_range = visitor.start(code)
        return jsonify({
            "error": {
                "code": ori_code,
                "markers": markers
            },
            "commandRange": command_range
        })


@app.route('/clcheck/checkcommand/', methods=['GET', 'POST'])
def checkcommand():
    command_name, commandline = request.json['commandName'], request.json[
        'commandline']
    marker = None
    command_info = {}
    try:
        clchecker.check(command_name=command_name, commandline=commandline)
    except CLError as e:
        marker = create_marker(e.start_line, e.start_col, e.end_line, e.end_col,
                               e.message, e.severity)
    metamodel_doc = clchecker.metamodel_doc_cache.get(command_name)
    if metamodel_doc:
        concrete_specs = metamodel_doc[1].concrete_specs
        command_info[
            'explanation_key_to_ExplanationPair_key'] = concrete_specs[
                'explanation_key_to_ExplanationPair_key']
        command_info['option_keys_to_OptionPair_key'] = concrete_specs[
            'option_keys_to_OptionPair_key']
        command_info['explanation'] = metamodel_doc[1].explanation
    return jsonify({"marker": marker, "commandInfo": command_info})


@app.route('/clcheck/explain/', methods=['GET', 'POST'])
def explain():
    command_name, words = request.json['commandName'], request.json['words']
    char, word = words['char'], words['word']
    found_key, explanation = clchecker.find_explanation(command_name, word)
    if not explanation:
        found_key, explanation = clchecker.find_explanation(command_name, char)
    if explanation:
        explanation = "```python\n" + explanation + '\n```'
    else:
        explanation = ''
    result = {'found_key': found_key, "explanation": explanation}
    return jsonify(result)

@app.route('/clcheck/dockerfiles/', methods=['GET', 'POST'])
def get_dockerfile():
    if os.environ['ENV'] == 'production':
        abort(404, description="not available in production mode")
    index = request.json['index']
    if index >= len(object_ids):
        abort(404, f"index({index}) should be smaller than {len(object_ids)}")
    r = dockerfile_collection.find_one({"_id": object_ids[index]})
    return jsonify({"code":r['code'], "repository": r['repo_name'], "file": r['file_path']})

@app.route('/clcheck/saveOutput/', methods=['GET', 'POST'])
def get_output():
    if os.environ['ENV'] == 'production':
        abort(404, description="not available in production mode")
    output = request.json['output']
    import json
    if os.path.exists('./error_outputs.json'):
        with open('./error_outputs.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    else:
        data = {"results": []}
    data['results'].append(output)
    try:
        with open('./error_outputs.json', 'w', encoding='utf-8') as f:
            json.dump(data, f)
    except json.decoder.JSONDecodeError:
        pass
    return "finish"

@app.route('/clcheck/getSkipped/', methods=['GET'])
def get_skipped():
    if os.environ['ENV'] == 'production':
        abort(404, description="not available in production mode")
    responce = skipped_collection.find({})
    skipped = [r['objectIdIndex'] for r in responce]
    return jsonify({"skipped_index": skipped})
    
@app.route('/clcheck/addToSkipped/', methods=['GET', 'POST'])
def add_to_skipped():
    if os.environ['ENV'] == 'production':
        abort(404, description="not available in production mode")
    try:
        details = request.json['details']
        skipped_collection.insert_one(details)
        return {'Added': True}
    except:
        abort(404, description="can not add to the database")

@app.route('/clcheck/deleteFromSkipped/', methods=['GET', 'POST'])
def delete_from_skipped():
    if os.environ['ENV'] == 'production':
        abort(404, description="not available in production mode")
    try:
        objectIdIndex = request.json['objectIdIndex']
        skipped_collection.delete_one({"objectIdIndex":objectIdIndex})
        return {'deleted': True}
    except:
        abort(404, description="can not add to the database")

@app.route('/clcheck/getUnknown/', methods=['GET'])
def get_unknown():
    if os.environ['ENV'] == 'production':
        abort(404, description="not available in production mode")
    responce = unknown_collection.find({})
    unknown = [r['objectIdIndex'] for r in responce]
    return jsonify({"unknown_index": unknown})
    
@app.route('/clcheck/addToUnknown/', methods=['GET', 'POST'])
def add_to_unknown():
    if os.environ['ENV'] == 'production':
        abort(404, description="not available in production mode")
    try:
        details = request.json['details']
        unknown_collection.insert_one(details)
        return {'Added': True}
    except:
        abort(404, description="can not add to the database")

@app.route('/clcheck/deleteFromUnknown/', methods=['GET', 'POST'])
def delete_from_unknown():
    if os.environ['ENV'] == 'production':
        abort(404, description="not available in production mode")
    try:
        objectIdIndex = request.json['objectIdIndex']
        unknown_collection.delete_one({"objectIdIndex":objectIdIndex})
        return {'deleted': True}
    except:
        abort(404, description="can not add to the database")

@app.route('/clcheck/getBugs/', methods=['GET'])
def get_bugs():
    if os.environ['ENV'] == 'production':
        abort(404, description="not available in production mode")
    responce = bug_collection.find({})
    bugs = [r['objectIdIndex'] for r in responce]
    return jsonify({"bugs": bugs})
    
@app.route('/clcheck/addToBug/', methods=['GET', 'POST'])
def add_to_bug():
    if os.environ['ENV'] == 'production':
        abort(404, description="not available in production mode")
    try:
        details = request.json['details']
        bug_collection.insert_one(details)
        return {'Added': True}
    except:
        abort(404, description="can not add to the database")

@app.route('/clcheck/deleteFromBug/', methods=['GET', 'POST'])
def delete_from_bug():
    if os.environ['ENV'] == 'production':
        abort(404, description="not available in production mode")
    try:
        objectIdIndex = request.json['objectIdIndex']
        bug_collection.delete_one({"objectIdIndex":objectIdIndex})
        return {'deleted': True}
    except:
        abort(404, description="can not add to the database")


@app.route('/clcheck/getVerifiedBugs/', methods=['GET'])
def get_verified_bugs():
    contents = verified_bug_collection.find({})
    new_contents = []
    for content in contents:
        new_content = dict()
        for key in content:
            if key != '_id':
                new_content[key] = content[key]
        new_contents.append(new_content)
    return jsonify({"contents": new_contents})
    
@app.route('/clcheck/addToVerifiedBug/', methods=['GET', 'POST'])
def add_to_verified_bug():
    try:
        content = request.json['content']
        verified_bug_collection.insert_one(content)
        return {'Added': True}
    except:
        abort(404, description="can not add to the database")


def refine_markers_and_command_range(pre_lines, pre_cols, markers,
                                     command_range):
    for marker in markers:
        if marker["startLineNumber"]:
            marker["startLineNumber"] += pre_lines
        if marker["startColumn"]:
            marker["startColumn"] += pre_cols
        if marker["endLineNumber"]:
            marker["endLineNumber"] += pre_lines
        if marker["endColumn"]:
            marker["endColumn"] += pre_cols
    if command_range:
        for cmd in command_range:
            if "startLine" in command_range[cmd] and command_range[cmd][
                    "startLine"]:
                command_range[cmd]["startLine"] += pre_lines
            if "startColumn" in command_range[cmd] and command_range[cmd][
                    "startColumn"]:
                command_range[cmd]["startColumn"] += pre_cols
            if "endLine" in command_range[cmd] and command_range[cmd]["endLine"]:
                command_range[cmd]["endLine"] += pre_lines
            if "endColumn" in command_range[cmd] and command_range[cmd][
                    "endColumn"]:
                command_range[cmd]["endColumn"] += pre_cols
    return markers, command_range
