const parse = require("bash-parser");
const traverse = require("bash-ast-traverser");
const DockerfileParser = require("dockerfile-ast").DockerfileParser;
import axios from "axios";
import * as monaco from "monaco-editor/esm/vs/editor/editor.api";
console.log = function() {};

const dockerfileAllInstructions = [
  "add",
  "arg",
  "cmd",
  "copy",
  "entrypoint",
  "env",
  "expose",
  "from",
  "healthcheck",
  "label",
  "maintainer",
  "onbuild",
  "run",
  "shell",
  "stopsignal",
  "user",
  "volume",
  "workdir",
  "cross_build_copy"
];

export function getWords(model, position) {
  const value = model.getLineContent(position.lineNumber);
  let i = position.column - 1;
  const char = value[i];
  var re = /[\w-]/;
  while (i >= 0) {
    if (re.test(value[i])) {
      i--;
    } else {
      break;
    }
  }
  let j = position.column - 1;
  while (j < value.length) {
    if (re.test(value[j])) {
      j++;
    } else {
      break;
    }
  }
  let words = {
    char: char,
    word: value.slice(i + 1, j)
  };
  return words;
}

function offset_position(start, position) {
  if (position.start.row == 1) {
    position.start.col += start.col - 1;
  }
  if (position.end.row == 1) {
    position.end.col += start.col - 1;
  }
  position.start.row += start.row - 1;
  position.end.row += start.row - 1;
  return position;
}

export function find_explanation(AllCommandInfo, commandName, word) {
  const commandInfo = AllCommandInfo[commandName];
  if (commandInfo != null) {
    var Pair_key = null;
    var found_key = word;
    if (word in commandInfo["explanation_key_to_ExplanationPair_key"])
      Pair_key = commandInfo["explanation_key_to_ExplanationPair_key"][word];
    else if (word in commandInfo["option_keys_to_OptionPair_key"])
      Pair_key = commandInfo["option_keys_to_OptionPair_key"][word];
    else if ("-" + word in commandInfo["option_keys_to_OptionPair_key"]) {
      found_key = "-" + word;
      Pair_key = commandInfo["option_keys_to_OptionPair_key"][found_key];
    }
    if (Pair_key != null)
      return {
        found_key: found_key,
        explanation: commandInfo.explanation[Pair_key]
      };
    return null;
  }
}

export function isSmallerOrEqual(l1, l2) {
  for (let i = 0; i < 2; i++) {
    if (l1[i] < l2[i]) {
      return true;
    } else if (l1[i] > l2[i]) {
      return false;
    }
  }
  return true;
}

function modifyMarker(marker, start) {
  const modifiedMarker = Object.assign({}, marker);
  if (modifiedMarker.endLineNumber == null) {
    modifiedMarker.endLineNumber = modifiedMarker.startLineNumber;
  }
  if (modifiedMarker.endColumn == null) {
    modifiedMarker.endColumn = modifiedMarker.startColumn + 1;
  }

  if (modifiedMarker.startLineNumber == 1) {
    modifiedMarker.startColumn += start.col - 1;
  }
  if (modifiedMarker.endLineNumber == 1) {
    modifiedMarker.endColumn += start.col - 1;
  }
  modifiedMarker.startLineNumber += start.row - 1;
  modifiedMarker.endLineNumber += start.row - 1;

  return modifiedMarker;
}

function addUnknownInstruction(instruction, errorMarkers, outputs) {
  const range = instruction.getRange();
  const instructionName = instruction.instruction;
  const marker = {
    startLineNumber: range.start.line + 1,
    startColumn: range.start.character + 1,
    endLineNumber: range.start.line + 1,
    endColumn: instructionName.length,
    severity: monaco.MarkerSeverity.Error,
    message: `Unknow instruction "${instructionName}"`
  };
  errorMarkers.push(marker);
  outputs.push({
    line: marker.startLineNumber,
    col: marker.startColumn,
    color: "red",
    type: "error",
    commandline: instruction.getTextContent(),
    message: marker.message
  });
}

function addParsingError(
  e,
  shellscript,
  shellStartPosition,
  errorMarkers,
  outputs
) {
  // todo: the parser raises a false positive on "$(var $(var2))"
  if (
    e.message == "Unclosed $(" ||
    e.message == 'Unclosed "' ||
    e.message == "Unclosed '"
  )
    return;
  const start_index =
    e.message.indexOf("Parse error on line ") + "Parse error on line ".length;

  const end_index = e.message.slice(10).indexOf(":") + 10;
  let lineNumber = parseInt(e.message.slice(start_index, end_index));
  const commandline = shellscript.split("\n")[lineNumber - 1];
  lineNumber += shellStartPosition.row - 1;
  // todo: this parsing error is a false positive. It is caused by dockerfile comment
  if (e.message.slice(end_index) == ": Unexpected 'AND_IF'") return;
  let marker = {
    startLineNumber: lineNumber,
    endLineNumber: lineNumber,
    startColumn: 1,
    endColumn: 1000,
    message: "Parsing Error" + e.message.slice(end_index),
    severity: monaco.MarkerSeverity.Error
  };
  errorMarkers.push(marker);
  outputs.push({
    line: lineNumber,
    col: marker.startColumn,
    color: "red",
    type: "error",
    commandline: commandline,
    message: marker.message
  });
}

export function clcheck(code, language, AllCommandInfo, lruCache, path) {
  var commandRange = [];
  var errorMarkers = [];
  var outputs = [];
  var promises = [];
  if (language === "shell") {
    promises.push(
      checkshell(
        code,
        { row: 1, col: 1 },
        errorMarkers,
        outputs,
        commandRange,
        AllCommandInfo,
        lruCache,
        path
      )
    );
  } else {
    let dockerfile = DockerfileParser.parse(code);
    let instructions = dockerfile.getInstructions();
    for (let instruction of instructions) {
      const instructionName = instruction.instruction;
      if (
        !dockerfileAllInstructions.includes(instructionName.toLowerCase()) &&
        !instructionName.startsWith("{")
      ) {
        addUnknownInstruction(instruction, errorMarkers, outputs);
      }
      if (instruction.getKeyword() === "RUN") {
        const range = instruction.getRange();
        const shellStartPosition = {
          row: range.start.line + 1,
          col: range.start.character + 1 + 4
        };
        const shellscript = instruction.getTextContent().slice(4);
        promises.push(
          checkshell(
            shellscript,
            shellStartPosition,
            errorMarkers,
            outputs,
            commandRange,
            AllCommandInfo,
            lruCache,
            path
          )
        );
      }
    }
  }
  return Promise.all(promises).then(() => {
    return {
      outputs: outputs,
      errorMarkers: errorMarkers,
      commandRange: commandRange
    };
  });
}

function generateOutput(marker, commandline) {
  return {
    line: marker.startLineNumber,
    col: marker.startColumn,
    color: marker.severity == 8 ? "red" : "rgb(230, 141, 8)",
    type: marker.severity == 8 ? "error" : "warning",
    commandline: commandline,
    message: marker.message
  };
}

async function checkshell(
  shellscript,
  shellStartPosition,
  errorMarkers,
  outputs,
  commandRange,
  AllCommandInfo,
  lruCache,
  path
) {
  try {
    shellscript = shellscript.replace(/\r\n/g, "\n");
    // const shellscript = shellscript.replace('\r', '\n')
    const ast = parse(shellscript, { insertLOC: true });
    var subPromises = [];
    traverse(ast, {
      Command: node => {
        // have a check for `name` key. some command like redirect (when people mistakenly put it at the beginning)
        // don't have such key
        if (node.name == null) {
          console.log(node, "the command doesn't have name");
          return;
        }
        const commandName = node.name.text;
        var start = node.name.loc.start;
        var end = node.loc.end;
        if (node.suffix.length > 0) {
          var n;
          for (n of node.suffix) {
            if (
              n.type === "Word" &&
              !n.text.startsWith("`") &&
              !n.text.startsWith("$")
            ) {
              end = n.loc.end;
            }
            // todo: can't handle cases like `tar -xvf abd_$(uname -m)` because of the space between inside $()
            if (n.type === "Word" && n.text.includes("$")) return;
          }
        }
        const commandline = shellscript.slice(start.char, end.char + 1);
        var position = {
          start: start,
          end: end
        };
        position = offset_position(shellStartPosition, position);
        commandRange.push({
          commandName: commandName,
          start: position.start,
          end: position.end
        });
        if (lruCache.has(commandline)) {
          const marker = lruCache.get(commandline);
          if (marker != null) {
            const modifiedMarker = modifyMarker(marker, position.start);
            errorMarkers.push(modifiedMarker);
            outputs.push(generateOutput(modifiedMarker, commandline));
          }
        } else {
          subPromises.push(
            checkCommand(path, commandline, commandName).then(
              res => {
                const commandInfo = res.data.commandInfo;
                if (Object.keys(commandInfo).length > 0) {
                  AllCommandInfo[commandName] = commandInfo;
                }
                const marker = res.data.marker;
                if (marker != null) {
                  const severityCode = monaco.MarkerSeverity[marker.severity];
                  console.assert(
                    severityCode != null,
                    "marker.severty should be one of `Error`, `Warning`, `Info`, `Hint`"
                  );
                  marker.severity = severityCode;
                  lruCache.put(commandline, marker);
                  var modifiedMarker = modifyMarker(marker, position.start);
                  errorMarkers.push(modifiedMarker);
                  outputs.push(generateOutput(modifiedMarker, commandline));
                }
              },
              error => {
                console.log("can not access");
                console.log(error);
              }
            )
          );
        }
      }
    });
    return Promise.all(subPromises).then(() => {
      console.log("all subpromises done!");
    });
  } catch (e) {
    console.log("parsing error");
    console.log(e);
    addParsingError(e, shellscript, shellStartPosition, errorMarkers, outputs);
  }
}

async function checkCommand(path, commandline, commandName) {
  return axios({
    method: "POST",
    url: path + "checkcommand/",
    headers: { "Content-Type": "application/json" },
    data: { commandline: commandline, commandName: commandName }
  });
}

export async function getDockerfile(path, index) {
  return axios({
    method: "POST",
    url: path + "dockerfiles/",
    headers: { "Content-Type": "application/json" },
    data: { index: index }
  });
}

export async function saveOutput(path, output) {
  return axios({
    method: "POST",
    url: path + "saveOutput/",
    headers: { "Content-Type": "application/json" },
    data: { output: output }
  });
}

export async function getSkipped(path) {
  return axios.get(path + "getSkipped/");
}

export async function addToSkipped(path, details) {
  return axios({
    method: "POST",
    url: path + "addToSkipped/",
    headers: { "Content-Type": "application/json" },
    data: { details: details }
  });
}

export async function deleteFromSkipped(path, objectIdIndex) {
  return axios({
    method: "POST",
    url: path + "deleteFromSkipped/",
    headers: { "Content-Type": "application/json" },
    data: { objectIdIndex: objectIdIndex }
  });
}

export async function getUnknown(path) {
  return axios.get(path + "getUnknown/");
}

export async function addToUnknown(path, details) {
  return axios({
    method: "POST",
    url: path + "addToUnknown/",
    headers: { "Content-Type": "application/json" },
    data: { details: details }
  });
}

export async function deleteFromUnknown(path, objectIdIndex) {
  return axios({
    method: "POST",
    url: path + "deleteFromUnknown/",
    headers: { "Content-Type": "application/json" },
    data: { objectIdIndex: objectIdIndex }
  });
}

export async function getBugs(path) {
  return axios.get(path + "getBugs/");
}

export async function addToBug(path, details) {
  return axios({
    method: "POST",
    url: path + "addToBug/",
    headers: { "Content-Type": "application/json" },
    data: { details: details }
  });
}

export async function deleteFromBug(path, objectIdIndex) {
  return axios({
    method: "POST",
    url: path + "deleteFromBug/",
    headers: { "Content-Type": "application/json" },
    data: { objectIdIndex: objectIdIndex }
  });
}
