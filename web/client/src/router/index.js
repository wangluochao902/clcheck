import Vue from "vue";
import VueRouter from "vue-router";
import Home from "../views/Home.vue";
import Report from "../views/Report.vue";
import Bugs from "../views/Bugs.vue";
import CLcheck from "../views/CLcheck.vue";
// import BootstrapVue from 'bootstrap-vue'

// import 'bootstrap/dist/css/bootstrap.css'
// import 'bootstrap-vue/dist/bootstrap-vue.css'

Vue.use(VueRouter);
// Vue.use(BootstrapVue)

const routes = [
  {
    path: "/",
    name: "Home",
    component: Home,
    children: [
      {
        path: "",
        name: "CLcheck",
        component: CLcheck
      },
      {
        path: "report",
        name: "Report",
        component: Report
      },
      {
        path: "bugs",
        name: "Bugs",
        component: Bugs
      }
    ]
  }
];

const router = new VueRouter({
  mode: "history",
  base: process.env.BASE_URL,
  routes
});

export default router;
