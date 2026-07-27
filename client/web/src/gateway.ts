// Binding-B transport: POST /v1/session for a bearer token, then the
// WebSocket gateway (first-message auth). See docs/spec/api/README.md.

import type { Account, ClientMsg, ServerMsg } from './protocol';

export class Gateway {
  private ws: WebSocket | null = null;

  /** Exchange credentials for a bearer token (spec §2). */
  async login(httpBase: string, user: string, pass: string): Promise<{ token: string; account: Account }> {
    const r = await fetch(httpBase + '/v1/session', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user, pass }),
    });
    if (!r.ok) throw new Error('login failed (' + r.status + ')');
    return r.json();
  }

  /** Open the gateway and authenticate the socket with the token. */
  connect(
    wsBase: string,
    token: string,
    onMessage: (m: ServerMsg) => void,
    onClose: () => void,
    onError: () => void,
  ): void {
    const ws = new WebSocket(wsBase + '/v1/gateway');
    this.ws = ws;
    ws.onopen = () => this.send({ type: 'auth', token });
    ws.onmessage = (ev) => onMessage(JSON.parse(ev.data) as ServerMsg);
    ws.onclose = onClose;
    ws.onerror = onError;
  }

  send(msg: ClientMsg): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) this.ws.send(JSON.stringify(msg));
  }

  close(): void { this.ws?.close(); }
}
