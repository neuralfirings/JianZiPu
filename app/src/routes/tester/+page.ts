// The Tester is now the Text view of Build & test; old links keep working.
import { redirect } from '@sveltejs/kit';
import { testerRedirect } from '$lib/buildtest';

export const load = ({ url }: { url: URL }) => {
  redirect(307, testerRedirect(url.searchParams));
};
