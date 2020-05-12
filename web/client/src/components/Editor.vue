<template>
  <div>
    <div v-show="language == 'dockerfile'" class="load">
      <span v-on:click="load(0)" class="example" style="margin-left=0em"
        >Loads a buggy example from one of Microsoft's repo </span
      ><a
        href="https://github.com/Azure/sonic-buildimage/issues/4458"
        target="_blank"
        style="text-decoration: none"
        >link to the issue</a
      >
      <span v-on:click="loadRandom()" class="example" style="margin-left:2em"
        >Loads a random buggy example collected from GitHub</span
      >
    </div>
    <div id="container" class="editor"></div>
    <br />
    <div style="text-align: center;">Analysis Result</div>
    <div class="output" style="font-size:85%;">
      <div v-if="outputs.length > 0">
        <div v-for="(output, index) in outputs" :key="index">
          <div style="margin-left: 0.3em;margin-top:0.7em">
            <span :style="{ color: output.color }">{{ output.type }}</span> in
            <span
              style="color:blue;cursor:pointer;text-decoration:underline"
              v-on:click="setPosition(output.line, output.col)"
            >
              {{ output.line }}:</span
            >
            <span style="margin-left: 0.5em; color: rgb(71, 71, 69);">{{
              output.commandline
            }}</span>
          </div>
          <div
            style='margin-left: 2em; color:rgb(85, 60, 23); font-family: "Consolas", "Courier New", "Monospace";margin-bottom:0.4em'
          >
            {{ output.message }}
          </div>
        </div>
      </div>
      <div v-else>
        <p style="margin-left: 0.3em;">{{ message }}</p>
      </div>
    </div>
  </div>
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

const dockerfile_all_instructions = [
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
  "workdir"
];
export { monaco };

export default {
  name: "Editor",
  props: {
    width: [String, Number],
    height: [String, Number],
    language: String,
    path: String
  },
  data() {
    return {
      editor: null,
      lruCache: new LRUCache(1),
      value: "",
      errorMarkers: [],
      explanation: "",
      commandRange: {},
      commandInfo: {},
      message:
        "The analysis result will be here. Loading for the first time may take a few seconds",
      outputs: [],
      doneAnalysis: "no"
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
    value() {
      this.editor.setValue(this.value);
    }
  },

  methods: {
    resetValue() {
      if (this.language == "shell") {
        this.value =
          "if [ 3 -gt 2 ]; \nthen\n    apt-get --assume-no install -y nodejs;\nfi;";
      } else {
        this.value = `FROM ubuntu:16.04
RUN apt-get clean -y      && \\
    apt-get autoclean -   && \\
    apt-get autoremove -y && \\
    rm -rf /debs && \\
    tar xvffile.tar
`;
      }
    },

    loadRandom() {
      const fileNumber = Math.ceil(Math.random() * 8);
      this.load(fileNumber);
    },

    load(fileNumber) {
      axios
        .get(
          `https://raw.githubusercontent.com/wangluochao902/clcheck/master/web/client/public/buggy_files/${fileNumber}.txt`
        )
        .then(response => {
          this.value = response.data;
          console.log(response);
        })
        .catch(error => console.log(error));
    },

    setPosition(lineNumber, column) {
      this.editor.setPosition({ lineNumber: lineNumber, column: column });
      this.editor.revealPositionInCenter({
        lineNumber: lineNumber,
        column: column
      });
      this.editor.focus();
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
                value: "```python\n" + expl["explanation"] + "\n```"
              }
            ]
          };
        } else {
          return {
            contents: { value: `***${words.word}*` }
          };
        }
      }
    },

    getCommandName(position) {
      //TODO: use binary search instead or a hashmap for better performance
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
        word: value.slice(i + 1, j)
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
      return position;
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
            explanation: commandInfo.explanation[Pair_key]
          };
        return null;
      }
    },

    initMonaco() {
      this.editor = monaco.editor.create(document.getElementById("container"), {
        language: this.language,
        theme: "vs",
        scrollBeyondLastLine: false,
        minimap: { enabled: false },
        value: this.value,
        hover: { delay: 300 }
      });
      this.editor.onDidChangeModelContent(() => {
        console.log("in the ondidchange", this.doneAnalysis);
        this.clcheck(this.editor.getValue());
      });
      monaco.languages.registerHoverProvider("shell", {
        provideHover: this.provideHover
      });
      monaco.languages.registerHoverProvider("dockerfile", {
        provideHover: this.provideHover
      });
    },

    clcheck(code) {
      this.commandRange = [];
      this.errorMarkers = [];
      this.outputs = [];
      var promises = [];
      if (this.language === "shell") {
        promises.push(
          new Promise(resolve => {
            this.checkshell(code, { row: 1, col: 1 }).then(resolve());
          })
        );
      } else {
        let dockerfile = DockerfileParser.parse(code);
        let instructions = dockerfile.getInstructions();
        for (let instruction of instructions) {
          const keyWord = instruction.getKeyword();
          if (
            !dockerfile_all_instructions.includes(keyWord.toLowerCase()) &&
            !keyWord.startsWith("{")
          ) {
            const range = instruction.getRange();
            const marker = {
              startLineNumber: range.start.line + 1,
              startColumn: range.start.character + 1,
              endLineNumber: range.start.line + 1,
              endColumn: keyWord.length,
              severity: monaco.MarkerSeverity.Error,
              message: `Unknow instruction "${instruction.instruction}"`
            };
            this.errorMarkers.push(marker);
            this.outputs.push({
              line: marker.startLineNumber,
              col: marker.startColumn,
              color: "red",
              type: "error",
              commandline: instruction.getTextContent(),
              message: marker.message
            });
          }
          if (instruction.getKeyword() === "RUN") {
            const range = instruction.getRange();
            const shellStartPosition = {
              row: range.start.line + 1,
              col: range.start.character + 1 + 4
            };
            const shellscript = instruction.getTextContent().slice(4);
            promises.push(
              new Promise(resolve => {
                this.checkshell(shellscript, shellStartPosition).then(
                  resolve()
                );
              })
            );
          }
        }
      }
      if (promises.length > 0) {
        Promise.all(promises).then((this.message = "No results"));
      } else this.message = "No results";
    },

    async checkshell(shellscript, shellStartPosition) {
      try {
        shellscript = shellscript.replace(/\r\n/g, "\n");
        // const shellscript = shellscript.replace('\r', '\n')
        const ast = parse(shellscript, { insertLOC: true });
        traverse(ast, {
          Command: node => {
            // have a check for `name` key. some command like redirect (when people mistakenly put it at the beginning)
            // don't have such key
            if (node.name == null) {
              console.log(node, "the command doesn't have name");
              return;
            }
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
            };
            position = this.offset_position(shellStartPosition, position);
            this.commandRange.push({
              commandName: commandName,
              start: position.start,
              end: position.end
            });
            if (this.lruCache.has(commandline)) {
              const marker = this.lruCache.get(commandline);
              if (marker != null) {
                const modifiedMarker = this.modifyMarker(
                  marker,
                  position.start
                );
                this.errorMarkers.push(modifiedMarker);
                this.outputs.push({
                  line: modifiedMarker.startLineNumber,
                  col: modifiedMarker.startColumn,
                  color:
                    modifiedMarker.severity == 8 ? "red" : "rgb(230, 141, 8)",
                  type: modifiedMarker.severity == 8 ? "error" : "warning",
                  commandline: commandline,
                  message: modifiedMarker.message
                });
              }
            } else {
              this.checkCommand(commandline, commandName).then(
                res => {
                  const commandInfo = res.data.commandInfo;
                  if (Object.keys(commandInfo).length > 0) {
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
                    var modifiedMarker = this.modifyMarker(
                      marker,
                      position.start
                    );
                    this.errorMarkers.push(modifiedMarker);
                    this.outputs.push({
                      line: modifiedMarker.startLineNumber,
                      col: modifiedMarker.startColumn,
                      color:
                        modifiedMarker.severity == 8
                          ? "red"
                          : "rgb(230, 141, 8)",
                      type: modifiedMarker.severity == 8 ? "error" : "warning",
                      commandline: commandline,
                      message: modifiedMarker.message
                    });
                    console.log(this.outputs);
                  }
                },
                error => {
                  console.log("can not access");
                  console.log(error);
                }
              );
            }
          }
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
            severity: monaco.MarkerSeverity.Error
          };
          this.errorMarkers.push(marker);
          this.outputs.push({
            line: lineNumber,
            col: marker.startColumn,
            color: "red",
            type: "error",
            commandline: this.editor.getModel().getLineContent(lineNumber),
            message: marker.message
          });
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
        data: { commandline: commandline, commandName: commandName }
      });
    }
  }
};
</script>
<style>
.editor {
  border-color: grey;
  border-style: solid;
  width: 60%;
  height: 400px;
  margin: 0 auto;
}
.output {
  border-color: gray;
  border-style: solid;
  width: 60%;
  margin: 0 auto;
  background-color: rgb(245, 243, 240);
}
.load {
  width: 60%;
  margin: 0 auto;
  margin-bottom: 0.2em;
  color: grey;
}
.example {
  cursor: pointer;
}
span.example:hover {
  color: blue;
}
span.lineNumber:hover {
  color: blue;
}
</style>
