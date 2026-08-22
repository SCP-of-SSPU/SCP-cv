<script setup lang="ts">
/**
 * 登录页：username + password 表单。
 *  - 单页 Card 布局，居中 360px；移动端撑满；
 *  - 表单走 Pinia auth store；
 *  - 登录成功后跳转 query.redirect 指定路径，否则回 /dashboard。
 */
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute, useRouter } from 'vue-router';
import { NAlert, NButton, NCard, NForm, NFormItem, NInput } from 'naive-ui';

import { useToast } from '@/composables/useToast';
import { useAuthStore } from '@/stores/auth';
import FIcon from '@/design-system/FIcon.vue';

const { t } = useI18n();
const route = useRoute();
const router = useRouter();
const toast = useToast();
const auth = useAuthStore();

const username = ref('admin');
const password = ref('');
const submitting = ref(false);
const errorMessage = ref('');

const redirectTarget = computed<string>(() => {
  const raw = route.query.redirect;
  if (typeof raw === 'string' && raw.startsWith('/') && raw !== '/login') return raw;
  return '/dashboard';
});

async function submit(): Promise<void> {
  errorMessage.value = '';
  if (!username.value.trim() || !password.value) {
    errorMessage.value = t('auth.loginFail');
    return;
  }
  submitting.value = true;
  try {
    const user = await auth.login(username.value.trim(), password.value);
    toast.success(t('auth.loginSuccess', { name: user.username }));
    await router.replace(redirectTarget.value);
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : t('auth.loginFail');
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <main class="login-view">
    <div class="login-view__brand">
      <span class="login-view__brand-mark" aria-hidden="true">
        <FIcon name="tv_24_regular" :size="28" />
      </span>
    </div>
    <n-card class="login-view__card" :title="t('auth.pageTitle')" content-style="padding: 28px; overflow: visible;">
      <p class="login-view__subtitle">{{ t('auth.pageSubtitle') }}</p>
      <n-form @submit.prevent="submit">
        <n-form-item :label="t('auth.username')" required>
          <n-input
            v-model:value="username"
            :placeholder="t('auth.usernamePlaceholder')"
            :disabled="submitting"
            autocomplete="username"
            @keydown.enter.prevent="submit"
          />
        </n-form-item>
        <n-form-item :label="t('auth.password')" required>
          <n-input
            v-model:value="password"
            type="password"
            show-password-on="click"
            :placeholder="t('auth.passwordPlaceholder')"
            :disabled="submitting"
            autocomplete="current-password"
            @keydown.enter.prevent="submit"
          />
        </n-form-item>
        <n-alert v-if="errorMessage" type="error" :title="t('auth.loginFail')">
          {{ errorMessage }}
        </n-alert>
        <n-button
          attr-type="submit"
          type="primary"
          block
          :loading="submitting"
          :disabled="submitting"
          class="login-view__submit"
          @click="submit"
        >
          {{ submitting ? t('auth.submitting') : t('auth.submit') }}
        </n-button>
      </n-form>
      <p class="login-view__hint">{{ t('auth.defaultHint') }}</p>
    </n-card>
  </main>
</template>

<style scoped>
.login-view {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  min-height: 100dvh;
  padding: var(--spacingVerticalXXL) var(--spacingHorizontalL);
  background: var(--colorBrandBackground2);
  background-image: radial-gradient(ellipse at 50% 30%,
    var(--colorBrandBackground2) 0%,
    var(--colorNeutralBackground2) 60%,
    var(--colorNeutralBackground1) 100%);
  background-repeat: no-repeat;
  background-attachment: fixed;
}

.login-view__brand {
  margin-bottom: var(--spacingVerticalL);
}

.login-view__brand-mark {
  display: inline-grid;
  place-items: center;
  width: 56px;
  height: 56px;
  border-radius: var(--borderRadius3XLarge);
  background: var(--colorBrandBackground);
  color: var(--colorNeutralForegroundOnBrand);
}

.login-view__card {
  width: min(460px, 100%);
  box-shadow: var(--shadow28);
}

.login-view__subtitle {
  margin: 0 0 var(--spacingVerticalL);
  color: var(--colorNeutralForeground2);
  font-size: var(--fontSizeBase300);
  line-height: var(--lineHeightBase300);
}

.login-view__submit {
  margin-top: var(--spacingVerticalM);
}

.login-view__hint {
  margin: var(--spacingVerticalL) 0 0;
  color: var(--colorNeutralForeground3);
  font-size: var(--fontSizeBase200);
  text-align: left;
  line-height: 1.65;
  max-width: 380px;
}
</style>
