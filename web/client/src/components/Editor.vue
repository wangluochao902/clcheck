<template>
  <div id="container" style="width: 100%; height: 100%;"></div>
</template>

<script>
import * as monaco from "monaco-editor/esm/vs/editor/editor.api";
import axios from "axios";

const parse = require("bash-parser");
const traverse = require("bash-ast-traverser");
const DockerfileParser = require("dockerfile-ast").DockerfileParser;

class LRUCache {
  constructor(capacity) {
    this.cache = new Map();
    this.capacity = capacity;
  }

  has(key) {
    return this.cache.has(key);
  }

  get(key) {
    if (!this.cache.has(key)) return -1;

    const v = this.cache.get(key);
    this.cache.delete(key);
    this.cache.set(key, v);
    return this.cache.get(key);
  }

  put(key, value) {
    if (this.cache.has(key)) {
      this.cache.delete(key);
    }
    this.cache.set(key, value);
    if (this.cache.size > this.capacity) {
      this.cache.delete(this.cache.keys().next().value); // keys().next().value returns first item's key
    }
  }
}

export { monaco };

export default {
  name: "Editor",
  props: {
    width: [String, Number],
    height: [String, Number],
    language: String,
    path: String,
  },
  data() {
    return {
      editor: null,
      lruCache: new LRUCache(1),
      value:
        "if [ 3 -gt 2 ]; \nthen\n    apt-get --assume-no install -y nodejs;\nfi;",
      error: {
        code: "",
        marker: "",
      },
      errorMarkers: [],
      explanation: "",
      commandRange: {},
    };
  },

  mounted() {
    this.initMonaco();
  },

  watch: {
    errorMarkers() {
      monaco.editor.setModelMarkers(
        this.editor.getModel(),
        "test",
        this.errorMarkers
      );
      console.log("error marker changed");
      console.log(this.errorMarkers);
    },
    language() {
      monaco.editor.setModelLanguage(this.editor.getModel(), this.language);
      if (this.language == "shell") {
        this.value =
          "if [ 3 -gt 2 ]; \nthen\n    apt-get --assume-no install -y nodejs;\nfi;";
      } else {
        this.value =
          "FROM ubuntu:16.04\nRUN apt-get --assume-no install -qqy nodejs &&\\\n    tar xvfsaeadf\n";
      }
    },
    explanation() {},
    value() {
      this.editor.setValue(this.value);
    },
  },

  methods: {
    provideHover(model, position) {
      console.log("new");
      console.log(position);
      console.log("the command_range is");
      console.log(this.commandRange);
      let commandName = this.getCommandName(position);
      if (commandName != null) {
        const words = this.getWords(model, position);
        console.log(words + "  is the word");
        return this.explain(commandName, words).then((result) => {
          if (result["explanation"] != "") {
            console.log("this is the explanation: " + result["explanation"]);
            return {
              contents: [
                { value: `**${result["found_key"]}**` },
                {
                  value: result["explanation"],
                },
              ],
            };
          }
        });
      }
    },

    getCommandName(position) {
      //TODO: use binary search instead
      for (const command of this.commandRange) {
        if (
          position.lineNumber >= command["start"]["row"] &&
          position.lineNumber <= command["end"]["row"] &&
          position.column >= command["start"]["col"] &&
          position.column <= command["end"]["col"]
        ) {
          return command.commandName;
        }
      }
      return null;
    },

    getWords(model, position) {
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
        word: value.slice(i + 1, j),
      };
      return words;
    },

    modify_marker(marker, start, shellStartPosition) {
      const modified_marker = Object.assign({}, marker);
      if (modified_marker.endLineNumber == null) {
        modified_marker.endLineNumber = modified_marker.startLineNumber;
      }
      if (modified_marker.endColumn == null) {
        modified_marker.endColumn = modified_marker.startColumn + 1;
      }

      if (modified_marker.startLineNumber == 1) {
        modified_marker.startColumn += start.col - 1;
        if (start.row == 1) {
          modified_marker.startColumn += shellStartPosition.col - 1;
        }
      }
      if (modified_marker.endLineNumber == 1) {
        modified_marker.endColumn += start.col - 1;
        if (start.row == 1) {
          modified_marker.endColumn += shellStartPosition.col - 1;
        }
      }
      modified_marker.startLineNumber += start.row + shellStartPosition.row - 2;
      modified_marker.endLineNumber += start.row + shellStartPosition.row - 2;

      return modified_marker;
    },

    initMonaco() {
      this.editor = monaco.editor.create(document.getElementById("container"), {
        language: this.language,
        theme: "vs",
        scrollBeyondLastLine: false,
        minimap: { enabled: false },
        value: this.value,
        hover: { delay: 1000 },
      });
      this.editor.onDidChangeModelContent(() => {
        this.clcheck(this.editor.getValue());
        console.log(this.editor.getValue().length);
      });
      monaco.languages.registerHoverProvider("shell", {
        provideHover: this.provideHover,
      });
      monaco.languages.registerHoverProvider("dockerfile", {
        provideHover: this.provideHover,
      });
    },

    clcheck(code) {
      this.commandRange = [];
      this.errorMarkers = [];
      if (this.language === "shell") {
        this.checkshell(code, { row: 1, col: 1 });
      } else {
        let dockerfile = DockerfileParser.parse(code);
        let instructions = dockerfile.getInstructions();
        for (let instruction of instructions) {
          if (instruction.getKeyword() === "RUN") {
            const range = instruction.getRange();
            const shellStartPosition = {
              row: range.start.line + 1,
              col: range.start.character + 1 + 3,
            };
            const shellscript = instruction.getTextContent().slice(3);
            this.checkshell(shellscript, shellStartPosition);
          }
        }
      }
    },

    async checkshell(shellscript, shellStartPosition) {
      try {
        const ast = parse(shellscript, { insertLOC: true });
        // utils.logResults(result)
        traverse(ast, {
          Command: (node) => {
            const commandName = node.name.text;
            const start = node.loc.start;
            var end = node.loc.end;
            if (node.suffix) {
              var n;
              for (n of node.suffix) {
                if (
                  n.type === "Word" &&
                  !n.text.startsWith("`") &&
                  !n.text.startsWith("$")
                )
                  end = n.loc.end;
              }
            }
            this.commandRange.push({
              commandName: commandName,
              start: start,
              end: end,
            });
            const commandline = shellscript.slice(start.char, end.char + 1);
            if (this.lruCache.has(commandline)) {
              const marker = this.lruCache.get(commandline);
              if (marker != null) {
                const modified_marker = this.modify_marker(
                  marker,
                  start,
                  shellStartPosition
                );
                this.errorMarkers.push(modified_marker);
              }
            } else {
              this.checkCommand(commandline, commandName).then(
                (res) => {
                  const marker = res.data.marker;
                  const severityCode = monaco.MarkerSeverity[marker.severity];
                  console.assert(
                    severityCode != null,
                    "marker.severty should be one of `Error`, `Warning`, `Info`, `Hint`"
                  );
                  marker.severity = severityCode;
                  console.log("this is the marker");
                  console.log(marker);
                  this.lruCache.put(commandline, marker);
                  const modified_marker = this.modify_marker(
                    marker,
                    start,
                    shellStartPosition
                  );
                  this.errorMarkers.push(modified_marker);
                },
                (error) => {
                  console.log("can not access");
                  console.log(error);
                }
              );
            }
          },
        });
      } catch (e) {
        if (e instanceof Error) {
          console.log("parsing error");
          const start_index = "Parse error on line ".length;
          const end_index = e.message.indexOf(":");
          let lineNumber = parseInt(e.message.slice(start_index, end_index));
          lineNumber += shellStartPosition.row - 1;
          let marker = {
            startLineNumber: lineNumber,
            endLineNumber: lineNumber,
            startColumn: 1,
            endColumn: 1000,
            message: "Parsing Error" + e.message.slice(end_index),
            severity: monaco.MarkerSeverity.Error,
          };
          this.errorMarkers.push(marker);
          console.log(e);

          console.log(e.message);
        } else {
          throw e; // re-throw the error unchanged
        }
      }
    },

    async checkCommand(commandline, commandName) {
      return axios({
        method: "POST",
        url: this.path + "checkcommand/",
        headers: { "Content-Type": "application/json" },
        data: { commandline: commandline, commandName: commandName },
      });
    },

    async explain(commandName, words) {
      console.log("receive the explain event");
      let explanation = await axios({
        method: "POST",
        url: this.path + "explain/",
        headers: { "Content-Type": "application/json" },
        data: { commandName: commandName, words: words },
      }).then(
        (res) => {
          return res.data;
        },
        (error) => {
          console.log("can not get explanation");
          console.log(error);
          return "";
        }
      );
      return explanation;
    },
  },
};
</script>
