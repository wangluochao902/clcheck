<template>
  <div>
    <br />
    <h3 style="text-align: center;">Report</h3>
    <button
      style="text-align: center;margin:0 auto;display: flex;margin-bottom:2em"
      v-on:click="runAllDockerfile()"
    >
      Check all dockerfiles in GitHub
    </button>
    <!-- <button
            style="text-align: center;margin:0 auto;display: flex;margin-bottom:2em"
            v-on:click="runAndSave()"
        >
            Check all dockerfiles and save to local
        </button> -->
    <div class="result" style="font-size:100%;">
      <p
        v-show="done"
        style="margin-left: 0.3em;margin-top:0.5em;margin-bottom:0em"
      >
        {{ message }}
      </p>
      <p style="margin-left: 0.3em;margin-top:0.5em;margin-bottom:0em">
        {{ finished }}
      </p>
      <div v-for="(outputsInfo, outerIndex) in allOutputs" :key="outerIndex">
        <div>
          <div>
            <div style="display:inline">
              ObjectId Index: {{ outputsInfo.objectIdIndex }}

              <button
                style="margin-left:3em"
                v-on:click="flipDockerfile(outerIndex)"
              >
                {{ show[outerIndex] ? "Hide" : "Show" }} Dockerfile
              </button>

              <button
                style="margin-left:3em"
                v-on:click="addToUnknown(outputsInfo)"
              >
                add to unknown
              </button>
              <button
                style="margin-left:3em"
                v-on:click="addToBug(outputsInfo)"
              >
                add to bug collection
              </button>
              <button
                style="margin-left:3em"
                v-on:click="deleteFromBug(outputsInfo.objectIdIndex)"
              >
                delete from bug collection
              </button>
              <button
                style="margin-left:3em"
                v-on:click="addToSkipped(outputsInfo)"
              >
                add to skipped
              </button>
            </div>
            <div>
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
            <div>
              In Repo:
              <a
                :href="'https://github.com/' + outputsInfo.repository"
                target="_blank"
                >{{ outputsInfo.repository }}</a
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
          style="display: flex; margin:0 auto;text-align:center"
          v-on:click="flipOutput(outerIndex)"
        >
          {{ showOutput[outerIndex] ? "Hide" : "Show" }} Output
        </button>
        <div
          style="border:solid grey;width:95%;margin:0 auto;margin-top:0.4em;margin-bottom:2em"
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
    </div>
  </div>
</template>
<script>
import * as utils from "../helper/utils.js";
import { LRUCache } from "../helper/LRUcache.js";
import { runAndSave } from "../helper/runAndSave.js";
import Swal from "sweetalert2";
import Vue from "vue";
import * as monaco from "monaco-editor/esm/vs/editor/editor.api";

export default {
  name: "Report",
  data() {
    return {
      path:
        process.env.NODE_ENV === "production"
          ? "https://darpa-jeff.uc.r.appspot.com/clcheck/"
          : "http://127.0.0.1:5000/clcheck/",
      allOutputs: [],
      message: "Done analysis!",
      clicked: false,
      show: [],
      showOutput: [],
      dockerfiles: [],
      lruCache: new LRUCache(20),
      done: false,
      finished: 0,
      created: null
    };
  },

  methods: {
    flipDockerfile(outerIndex) {
      this.show[outerIndex] = !this.show[outerIndex];
      Vue.set(this.show, outerIndex, this.show[outerIndex]);
      if (this.created == null) {
        this.created = new Array(this.dockerfiles.length).fill(false);
      }
      if (!this.created[outerIndex]) {
        Vue.nextTick(() => {
          const editor = monaco.editor.create(
            document.getElementById("editor" + outerIndex),
            {
              language: "dockerfile",
              theme: "vs",
              scrollBeyondLastLine: false,
              minimap: { enabled: false },
              value: this.dockerfiles[outerIndex],
              hover: { delay: 300 }
            }
          );
          editor.layout();
          this.created[outerIndex] = true;
        });
      }
    },

    flipOutput(outerIndex) {
      this.showOutput[outerIndex] = !this.showOutput[outerIndex];
      Vue.set(this.showOutput, outerIndex, this.showOutput[outerIndex]);
    },

    showAllBugs() {
      utils.getBugs(this.path).then(res => {
        const bugs = res.data.bugs;
        var finished = 0;
        var nums = bugs.length;
        for (let i of bugs) {
          checkDockerfileById(
            this.path,
            i,
            this.show,
            this.dockerfiles,
            this.lruCache,
            this.allOutputs
          ).then(() => {
            nums = nums - 1;
            finished = finished + 1;
            if (nums == 0) this.done = true;
            if (finished % 20 == 0) this.finished = finished;
          });
        }
      });
    },

    runAllDockerfile() {
      this.clicked = true;
      runAllDockerfile(this, 17840, 100);
    },

    addToSkipped(details) {
      utils
        .addToSkipped(this.path, details)
        .then(
          Swal.fire(
            "Success!",
            "You just added this dockerfile to skipped collection",
            "success"
          )
        );
    },

    addToUnknown(details) {
      utils
        .addToUnknown(this.path, details)
        .then(
          Swal.fire(
            "Success!",
            "You just added this dockerfile to unknown collection",
            "success"
          )
        );
    },

    addToBug(details) {
      utils
        .addToBug(this.path, details)
        .then(
          Swal.fire(
            "Success!",
            "You just added this dockerfile to bug collection",
            "success"
          )
        );
    },

    deleteFromBug(objectIdIndex) {
      utils.deleteFromBug(this.path, objectIdIndex);
    },

    runAndSave() {
      runAndSave();
    }
  },
  created() {
    console.log("started");
  }
};

async function checkDockerfileById(
  path,
  i,
  show,
  showOutput,
  dockerfiles,
  lruCache,
  allOutputs
) {
  let res = await utils.getDockerfile(path, i).then(responce => {
    if (
      responce.data.file.endsWith(".js") ||
      responce.data.file.endsWith(".j2") ||
      responce.data.file.endsWith(".vim") ||
      responce.data.file.endsWith(".ejs") ||
      responce.data.file.endsWith(".yaml") ||
      responce.data.file.endsWith(".yml") ||
      responce.data.file.endsWith(".rb") ||
      responce.data.file.endsWith(".erb") ||
      responce.data.file.endsWith(".java") ||
      responce.data.file.endsWith(".py") ||
      responce.data.file.endsWith(".kak") ||
      responce.data.file.endsWith(".patch") ||
      responce.data.file.endsWith(".ftl") ||
      responce.data.file.endsWith(".json") ||
      responce.data.file.endsWith(".c") ||
      responce.data.file.endsWith(".php") ||
      responce.data.file.endsWith(".tar") ||
      responce.data.file.endsWith(".nanorc") ||
      responce.data.file.endsWith(".h") ||
      responce.data.file.endsWith(".cpp") ||
      responce.data.file.endsWith(".lua") ||
      responce.data.file.endsWith(".go") ||
      responce.data.file.includes("window") ||
      responce.data.file.endsWith(".sh") ||
      responce.data.file.endsWith(".rst") ||
      responce.data.file.endsWith(".template") ||
      responce.data.file.endsWith(".tmLanguage") ||
      responce.data.file.endsWith(".md")
    ) {
      return null;
    }
    return utils
      .clcheck(responce.data.code, "dockerfile", [], lruCache, path)
      .then(res => {
        return { data: responce.data, checkResults: res };
      });
  });
  if (res != null && res.checkResults.outputs.length > 0) {
    show.push(false);
    showOutput.push(true);
    dockerfiles.push(res.data.code);
    allOutputs.push({
      repository: res.data.repository,
      file: res.data.file,
      outputs: res.checkResults.outputs,
      objectIdIndex: i
    });
  }
}

async function runAllDockerfile(vm, start, num_batch) {
  let res = await utils.getSkipped(vm.path);
  const skipped = res.data.skipped_index;
  const unknown_index = await utils.getUnknown(vm.path).then(res => {
    return res.data.unknown_index;
  });
  const batch_size = 80;
  for (var b = 0; b < num_batch; b++) {
    var promises = [];
    for (let i = 0; i < batch_size; i++) {
      const objectIdIndex = start + b * batch_size + i;
      if (
        skipped.includes(objectIdIndex) ||
        unknown_index.includes(objectIdIndex)
      )
        continue;
      promises.push(
        checkDockerfileById(
          vm.path,
          objectIdIndex,
          vm.show,
          vm.showOutput,
          vm.dockerfiles,
          vm.lruCache,
          vm.allOutputs
        )
      );
    }
    let res = await Promise.all(promises);
    if (res == 0) console.log(res);
    if ((b + 1) % 1 == 0) vm.finished = (b + 1) * batch_size;
    if (vm.allOutputs.length > 30) {
      console.log(vm.allOutputs.length);
      break;
    }
  }
  vm.done = true;
}
</script>
<style>
.result {
  border-color: gray;
  border-style: solid;
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
</style>
