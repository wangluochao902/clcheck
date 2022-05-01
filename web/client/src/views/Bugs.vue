<template>
  <div>
    <br />
    <h3 style="text-align: center;">Bugs found using CLcheck</h3>
    <div class="result" style="font-size:100%;">
      <br />
      <div v-for="(outputsInfo, outerIndex) in allOutputs" :key="outerIndex">
        <div>
          <div style="margin-top:1em;margin-left:3em">
            <div class="repoDetail" style="display:inline">
              Dockerfile Index: {{ outerIndex + 1 }}

              <button
                style="margin-left:3em"
                v-on:click="flipDockerfile(outerIndex)"
              >
                {{ show[outerIndex] ? "Hide" : "Show" }} Dockerfile
              </button>
            </div>
            <button class="repoDetail">
              <a :href="outputsInfo.issueLink" target="_blank">Github Issue</a>
            </button>
            <div class="repoDetail">
              In Repo:
              <a
                :href="'https://github.com/' + outputsInfo.repository"
                target="_blank"
                >{{ outputsInfo.repository }}</a
              >
            </div>
            <div class="repoDetail">
              In File:
              <a
                :href="
                  'https://github.com/' +
                    outputsInfo.repository +
                    '/blob/master/' +
                    outputsInfo.file
                "
                target="_blank"
                >{{ outputsInfo.file }}</a
              >
            </div>
          </div>
          <div
            v-show="show[outerIndex]"
            :id="'editor' + outerIndex"
            class="dockerfile"
          ></div>
        </div>
        <button
          style="display: flex; margin:0 auto;text-align:center;margin-top:0.5em"
          v-on:click="flipOutput(outerIndex)"
        >
          {{ showOutput[outerIndex] ? "Hide" : "Show" }} Output
        </button>
        <div
          style="border:solid grey;width:90%;margin:0 auto;margin-top:0.4em;margin-bottom:2em;margin-left:3em"
        >
          <div
            v-show="showOutput[outerIndex]"
            v-for="(output, index) in outputsInfo.outputs"
            :key="index"
          >
            <div style="margin-left: 0.3em;margin-top:0.7em">
              <span :style="{ color: output.color }">{{ output.type }}</span>
              on
              <span
                style="color:blue;cursor:pointer;text-decoration:underline"
                v-on:click="setPosition(outerIndex, output.line, output.col)"
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
        <hr style="margin-top:1em;margin-bottom:1em" />
      </div>
    </div>
  </div>
</template>
<script>
import * as utils from "../helper/utils.js";
import Vue from "vue";
import * as monaco from "monaco-editor/esm/vs/editor/editor.api";

export default {
  name: "Bugs",
  data() {
    return {
      path: process.env.VUE_APP_CLCHECKER_URI,
      allOutputs: [],
      message: "Done analysis!",
      clicked: false,
      show: [],
      showOutput: [],
      editors: []
    };
  },

  methods: {
    flipDockerfile(outerIndex) {
      this.show[outerIndex] = !this.show[outerIndex];
      Vue.set(this.show, outerIndex, this.show[outerIndex]);
    },

    flipOutput(outerIndex) {
      this.showOutput[outerIndex] = !this.showOutput[outerIndex];
      Vue.set(this.showOutput, outerIndex, this.showOutput[outerIndex]);
    },

    showAllBugs() {
      utils.getVerifiedBugs(this.path).then(res => {
        this.allOutputs = res.data.contents;
        const important = [46111, 136961, 40221, 21596];
        const left = [];
        const right = [];
        for (let out of this.allOutputs) {
          if (important.includes(out.objectIdIndex)) {
            left.push(out);
          } else right.push(out);
        }
        this.allOutputs = left.concat(right);
        for (let i = 0; i < this.allOutputs.length; i++) {
          this.show.push(true);
          this.showOutput.push(true);
          Vue.nextTick(() => this.createEditor(i));
        }
      });
    },

    setPosition(index, lineNumber, column) {
      this.editors[index].setPosition({
        lineNumber: lineNumber,
        column: column
      });
      this.editors[index].revealPositionInCenter({
        lineNumber: lineNumber,
        column: column
      });
      this.editors[index].focus();
    },

    createEditor(index) {
      const editor = monaco.editor.create(
        document.getElementById("editor" + index),
        {
          language: "dockerfile",
          theme: "vs",
          scrollBeyondLastLine: false,
          minimap: { enabled: false },
          value: this.allOutputs[index].value,
          hover: { delay: 300 },
          readOnly: true
        }
      );
      editor.layout();
      this.editors.push(editor);
    }
  },
  created() {
    console.log("started");
    this.showAllBugs();
  }
};
</script>
<style>
.result {
  border-color: gray;
  border-style: none;
  width: 70%;
  margin: 0 auto;
  background-color: rgb(245, 243, 240);
}
.dockerfile {
  border: solid;
  margin-left: 3em;
  margin-top: 0.3em;
  width: 90%;
  height: 400px;
  display: flex;
  border-color: rgb(156, 154, 154);
}
.repoDetail {
  margin-left: 0.2em;
}
</style>
