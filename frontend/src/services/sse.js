export async function consumeSSE(response, onEvent) {
  if (!response.ok || !response.headers.get('content-type')?.includes('text/event-stream')) {
    throw new Error('Invalid streaming response');
  }
  const reader = response.body.getReader(), decoder = new TextDecoder();
  let buffer = '', result;
  try {
    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value, { stream: !done });
      buffer = buffer.replace(/\r\n/g, '\n');
      if (buffer.length > 200000) throw new Error('Stream frame too large');
      let boundary;
      while ((boundary = buffer.indexOf('\n\n')) >= 0) {
        const frame = buffer.slice(0, boundary); buffer = buffer.slice(boundary + 2);
        const lines = frame.split('\n');
        const event = lines.find(line => line.startsWith('event:'))?.slice(6).trim();
        const data = lines.filter(line => line.startsWith('data:')).map(line => line.slice(5).trimStart()).join('\n');
        if (!event || !data) continue;
        const payload = JSON.parse(data);
        if (event === 'error') throw new Error(payload.message || 'Stream failed');
        onEvent?.(event, payload);
        if (event === 'done') { result = payload; return result; }
      }
      if (done) throw new Error('Stream closed without a final answer');
    }
  } finally {
    await reader.cancel().catch(() => {});
    reader.releaseLock();
  }
}
