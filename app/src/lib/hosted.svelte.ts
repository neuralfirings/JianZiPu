// Hosted (pilot) mode: who is signed in, and the Supabase client that keeps their draft.
// The server says which mode it runs in (GET /api/config). Local mode (your own machine) needs
// none of this, except that a local Builder with Supabase settings can sign in as the admin to
// list testers' drafts on the Review screen.
import type { SupabaseClient } from '@supabase/supabase-js';
import { api, session, type ServerConfig } from './api';

export type Person = { id: string; email: string; name: string };

class Hosted {
  config = $state<ServerConfig | null>(null);
  ready = $state(false);
  user = $state<Person | null>(null);
  /** The server answered 401 mid-session: the sign-in is gone. */
  signedOut = $state(false);
  /** A magic link that came back expired or already used. */
  linkExpired = $state(false);
  isAdmin = $state(false);
  client: SupabaseClient | null = null;
  private token: string | null = null;
  private listeners: (() => void)[] = [];

  get isHosted() {
    return this.config?.mode === 'hosted';
  }
  get canSignIn() {
    return !!(this.config?.supabase_url && this.config?.supabase_anon_key);
  }
  get firstName() {
    return (this.user?.name || this.user?.email || '').split(/[\s@]/)[0];
  }

  /** Call `fn` whenever someone signs in (the app then loads their draft). */
  onSignIn(fn: () => void) {
    this.listeners.push(fn);
  }

  async init() {
    try {
      this.config = await api.config();
    } catch {
      this.config = { mode: 'local', commit: null, supabase_url: null, supabase_anon_key: null };
    }
    session.token = () => this.token;
    session.onSignedOut = () => { if (this.isHosted && this.user) this.signedOut = true; };
    const hash = typeof location !== 'undefined' ? location.hash : '';
    if (/error_code=otp_expired|error=access_denied/.test(hash)) {
      this.linkExpired = true;
      history.replaceState(null, '', location.pathname + location.search);
    }
    if (this.canSignIn) {
      const { createClient } = await import('@supabase/supabase-js');
      this.client = createClient(this.config!.supabase_url!, this.config!.supabase_anon_key!, {
        auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true, flowType: 'implicit' }
      });
      const { data } = await this.client.auth.getSession();
      await this.setSession(data.session);
      this.client.auth.onAuthStateChange((event, s) => {
        const was = this.user?.id;
        void this.setSession(s).then(() => {
          if (event === 'SIGNED_IN' && this.user && this.user.id !== was) for (const fn of this.listeners) fn();
        });
      });
    }
    this.ready = true;
  }

  private async setSession(s: { access_token: string; user: { id: string; email?: string; user_metadata?: Record<string, unknown> } } | null) {
    this.token = s?.access_token ?? null;
    if (!s) { this.user = null; this.isAdmin = false; return; }
    const meta = s.user.user_metadata ?? {};
    this.user = { id: s.user.id, email: s.user.email ?? '', name: String(meta.full_name ?? meta.name ?? '') };
    this.signedOut = false;
    this.linkExpired = false;
    if (this.client) {
      const { data } = await this.client.from('profiles').select('name, role').eq('id', s.user.id).maybeSingle();
      if (data?.name) this.user = { ...this.user, name: data.name };
      this.isAdmin = data?.role === 'admin';
    }
  }

  /** Email a sign-in link. Only invited people (already in Supabase) get one. */
  async sendLink(email: string): Promise<'sent' | 'not-invited' | string> {
    if (!this.client) return 'Sign-in is not set up on this server.';
    const { error } = await this.client.auth.signInWithOtp({
      email: email.trim(),
      options: { shouldCreateUser: false, emailRedirectTo: location.origin + location.pathname }
    });
    if (!error) return 'sent';
    // shouldCreateUser: false → Supabase refuses unknown addresses with otp_disabled ("Signups not allowed for otp")
    if ((error as { code?: string }).code === 'otp_disabled' || /signups? not allowed/i.test(error.message)) return 'not-invited';
    if (/fetch|network/i.test(error.message)) return "We can't reach the sign-in service right now. Try again in a minute.";
    return error.message;
  }

  async signOut() {
    await this.client?.auth.signOut();
    this.token = null;
    this.user = null;
  }
}

export const hosted = new Hosted();
