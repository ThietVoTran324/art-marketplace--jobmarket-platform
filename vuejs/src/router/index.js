import { createRouter, createWebHistory } from "vue-router";
import axios from "axios";
import { authUserStore } from "@/stores/authUserStore";
import { useAuthModal } from "@/composables/useAuthModal";
import HomeView from '@/views/HomeView.vue';
import CreatePinView from '@/views/CreatePinView.vue';
import PinView from '@/views/PinView.vue';
import CheckoutView from '@/views/CheckoutView.vue';
import UserView from '@/views/UserView.vue';  
import NotFoundView from '@/views/NotFoundView.vue';
import MessagesView from '@/views/MessagesView.vue';
import RecommendationsView from '@/views/RecommendationsView.vue';
import SettingsView from '@/views/SettingsView.vue';
import ExploreView from '@/views/ExploreView.vue';
import CompanyView from '@/views/CompanyView.vue';
import ApplicationCvView from '@/views/ApplicationCvView.vue';
import AdminLayout from '@/views/admin/AdminLayout.vue';
import AdminOverviewView from '@/views/admin/AdminOverviewView.vue';
import AdminRolesView from '@/views/admin/AdminRolesView.vue';
import AdminAuditView from '@/views/admin/AdminAuditView.vue';
import AdminContentView from '@/views/admin/AdminContentView.vue';
import AdminKycView from '@/views/admin/AdminKycView.vue';
import AdminCredentialsView from '@/views/admin/AdminCredentialsView.vue';
import AdminJobReportsView from '@/views/admin/AdminJobReportsView.vue';
import AdminCopyrightView from '@/views/admin/AdminCopyrightView.vue';
import AdminPayoutsView from '@/views/admin/AdminPayoutsView.vue';
import AdminWorkExperiencesView from '@/views/admin/AdminWorkExperiencesView.vue';

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', name: 'home', component: HomeView },
    { path: '/create-pin', name: 'create-pin', component: CreatePinView },
    { path: '/pin/:id', name: 'pin', component: PinView },
    { path: '/checkout/pin/:pinId', name: 'checkout-pin', component: CheckoutView },
    { path: '/checkout/order/:orderId', name: 'checkout-order', component: CheckoutView },
    { path: '/user/:username', name: 'user', component: UserView },
    { path: '/messages', name: 'messages', component: MessagesView },
    { path: '/settings', name: 'settings', component: SettingsView },
    { path: '/explore', name: 'explore', component: ExploreView },
    { path: '/companies/:id', name: 'company', component: CompanyView },
    {
      path: '/jobs/:id',
      name: 'job-detail',
      redirect: (to) => ({ path: '/explore', query: { job: String(to.params.id) } }),
    },
    { path: '/applications/:id/cv', name: 'application-cv', component: ApplicationCvView },
    { path: '/recommendations/:id', name: 'recommendations', component: RecommendationsView },
    {
      path: '/admin',
      component: AdminLayout,
      meta: { requiresAdmin: true },
      children: [
        { path: '', name: 'admin-overview', component: AdminOverviewView },
        { path: 'roles', name: 'admin-roles', component: AdminRolesView },
        { path: 'audit', name: 'admin-audit', component: AdminAuditView },
        { path: 'content', name: 'admin-content', component: AdminContentView },
        { path: 'kyc', name: 'admin-kyc', component: AdminKycView },
        { path: 'credentials', name: 'admin-credentials', component: AdminCredentialsView },
        { path: 'job-reports', name: 'admin-job-reports', component: AdminJobReportsView },
        { path: 'copyright', name: 'admin-copyright', component: AdminCopyrightView },
        { path: 'marketplace/payouts', name: 'admin-marketplace-payouts', component: AdminPayoutsView },
        { path: 'work-experiences', name: 'admin-work-experiences', component: AdminWorkExperiencesView },
      ],
    },
    { path: '/:catchAll(.*)', name: 'not-found', component: NotFoundView },
  ],
});

async function ensureRolesLoaded() {
  const userStore = authUserStore();
  if (userStore.roles.length) return userStore;
  try {
    const { data } = await axios.get('/api/users/me/roles', { withCredentials: true });
    userStore.setRoles(data.roles || []);
  } catch {
    userStore.setRoles([]);
  }
  return userStore;
}

router.beforeEach(async (to) => {
  const userStore = authUserStore();
  const allowedGuest =
    to.path === '/' || to.path === '/portfolio' || to.path.startsWith('/portfolio');

  if (userStore.isGuest && !allowedGuest) {
    const { openAuthModal } = useAuthModal();
    openAuthModal('login');
    return { path: '/' };
  }

  if (!to.matched.some((record) => record.meta.requiresAdmin)) {
    return true;
  }
  const loaded = await ensureRolesLoaded();
  if (!loaded.hasRole('admin')) {
    return { path: '/' };
  }
  return true;
});

export default router;
