<template>
  <div>
    <div style="text-align: center">
      <br />
      <br />
      <h1>CLchecker</h1>
      <h6>A linter for command line</h6>
      <br />
      <h6>Type/paste codes below to check bugs instantly</h6>
      <div>
        <span>Programming Language:</span>
        <select v-model="language">
          <option>shell</option>
          <option>dockerfile</option>
        </select>
      </div>
      <br />
    </div>

    <div class="editor">
      <Editor :language="language" :path="path"></Editor>
    </div>
  </div>
</template>

<script>
import axios from "axios";
import Editor from "../components/Editor.vue";

export default {
  name: "Home",
  components: {
    Editor
  },
  data() {
    return {
      language: "shell",
      // height: "400px",
      // width: "100px",
      path: "http://127.0.0.1:5001/clcheck/",
      error: {
        code: "",
        marker: ""
      },
      explanation: "",
      commandRange: {
        hello: {
          startLine: 1,
          endLine: 2,
          startColumn: 1,
          endColumn: 10
        }
      }
    };
  },

  methods: {
    clcheck(code) {
      console.log("receive the event" + code);
      axios({
        method: "POST",
        url: this.path,
        headers: { "Content-Type": "application/json" },
        data: { code: code }
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

    explain(commandName, word) {
      console.log("receive the explain event");
      axios({
        method: "POST",
        url: this.path+"explain/",
        headers: { "Content-Type": "application/json" },
        data: { commandName: commandName, key: word }
      }).then(
        res => {
          this.explanation = res.data.explanation;
        },
        error => {
          console.log("can not get explanation");
          console.log(error);
          this.explanation = "";
        }
      );
    }
  },
  created() {
    console.log("started");
  }
};
</script>

<style>
.content {
  text-align: center;
  padding: 1em;
}
.editor {
  border-color: grey;
  border-style: solid;
  height: 400px;
  width: 50%;
  margin: 0 auto;
}
</style>
