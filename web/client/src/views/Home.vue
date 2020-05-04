<template>
  <div>
    <div style="text-align: center">
      <h1>CLcheck</h1>
      <p>A linter for command line. Type/paste codes below to check bugs instantly</p>
      <div>
        <span>Programming Language:</span>
        <select v-model="language">
          <option>dockerfile</option>
          <option>shell</option>
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
import Editor from "../components/Editor.vue";

export default {
  name: "Home",
  components: {
    Editor,
  },
  data() {
    return {
      language: "shell",
      // height: "400px",
      // width: "100px",
      path: "http://127.0.0.1:5000/clcheck/",
      error: {
        code: "",
        marker: "",
      },
      explanation: "",
      commandRange: {
        hello: {
          startLine: 1,
          endLine: 2,
          startColumn: 1,
          endColumn: 10,
        },
      },
    };
  },

  methods: {},
  created() {
    console.log("started");
  },
};
</script>

<style>
.clcheckcontent {
  text-align: center;
  padding: 1em;
}
.editor {
  border-color: grey;
  border-style: solid;
  height: 600px;
  width: 70%;
  margin: 0 auto;
}
</style>
