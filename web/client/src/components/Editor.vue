<template>
  <div>
    <div v-show="language == 'dockerfile'" class="load">
      <span v-on:click="load(0)" class="example" style="margin-left=0em"
        >Loads a buggy example detected by this tool in Microsoft's repo </span
      ><a
        href="https://github.com/Azure/sonic-buildimage/issues/4458"
        target="_blank"
        style="text-decoration: none"
        >link</a
      >
      <span v-on:click="loadRandom()" class="example" style="margin-left:2em"
        >Loads a random buggy example detected by this tool from GitHub</span
      >
    </div>
    <div id="container" class="editor"></div>
    <br />
    <div style="text-align: center;">Analysis Result</div>
    <div class="output" style="font-size:85%;">
      <p style="margin-left: 0.3em;margin-top:0.5em;margin-bottom:0em">
        {{ message }}
      </p>
      <div v-show="outputs.length == 0" style="margin-top:0.5em"></div>
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
  </div>
</template>

<script>
import * as monaco from "monaco-editor/esm/vs/editor/editor.api";
import axios from "axios";
import * as utils from "./utils.js";
import { LRUCache } from "./LRUcache.js";
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
      AllCommandInfo: {},
      message:
        "The analysis result will be here. Loading for the first time may take a few seconds",
      outputs: []
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
      let commandName = this.getCommandName(position);
      if (commandName != null) {
        const words = utils.getWords(model, position);
        console.log(words + "  is the word");
        var expl = utils.find_explanation(
          this.AllCommandInfo,
          commandName,
          words.word
        );
        if (expl == null) {
          expl = utils.find_explanation(
            this.AllCommandInfo,
            commandName,
            words.char
          );
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
      const l = [position.lineNumber, position.column];
      if (Object.keys(this.commandRange).length > 0) {
        for (const command of this.commandRange) {
          if (
            utils.isSmallerOrEqual(
              [command["start"]["row"], command["start"]["col"]],
              l
            ) &&
            utils.isSmallerOrEqual(l, [
              command["end"]["row"],
              command["end"]["col"]
            ])
          ) {
            return command.commandName;
          }
        }
      }
      return null;
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
        this.outputs = [];
        this.message =
          "Analyzing...(loading for the first time may take a few seconds)";
        utils
          .clcheck(
            this.editor.getValue(),
            this.language,
            this.AllCommandInfo,
            this.lruCache,
            this.path
          )
          .then(res => {
            if (res.outputs.length == 0) {
              this.message = "No problems detected!";
            } else {
              this.message = "Done analysis!";
              this.outputs = res.outputs;
              this.errorMarkers = res.errorMarkers;
              this.commandRange = res.commandRange;
            }
          });
      });
      monaco.languages.registerHoverProvider("shell", {
        provideHover: this.provideHover
      });
      monaco.languages.registerHoverProvider("dockerfile", {
        provideHover: this.provideHover
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
  font-size: 95%;
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
