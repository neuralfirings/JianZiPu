<script lang="ts">
  // A Change Request's status as a pill: colour + icon + word (design system).
  import * as I from '$lib/icons';
  import { STATUS_LABEL, STATUS_PILL, type RequestStatus } from '$lib/requests';
  let { status, release = null }: { status: RequestStatus; release?: string | null } = $props();
  const ICON = { sent: I.Send, in_review: I.Info, in_candidate: I.Draft, released: I.Check, declined: I.Problem, withdrawn: I.Withdraw };
  const Ic = $derived(ICON[status]);
</script>

<span class="pill {STATUS_PILL[status]}"><Ic size={14} />{STATUS_LABEL[status]}{#if release && (status === 'in_candidate' || status === 'released')}{` · v${release}`}{/if}</span>
