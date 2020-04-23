<template>
  <div id="container" style="width: 100%; height: 100%;"></div>
</template>

<script>
import * as monaco from "monaco-editor/esm/vs/editor/editor.api";
import axios from "axios";

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
      value:
        "if [ 3 -gt 2 ]; \nthen\n    apt-get --assume-no install -y nodejs;\nfi;",
      error: {
        code: "",
        marker: ""
      },
      explanation: "",
      commandRange: {}
    };
  },

  mounted() {
    this.initMonaco();
  },

  watch: {
    error() {
      // if the value in the editor is not updated, we will report the error
      // otherwise just discard the error
      console.log("error changed");
      if (this.error.code == this.editor.getValue()) {
        let markers = this.error.markers;
        console.log(markers);
        for (let i = 0; i < markers.length; i++) {
          //convert severity to monaco.MarkerSeverity
          markers[i].severity = monaco.MarkerSeverity[markers[i].severity];
        }
        console.log("after", markers);
        monaco.editor.setModelMarkers(this.editor.getModel(), "test", markers);
      }
    },
    language() {
      console.log(this.language);
      monaco.editor.setModelLanguage(this.editor.getModel(), this.language);
      if (this.language == "shell"){
        this.value = "if [ 3 -gt 2 ]; \nthen\n    apt-get --assume-no install -y nodejs;\nfi;"
      } else{
        this.value = "FROM ubuntu:16.04\nRUN apt-get --assume-no install -qqy nodejs\n"
      }
    },
    explanation() {},
    value(){
      this.editor.setValue(this.value)
    }
  },

  methods: {
    provideHover(model, position) {
      console.log("new");
      console.log(position)
      console.log('the command_range is')
      console.log(this.commandRange)
      let commandName = this.getCommandName(position);
      if (commandName != null) {
        const word = this.getWord(model, position);
        console.log(word + "  is the word");
        return this.explain(commandName, word).then(explanation => {
          if (explanation != "") {
            console.log("this is the explanation: " + explanation);
            return {
              range: new monaco.Range(
                1,
                1,
                position.lineNumber,
                position.column
              ),
              contents: [
                { value: `**${word}**` },
                {
                  value: explanation
                }
              ]
            };
          }
        });
      }
    },

    getCommandName(position) {
      for (const commandName in this.commandRange) {
        if (
          position.lineNumber >= this.commandRange[commandName]["startLine"] &&
          position.lineNumber <= this.commandRange[commandName]["endLine"] &&
          position.column >= this.commandRange[commandName]["startColumn"] &&
          position.column <= this.commandRange[commandName]["endColumn"]
        ) {
          return commandName;
        }
      }
      return null;
    },

    getWord(model, position) {
      const value = model.getLineContent(position.lineNumber);
      console.log("value is" + value);
      let i = position.column - 1;
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
      return value.slice(i + 1, j);
    },

    initMonaco() {
      this.editor = monaco.editor.create(document.getElementById("container"), {
        language: this.language,
        theme: "vs",
        scrollBeyondLastLine: false,
        minimap: { enabled: false },
        value: this.value
      });
      this.editor.onDidChangeModelContent(() => {
        this.reset_error()
        this.clcheck(this.editor.getValue());
        console.log(this.editor.getValue().length);
      });
      monaco.languages.registerHoverProvider("shell", {
        provideHover: this.provideHover
      });
      monaco.languages.registerHoverProvider("dockerfile", {
        provideHover: this.provideHover
      });
    },

    reset_error(){
      this.error = {
        code: "",
        marker: ""
      };
    },

    clcheck(code) {
      console.log("receive the event" + code);
      axios({
        method: "POST",
        url: this.path,
        headers: { "Content-Type": "application/json" },
        data: { code: code, language: this.language }
      }).then(
        res => {
          console.log("inside axios");
          console.log(res);
          this.error = res.data.error;
          console.log(res.data.commandRange);
          this.commandRange = res.data.commandRange;
          console.log(this.commandRange);
          console.log("end axios");
        },
        error => {
          console.log("can not access");
          console.log(error);
          this.error = {
            code: "",
            marker: ""
          };
          this.commandRange = {};
        }
      );
    },

    async explain(commandName, word) {
      console.log("receive the explain event");
      let explanation = await axios({
        method: "POST",
        url: this.path + "explain/",
        headers: { "Content-Type": "application/json" },
        data: { commandName: commandName, key: word }
      }).then(
        res => {
          return res.data.explanation;
        },
        error => {
          console.log("can not get explanation");
          console.log(error);
          return "";
        }
      );
      return explanation;
    }
  }
};
</script>
