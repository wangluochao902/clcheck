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
      lruCache: new LRUCache(10),
      value: "",
      errorMarkers: [],
      explanation: "",
      commandRange: {},
      commandInfo: {},
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
      this.resetValue();
      this.lruCache = new LRUCache(10);
    },
    explanation() {},
    value() {
      this.editor.setValue(this.value);
    },
  },

  methods: {
    resetValue() {
      if (this.language == "shell") {
        this.value =
          "if [ 3 -gt 2 ]; \nthen\n    apt-get --assume-no install -y nodejs;\nfi;";
      } else {
        this.value =
          `FROM ubuntu:16.04
RUN apt-get clean -y      && \\
    apt-get autoclean -   && \\
    apt-get autoremove -y && \\
    rm -rf /debs && \\
    tar xvffile.tar
`;
      }
    },

    provideHover(model, position) {
      console.log("new");
      console.log(position);
      console.log("the command_range is");
      console.log(this.commandRange);
      let commandName = this.getCommandName(position);
      if (commandName != null) {
        const words = this.getWords(model, position);
        console.log(words + "  is the word");
        var expl = this.find_explanation(commandName, words.word);
        if (expl == null) {
          expl = this.find_explanation(commandName, words.char);
        }
        if (expl != null) {
          return {
            contents: [
              { value: `**${expl["found_key"]}**` },
              {
                value: "```python\n" + expl["explanation"] + "\n```",
              },
            ],
          };
        } else {
          return {
            contents: { value: `***${words.word}*` },
          };
        }
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

    offset_position(start, position) {
      if (position.start.row == 1) {
        position.start.col += start.col - 1;
      }
      if (position.end.row == 1) {
        position.end.col += start.col - 1;
      }
      position.start.row += start.row - 1;
      position.end.row += start.row - 1;
      return position
    },

    modifyMarker(marker, start) {
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
    },

    find_explanation(commandName, word) {
      const commandInfo = this.commandInfo[commandName];
      if (commandInfo != null) {
        var Pair_key = null;
        var found_key = word;
        if (word in commandInfo["explanation_key_to_ExplanationPair_key"])
          Pair_key =
            commandInfo["explanation_key_to_ExplanationPair_key"][word];
        else if (word in commandInfo["option_keys_to_OptionPair_key"])
          Pair_key = commandInfo["option_keys_to_OptionPair_key"][word];
        else if ("-" + word in commandInfo["option_keys_to_OptionPair_key"]) {
          found_key = "-" + word;
          Pair_key = commandInfo["option_keys_to_OptionPair_key"][found_key];
        }
        if (Pair_key != null)
          return {
            found_key: found_key,
            explanation: commandInfo.explanation[Pair_key],
          };
        return null;
      }
    },

    initMonaco() {
      this.editor = monaco.editor.create(document.getElementById("container"), {
        language: this.language,
        theme: "vs",
        scrollBeyondLastLine: true,
        minimap: { enabled: false },
        value: this.value,
        hover: { delay: 300 },
      });
      this.editor.onDidChangeModelContent(() => {
        this.clcheck(this.editor.getValue());
        console.log(this.editor.getValue().length);
      });
      this.resetValue();
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
            var start = node.loc.start;
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
            const commandline = shellscript.slice(start.char, end.char + 1);
            var position = {
              start: start,
              end: end
            }
            position = this.offset_position(shellStartPosition, position);
            this.commandRange.push({
              commandName: commandName,
              start: position.start,
              end: position.end,
            });
            if (this.lruCache.has(commandline)) {
              const marker = this.lruCache.get(commandline);
              if (marker != null) {
                const modifiedMarker = this.modifyMarker(
                  marker,
                  position.start
                );
                this.errorMarkers.push(modifiedMarker);
              }
            } else {
              this.checkCommand(commandline, commandName).then(
                (res) => {
                  const commandInfo = res.data.commandInfo;
                  if (commandInfo.length > 0) {
                    this.commandInfo[commandName] = commandInfo;
                  }
                  const marker = res.data.marker;
                  if (marker != null) {
                    const severityCode = monaco.MarkerSeverity[marker.severity];
                    console.assert(
                      severityCode != null,
                      "marker.severty should be one of `Error`, `Warning`, `Info`, `Hint`"
                    );
                    marker.severity = severityCode;
                    console.log("this is the marker");
                    console.log(marker);
                    this.lruCache.put(commandline, marker);
                    const modifiedMarker = this.modifyMarker(
                      marker,
                      position.start
                    );
                    this.errorMarkers.push(modifiedMarker);
                  }
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
