// Which email a change to change_requests sends (pure, so notify_test.ts can check it).
// The Database Webhook posts {type, table, record, old_record} on insert and update.

export type Status = 'sent' | 'in_review' | 'in_candidate' | 'released' | 'declined' | 'withdrawn';
export type RequestRow = {
  id: string; author: string; title: string; notes: string; credit: string; item_ids: string[];
  status: Status; decisions: Record<string, 'keep' | 'skip'>; reply: string; release: string | null; created_at: string;
};
export type Payload = { type: 'INSERT' | 'UPDATE' | 'DELETE'; table: string; record: RequestRow | null; old_record: RequestRow | null };
export type Email = { template: 'new_request' | 'withdrawn' | 'status_changed'; to: 'admins' | 'author' };

export function decide(p: Payload): Email | null {
  if (p.table !== 'change_requests' || !p.record) return null;
  if (p.type === 'INSERT') return { template: 'new_request', to: 'admins' };
  if (p.type !== 'UPDATE' || !p.old_record || p.old_record.status === p.record.status) return null;
  if (p.record.status === 'withdrawn') return { template: 'withdrawn', to: 'admins' };
  if (p.record.status === 'sent') return null;
  return { template: 'status_changed', to: 'author' };
}
