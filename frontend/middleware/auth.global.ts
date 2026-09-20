export default defineNuxtRouteMiddleware(async (to) => {
  const auth = useAuth()
  if (!auth.initialized.value) await auth.refresh()

  if (to.path === '/login') {
    if (auth.session.value) return navigateTo('/')
    return
  }
  if (!auth.session.value) {
    return navigateTo({ path: '/login', query: { redirect: to.fullPath } })
  }
})
