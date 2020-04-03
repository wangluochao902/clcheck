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
      <Editor :error="error" :language="language" @clcheck="clcheck"></Editor>
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
      path: "http://127.0.0.1:5000/clcheck/",
      error: {
        code: "",
        marker: ""
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
          this.error = res.data;
        },
        error => {
          console.log("can not access");
          console.log(error);
          this.error = {
            code: "",
            marker: ""
          };
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
