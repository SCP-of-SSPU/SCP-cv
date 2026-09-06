<script setup lang="ts">
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';
import { NAlert, NButton, NCard, NFormItem, NInput } from 'naive-ui';

import { useToast } from '@/composables/useToast';
import { useAuthStore } from '@/stores/auth';

const { t } = useI18n();
const router = useRouter();
const auth = useAuthStore();
const toast = useToast();

const currentPassword = ref('');
const newPassword = ref('');
const confirmPassword = ref('');
const saving = ref(false);
const loggingOut = ref(false);
const errorMessage = ref('');
const canSave = computed(() => Boolean(currentPassword.value && newPassword.value && confirmPassword.value) && !saving.value);

async function save(): Promise<void> {
  errorMessage.value = '';
  if (newPassword.value !== confirmPassword.value) {
    errorMessage.value = t('settings.passwordMismatch');
    return;
  }
  saving.value = true;
  try {
    await auth.changePassword(currentPassword.value, newPassword.value);
    currentPassword.value = '';
    newPassword.value = '';
    confirmPassword.value = '';
    toast.success(t('settings.passwordChanged'));
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : t('settings.passwordChangeFail');
  } finally {
    saving.value = false;
  }
}

async function logout(): Promise<void> {
  loggingOut.value = true;
  try {
    await auth.logout();
    toast.success(t('auth.logoutOk'));
    await router.replace('/login');
  } catch (error) {
    toast.error(t('auth.logoutFail'), error instanceof Error ? error.message : t('common.retry'));
  } finally {
    loggingOut.value = false;
  }
}
</script>

<template>
  <section class="settings-view__grid">
    <n-card :title="t('settings.accountTitle')">
      <p class="settings-view__hint">{{ t('settings.accountSignedIn', { username: auth.username }) }}</p>
      <n-form-item :label="t('settings.currentPassword')" required>
        <n-input v-model:value="currentPassword" type="password" show-password-on="click" autocomplete="current-password" />
      </n-form-item>
      <n-form-item :label="t('settings.newPassword')" required :feedback="t('settings.passwordHint')">
        <n-input v-model:value="newPassword" type="password" show-password-on="click" autocomplete="new-password" />
      </n-form-item>
      <n-form-item :label="t('settings.confirmPassword')" required>
        <n-input v-model:value="confirmPassword" type="password" show-password-on="click" autocomplete="new-password" />
      </n-form-item>
      <n-alert v-if="errorMessage" type="error" :title="t('settings.passwordChangeFail')">{{ errorMessage }}</n-alert>
      <n-button type="primary" :disabled="!canSave" :loading="saving" @click="save">
        {{ t('settings.changePassword') }}
      </n-button>
    </n-card>

    <n-card :title="t('settings.sessionTitle')">
      <p class="settings-view__hint">{{ t('settings.sessionHint') }}</p>
      <n-button secondary :loading="loggingOut" @click="logout">
        {{ t('auth.logoutAction') }}
      </n-button>
    </n-card>
  </section>
</template>
