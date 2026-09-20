<script setup lang="ts">
import { errorMessage } from '~/composables/useLedger'

const auth = useAuth()
const route = useRoute()
const username = ref('')
const password = ref('')
const busy = ref(false)
const error = ref('')
const showPassword = ref(false)

function safeRedirect(value: unknown) {
  const target = typeof value === 'string' ? value : '/'
  return target.startsWith('/') && !target.startsWith('//') && !target.includes('://') ? target : '/'
}

async function submit() {
  if (busy.value) return
  busy.value = true
  error.value = ''
  try {
    await auth.login(username.value, password.value)
    await navigateTo(safeRedirect(route.query.redirect))
  } catch (cause) {
    error.value = errorMessage(cause)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <main class="auth-page" aria-labelledby="login-title">
    <UContainer class="w-full max-w-md">
      <UCard>
        <template #header>
          <div class="space-y-2">
            <p class="text-sm text-muted">PocketTally</p>
            <h1 id="login-title" class="text-2xl font-semibold text-highlighted">登录个人账本</h1>
            <p class="text-sm text-muted">请输入所有者凭据继续。</p>
          </div>
        </template>
        <form class="space-y-5" @submit.prevent="submit">
          <UAlert v-if="error" color="error" variant="soft" icon="i-lucide-circle-alert" title="登录失败" :description="error" role="alert" />
          <UFormField label="用户名" name="username">
            <UInput v-model="username" autocomplete="username" autofocus class="w-full" :disabled="busy" />
          </UFormField>
          <UFormField label="密码" name="password">
            <UInput v-model="password" :type="showPassword ? 'text' : 'password'" autocomplete="current-password" class="w-full" :disabled="busy">
              <template #trailing>
                <UButton color="neutral" variant="ghost" size="xs" :icon="showPassword ? 'i-lucide-eye-off' : 'i-lucide-eye'" :aria-label="showPassword ? '隐藏密码' : '显示密码'" @click="showPassword = !showPassword" />
              </template>
            </UInput>
          </UFormField>
          <UButton type="submit" block label="登录" :loading="busy" :disabled="!username || !password" />
        </form>
      </UCard>
    </UContainer>
  </main>
</template>
