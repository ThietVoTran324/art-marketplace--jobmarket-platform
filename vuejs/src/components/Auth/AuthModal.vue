<script setup>
import { reactive, ref, watch } from 'vue';
import axios from 'axios';
import ClipLoader from 'vue-spinner/src/ClipLoader.vue';
import { useToast } from 'vue-toastification';
import google_logo from '@/assets/g-logo.png';
import { useAuthModal } from '@/composables/useAuthModal';

const emit = defineEmits(['login', 'signup']);
const toast = useToast();
const { isOpen, mode, closeAuthModal, openAuthModal } = useAuthModal();

const color = ref('#ef4444');
const size = ref('60px');

const formLogin = reactive({ username: '', password: '' });
const formSignUp = reactive({ username: '', password: '', email: '' });
const formPasswordReset = reactive({ username: '', email: '', password: '' });

const imageFile = ref(null);
const imagePreview = ref(null);
const fileError = ref(false);

const showLoginLoader = ref(false);
const showSignUpLoader = ref(false);
const showPasswordResetLoader = ref(false);

const errorMessage = ref('');
const showError = ref(false);
const showSignUpSuccess = ref(false);
const signUpSuccessMessage = ref('');

watch(isOpen, (open) => {
  if (!open) {
    showError.value = false;
    errorMessage.value = '';
    showSignUpSuccess.value = false;
    signUpSuccessMessage.value = '';
    showLoginLoader.value = false;
    showSignUpLoader.value = false;
    showPasswordResetLoader.value = false;
  }
});

function switchMode(next) {
  openAuthModal(next);
  showError.value = false;
  showSignUpSuccess.value = false;
}

function finishSignUpSuccess() {
  showSignUpSuccess.value = false;
  signUpSuccessMessage.value = '';
  formSignUp.username = '';
  formSignUp.password = '';
  formSignUp.email = '';
  imageFile.value = null;
  imagePreview.value = null;
  switchMode('login');
}

function handleImageUpload(event) {
  const file = event.target.files?.[0];
  const allowedTypes = [
    'image/jpeg',
    'image/jpg',
    'image/gif',
    'image/webp',
    'image/png',
    'image/bmp',
  ];
  if (!file) return;
  if (!allowedTypes.includes(file.type)) {
    fileError.value = true;
    return;
  }
  imageFile.value = file;
  const reader = new FileReader();
  reader.onload = (e) => {
    imagePreview.value = e.target.result;
  };
  reader.readAsDataURL(file);
}

async function googleAuth() {
  try {
    const response = await axios.get('/api/users/google/auth/login/');
    window.location.href = response.data.url;
  } catch (error) {
    toast.error('Google auth unavailable', { position: 'top-center' });
  }
}

async function submitLogin() {
  const username = formLogin.username.trim();
  const password = formLogin.password.trim();
  if (!username || !password) {
    toast.warning('Please enter username and password', { position: 'top-center' });
    return;
  }
  showLoginLoader.value = true;
  try {
    const response = await axios.post('/api/users/login', { username, password });
    showLoginLoader.value = false;
    closeAuthModal();
    emit('login', response.data.access_token);
  } catch (error) {
    showLoginLoader.value = false;
    showError.value = true;
    if (error.response?.status === 403) {
      errorMessage.value = 'You need verify your account to login';
    } else {
      errorMessage.value = error.response?.data?.detail || 'Login failed';
    }
  }
}

async function submitSignUp() {
  const username = formSignUp.username.trim();
  const password = formSignUp.password.trim();
  const email = formSignUp.email.trim();
  if (!username || !password) {
    toast.warning('Please enter username and password', { position: 'top-center' });
    return;
  }
  showSignUpLoader.value = true;
  try {
    if (imageFile.value) {
      const formData = new FormData();
      formData.append('file', imageFile.value);
      const payload = { username, password };
      if (email) payload.email = email;
      formData.append('user_model', JSON.stringify(payload));
      await axios.post('/api/users/create-user-entity', formData, {
        withCredentials: true,
        headers: { 'Content-Type': 'multipart/form-data' },
      });
    } else {
      const payload = { username, password };
      if (email) payload.email = email;
      await axios.post('/api/users/register', payload, { withCredentials: true });
    }
    showSignUpLoader.value = false;
    signUpSuccessMessage.value = email
      ? `We sent a verification link to ${email}. You can log in now — email verification is optional.`
      : 'Account created. You can log in now.';
    showSignUpSuccess.value = true;
  } catch (error) {
    showSignUpLoader.value = false;
    showError.value = true;
    const detail = error.response?.data?.detail;
    errorMessage.value =
      typeof detail === 'string' ? detail : 'Sign up failed. Try again later.';
  }
}

async function submitPasswordReset() {
  const username = formPasswordReset.username.trim();
  const email = formPasswordReset.email.trim();
  const password = formPasswordReset.password.trim();
  if (!username || !email || !password) {
    toast.warning('Please fill all password reset fields', { position: 'top-center' });
    return;
  }
  showPasswordResetLoader.value = true;
  try {
    await axios.post('/api/users/password-reset-request', {
      username,
      email,
      password,
    });
    showPasswordResetLoader.value = false;
    toast.success('Check your email to confirm password reset', { position: 'top-center' });
    switchMode('login');
  } catch (error) {
    showPasswordResetLoader.value = false;
    showError.value = true;
    errorMessage.value = error.response?.data?.detail || 'Password reset failed';
  }
}
</script>

<template>
  <div
    v-if="isOpen"
    class="fixed inset-0 flex items-center justify-center bg-black bg-opacity-50 z-[80]"
    @click.self="closeAuthModal"
  >
    <div class="relative p-4 w-full max-w-md max-h-[90vh] overflow-y-auto">
      <div class="relative bg-white rounded-3xl">
        <div class="flex items-center justify-between p-4 md:p-5 border-b">
          <h3 class="text-lg font-semibold text-gray-900">
            <span v-if="mode === 'login'">Log In</span>
            <span v-else-if="mode === 'signup'">Sign Up</span>
            <span v-else>Password Reset</span>
          </h3>
          <button
            type="button"
            class="text-gray-400 hover:bg-gray-200 hover:text-gray-900 rounded-lg text-sm w-8 h-8 inline-flex justify-center items-center"
            @click="closeAuthModal"
          >
            ✕
          </button>
        </div>

        <div v-if="showError" class="p-5 text-center">
          <p class="mb-4 text-gray-700">{{ errorMessage }}</p>
          <button
            type="button"
            class="text-white bg-red-600 hover:bg-red-700 font-medium rounded-3xl text-sm px-5 py-2.5"
            @click="showError = false"
          >
            OK
          </button>
        </div>

        <div v-else-if="showSignUpSuccess" class="p-5 text-center">
          <p class="mb-4 text-gray-700">{{ signUpSuccessMessage }}</p>
          <button
            type="button"
            class="text-white bg-red-500 hover:bg-red-600 font-medium rounded-3xl text-sm px-5 py-2.5"
            @click="finishSignUpSuccess"
          >
            OK — go to Log In
          </button>
        </div>

        <div v-else-if="mode === 'login'" class="p-5">
          <ClipLoader
            v-if="showLoginLoader"
            :color="color"
            :size="size"
            class="flex items-center justify-center h-48"
          />
          <form v-else class="space-y-4" @submit.prevent="submitLogin">
            <div>
              <label class="block mb-2 text-sm font-medium text-gray-900">Username</label>
              <input
                v-model="formLogin.username"
                type="text"
                autocomplete="username"
                class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-3xl block w-full py-3 px-5"
              />
            </div>
            <div>
              <label class="block mb-2 text-sm font-medium text-gray-900">Password</label>
              <input
                v-model="formLogin.password"
                type="password"
                autocomplete="current-password"
                class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-3xl block w-full py-3 px-5"
              />
            </div>
            <button
              type="submit"
              class="w-full text-white bg-red-500 hover:bg-red-600 font-semibold rounded-3xl text-sm px-5 py-3"
            >
              Log In
            </button>
            <button
              type="button"
              class="w-full flex items-center justify-center gap-2 border rounded-3xl py-3 text-sm hover:bg-gray-50"
              @click="googleAuth"
            >
              <img :src="google_logo" alt="" class="w-5 h-5 rounded-full" />
              Continue with Google
            </button>
            <p class="text-sm text-gray-600">
              No account?
              <button type="button" class="text-red-500 hover:underline" @click="switchMode('signup')">
                Sign Up
              </button>
            </p>
            <button type="button" class="text-sm text-red-500 hover:underline" @click="switchMode('reset')">
              Lost Password?
            </button>
          </form>
        </div>

        <div v-else-if="mode === 'signup'" class="p-5">
          <ClipLoader
            v-if="showSignUpLoader"
            :color="color"
            :size="size"
            class="flex items-center justify-center h-48"
          />
          <form v-else class="space-y-4" @submit.prevent="submitSignUp">
            <div>
              <label class="block mb-2 text-sm font-medium text-gray-900">Username</label>
              <input
                v-model="formSignUp.username"
                type="text"
                autocomplete="username"
                class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-3xl block w-full py-3 px-5"
              />
            </div>
            <div>
              <label class="block mb-2 text-sm font-medium text-gray-900">Password</label>
              <input
                v-model="formSignUp.password"
                type="password"
                autocomplete="new-password"
                class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-3xl block w-full py-3 px-5"
              />
            </div>
            <div>
              <label class="block mb-2 text-sm font-medium text-gray-900">
                Profile image <span class="text-gray-500 font-normal">(optional)</span>
              </label>
              <input
                type="file"
                accept=".jpg,.jpeg,.gif,.webp,.png,.bmp"
                class="block w-full text-sm"
                @change="handleImageUpload"
              />
              <p class="mt-1 text-xs text-gray-500">You can add or change this later on your profile.</p>
              <img
                v-if="imagePreview"
                :src="imagePreview"
                alt=""
                class="mt-2 w-20 h-20 object-cover rounded-full"
              />
            </div>
            <div>
              <label class="block mb-2 text-sm font-medium text-gray-900">Email (optional)</label>
              <input
                v-model="formSignUp.email"
                type="text"
                autocomplete="email"
                class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-3xl block w-full py-3 px-5"
              />
            </div>
            <button
              type="submit"
              class="w-full text-white bg-red-500 hover:bg-red-600 font-semibold rounded-3xl text-sm px-5 py-3"
            >
              Sign Up
            </button>
            <button
              type="button"
              class="w-full flex items-center justify-center gap-2 border rounded-3xl py-3 text-sm hover:bg-gray-50"
              @click="googleAuth"
            >
              <img :src="google_logo" alt="" class="w-5 h-5 rounded-full" />
              Continue with Google
            </button>
            <p class="text-sm text-gray-600">
              Already have an account?
              <button type="button" class="text-red-500 hover:underline" @click="switchMode('login')">
                Login
              </button>
            </p>
          </form>
        </div>

        <div v-else class="p-5">
          <ClipLoader
            v-if="showPasswordResetLoader"
            :color="color"
            :size="size"
            class="flex items-center justify-center h-48"
          />
          <form v-else class="space-y-4" @submit.prevent="submitPasswordReset">
            <div>
              <label class="block mb-2 text-sm font-medium text-gray-900">Username</label>
              <input
                v-model="formPasswordReset.username"
                type="text"
                class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-3xl block w-full py-3 px-5"
              />
            </div>
            <div>
              <label class="block mb-2 text-sm font-medium text-gray-900">Email</label>
              <input
                v-model="formPasswordReset.email"
                type="text"
                class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-3xl block w-full py-3 px-5"
              />
            </div>
            <div>
              <label class="block mb-2 text-sm font-medium text-gray-900">New password</label>
              <input
                v-model="formPasswordReset.password"
                type="password"
                autocomplete="new-password"
                class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-3xl block w-full py-3 px-5"
              />
            </div>
            <button
              type="submit"
              class="w-full text-white bg-red-500 hover:bg-red-600 font-semibold rounded-3xl text-sm px-5 py-3"
            >
              Reset Password
            </button>
            <button type="button" class="text-sm text-red-500 hover:underline" @click="switchMode('login')">
              Back to Login
            </button>
          </form>
        </div>
      </div>
    </div>

    <div
      v-if="fileError"
      class="fixed inset-0 flex items-center justify-center bg-black/40 z-[90]"
      @click.self="fileError = false"
    >
      <div class="bg-white rounded-3xl p-6 max-w-sm text-center">
        <p class="mb-4">Invalid file type. Allowed: .jpg, .jpeg, .gif, .webp, .png, .bmp</p>
        <button
          type="button"
          class="text-white bg-red-600 rounded-3xl px-5 py-2"
          @click="fileError = false"
        >
          OK
        </button>
      </div>
    </div>
  </div>
</template>
