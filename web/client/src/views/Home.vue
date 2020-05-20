<template>
  <div>
    <div style="text-align: center">
      <h1 style="margin-bottom: 0em;">
        CLcheck
        <a
          href="https://github.com/wangluochao902/clcheck"
          class="fa fa-github"
          style="color: blue; font-size:50%; text-decoration: none"
          target="_blank"
          >GitHub</a
        >
      </h1>
      <p style="margin-top: 0.2em;margin-bottom:0.6em">
        check errors in command lines of dockerfile or shell script
      </p>
      <div>
        <span>Programming Language:</span>
        <select v-model="language">
          <option>dockerfile</option>
          <option>shell</option>
        </select>
      </div>
      <br />
    </div>

    <div>
      <Editor :language="language" :path="path"></Editor>
    </div>
    <br />
    <div style="text-align:left">
      <div style="margin:0 auto;width:51%;">
        <h3 style="text-align:center;margin-top:0.3em;margin-bottom:0.2em">
          Why CLcheck?
        </h3>
        <ul style="margin-top:0.1em">
          <li>
            A large portion of codes in Dockerfile and Shell script are command
            lines like <i>`apt-get install ...`</i>. However, the well-known
            tool <a href="https://www.shellcheck.net">ShellSheck</a> does not
            have rules for command lines, assuming all of them are correct!
          </li>
          <li>
            We design a domain specific language
            <span style="font-weight:bold">Eman</span> to specify the grammar
            that a shell command should follow. Here is an example of Eman.
            <a
              href="https://raw.githubusercontent.com/wangluochao902/clcheck/master/eman/apt-get.eman"
              >apt-get.eman</a
            >. Compared with its original manual
            <a
              href="https://raw.githubusercontent.com/wangluochao902/clcheck/master/eman/apt-get.txt"
              >apt-get.man</a
            >, the structure is similar, making creating a new Eman faster.
            Association Rules Mining and NLP techniques can help mining rules.
          </li>
          <li>
            CLcheck is based on Eman, emitting errors when rules in a Eman are
            violated.
          </li>
          <li>
            CLcheck is conservative. We use Dockerfiles in top stared 100,000
            GitHub repositories to test against the tool. The Eman or CLcheck
            will be modified when a false positive occurs. Some true positves
            (real bugs) are listed in the example above.
          </li>
          <li>
            Hovering over a supported command (like apt-get) and its options
            will pop out useful information.
          </li>
          <li>
            Current supported commands are `apt-get`, `tar`, `cd`, `cp`, `rm`,
            `chown`, `chmod`, `groupadd`, `mkdir`, `mv`.
          </li>
          <li>
            Commands working in progress are `echo`, `curl`, `make`, `git`,
            `apk` etc.
          </li>
        </ul>
        <h4 style="text-align:center">
          Useful? Please let us know by giving us a star at
          <a
            href="https://github.com/wangluochao902/clcheck"
            class="fa fa-github"
            style="color: blue; font-size:100%; text-decoration: none"
            target="_blank"
            >GitHub</a
          >.
        </h4>
        <h4 style="text-align:center">
          Visit other projects at
          <a href="https://smart-scripts.org" target="_blank"
            >smart-scripts.org</a
          >.
        </h4>
        <p style="font-size:60%; text-align:left">
          © 2020 wangluochao All Rights Reserved
        </p>
      </div>
    </div>
  </div>
</template>

<script src="https://use.fontawesome.com/8108a8e12c.js"></script>
<script>
import Editor from "../components/Editor.vue";
export default {
  name: "Home",
  components: {
    Editor
  },
  data() {
    return {
      language: "dockerfile",
      path:
        process.env.NODE_ENV === "production"
          ? "https://darpa-jeff.uc.r.appspot.com/clcheck/"
          : "http://127.0.0.1:5000/clcheck/"
    };
  },

  methods: {},
  created() {
    console.log("started");
  }
};
</script>
