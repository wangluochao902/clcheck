<template>
  <div id="container" style="width: 100%; height: 100%;"></div>
</template>

<script>
import * as monaco from "monaco-editor/esm/vs/editor/editor.api";

export { monaco };

export default {
  name: "Editor",
  props: {
    width: [String, Number],
    height: [String, Number],
    error: Object,
    language: String
  },
  data() {
    return {
      editor: null
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
    }
  },

  methods: {
    initMonaco() {
      this.editor = monaco.editor.create(document.getElementById("container"), {
        language: this.language,
        theme: "vs",
        scrollBeyondLastLine: false,
        minimap: { enabled: false }
      });
      this.editor.onDidChangeModelContent(() => {
        this.$emit("clcheck", this.editor.getValue());
        console.log(this.editor.getValue().length)
      });
    }
  }
};
</script>
