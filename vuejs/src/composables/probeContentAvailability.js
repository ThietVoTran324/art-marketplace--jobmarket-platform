import axios from 'axios';

/**
 * Probe whether a frontend path still points at reachable content.
 * Returns false for 404/403 (hidden, closed, deleted). Unknown paths → true.
 */
export async function probeContentPath(pathWithQuery) {
  if (!pathWithQuery || typeof pathWithQuery !== 'string') return true;

  let url;
  try {
    url = new URL(pathWithQuery, window.location.origin);
  } catch {
    return true;
  }

  const path = url.pathname;
  const jobQ = url.searchParams.get('job');

  try {
    if (path === '/explore' && jobQ) {
      await axios.get(`/api/job-market/jobs/${jobQ}`);
      return true;
    }

    let m = path.match(/^\/jobs\/(\d+)/);
    if (m) {
      await axios.get(`/api/job-market/jobs/${m[1]}`);
      return true;
    }

    m = path.match(/^\/companies\/(\d+)/);
    if (m) {
      await axios.get(`/api/job-market/companies/${m[1]}`);
      return true;
    }

    m = path.match(/^\/pin\/(\d+)/);
    if (m) {
      await axios.get(`/api/pins/${m[1]}`);
      return true;
    }

    m = path.match(/^\/user\/([^/]+)/);
    if (m) {
      await axios.get(`/api/users/user_username/${decodeURIComponent(m[1])}`);
      return true;
    }

    m = path.match(/^\/applications\/(\d+)/);
    if (m) {
      await axios.get(`/api/job-market/applications/${m[1]}/cv-view`);
      return true;
    }

    m = path.match(/^\/recommendations\/(\d+)/);
    if (m) {
      const { data } = await axios.get(`/api/recommendations/${m[1]}`, {
        params: { offset: 0, limit: 1 },
      });
      if (!data || (Array.isArray(data) && data.length === 0)) return false;
      return true;
    }

    return true;
  } catch (e) {
    const status = e?.response?.status;
    if (status === 404 || status === 403 || status === 410) return false;
    return true;
  }
}
