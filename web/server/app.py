import re
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from flask_bootstrap import Bootstrap
import bashlex
from clchecker.visitor import Visitor
from clchecker.checker import CLchecker
from clchecker.store import Store, Command
import dockerfile

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
    language = request.json['language']
    print(f"this is the language: {language}")
    code = ori_code.replace('\r\n', '\n').replace('\r', '\n')
    assert language in ('shell',
                        'dockerfile'), 'Only shell or dockerfile is accepted'
    if language == 'dockerfile':
        try:
            print("is is dockerfile")
            dockerfile_commands = dockerfile.parse_string(ori_code)
            print("parse dockerfile sucessfully")
            for command in dockerfile_commands:
                if command.cmd == 'run':
                    print('has a command run')
                    print(
                        f"pass `{command.original.split(' ', 1)[-1].strip()}` into visit"
                    )
                    markers, command_range = VISITOR.start(
                        command.original.split(' ', 1)[-1].strip())
                    print(
                        f'get markers back {markers}, and command_range {command_range}'
                    )
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
                        print(
                            f'after refining {markers}, and command_range {command_range}'
                        )
                        return jsonify({
                            "error": {
                                "code": ori_code,
                                "markers": markers
                            },
                            "commandRange": command_range
                        })
        except:
            print("can't parse the dockerfile")
            pass
        return jsonify({
            "error": {
                "code": ori_code,
                "markers": []
            },
            "commandRange": {}
        })

    else:
        print(code.encode('utf-8'))
        markers, command_range = VISITOR.start(code)
        return jsonify({
            "error": {
                "code": ori_code,
                "markers": markers
            },
            "commandRange": command_range
        })


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
            if "startLine" in command_range[cmd] and command_range[cmd]["startLine"]:
                command_range[cmd]["startLine"] += pre_lines
            if "startColumn" in command_range[cmd] and command_range[cmd]["startColumn"]:
                command_range[cmd]["startColumn"] += pre_cols
            if "endLine" in command_range[cmd] and command_range[cmd]["endLine"]:
                command_range[cmd]["endLine"] += pre_lines
            if "endColumn" in command_range[cmd] and command_range[cmd]["endColumn"]:
                command_range[cmd]["endColumn"] += pre_cols
    return markers, command_range
