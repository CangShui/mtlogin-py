import type { RouteRecordRaw } from "vue-router"
import { createRouter } from "vue-router"
import { routerConfig } from "@/router/config"
import { registerNavigationGuard } from "@/router/guard"
import { flatMultiLevelRoutes } from "./helper"

const Layouts = () => import("@/layouts/index.vue")

export const constantRoutes: RouteRecordRaw[] = [
  {
    path: "/403",
    component: () => import("@/pages/error/403.vue"),
    meta: {
      hidden: true
    }
  },
  {
    path: "/404",
    component: () => import("@/pages/error/404.vue"),
    meta: {
      hidden: true
    },
    alias: "/:pathMatch(.*)*"
  },
  {
    path: "/login",
    component: () => import("@/pages/login/index.vue"),
    meta: {
      hidden: true
    }
  },
  {
    path: "/dashboard",
    redirect: "/accounts",
    meta: {
      hidden: true
    }
  },
  {
    path: "/",
    redirect: "/accounts",
    meta: {
      hidden: true
    }
  },
  {
    path: "/accounts",
    component: Layouts,
    children: [
      {
        path: "",
        component: () => import("@/pages/accounts/index.vue"),
        name: "Accounts",
        meta: {
          title: "账户管理",
          elIcon: "UserFilled",
          affix: true
        }
      }
    ]
  },
  {
    path: "/platforms",
    component: Layouts,
    children: [
      {
        path: "",
        component: () => import("@/pages/platforms/index.vue"),
        name: "Platforms",
        meta: {
          title: "平台配置",
          elIcon: "Connection"
        }
      }
    ]
  },
  {
    path: "/notifications",
    component: Layouts,
    children: [
      {
        path: "",
        component: () => import("@/pages/notifications/index.vue"),
        name: "Notifications",
        meta: {
          title: "通知管理",
          elIcon: "Bell"
        }
      }
    ]
  },
  {
    path: "/history",
    component: Layouts,
    children: [
      {
        path: "",
        component: () => import("@/pages/history/index.vue"),
        name: "History",
        meta: {
          title: "执行记录",
          elIcon: "Document"
        }
      }
    ]
  },
  {
    path: "/settings",
    component: Layouts,
    children: [
      {
        path: "",
        component: () => import("@/pages/settings/index.vue"),
        name: "Settings",
        meta: {
          title: "系统设置",
          elIcon: "Setting"
        }
      }
    ]
  }
]

export const dynamicRoutes: RouteRecordRaw[] = []

/** 路由实例 */
export const router = createRouter({
  history: routerConfig.history,
  routes: routerConfig.thirdLevelRouteCache ? flatMultiLevelRoutes(constantRoutes) : constantRoutes
})

/** 重置路由 */
export function resetRouter() {
  try {
    // 注意：所有动态路由路由必须带有 Name 属性，否则可能会不能完全重置干净
    router.getRoutes().forEach((route) => {
      const { name, meta } = route
      if (name && meta.roles?.length) {
        router.hasRoute(name) && router.removeRoute(name)
      }
    })
  } catch {
    // 强制刷新浏览器也行，只是交互体验不是很好
    location.reload()
  }
}

// 注册路由导航守卫
registerNavigationGuard(router)
