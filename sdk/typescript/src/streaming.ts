import { Configuration, getDefaultHeaders } from "./config.js";
import type { StreamChunk } from "./types.js";

export class StreamProcessor {
  private reader: ReadableStreamDefaultReader<Uint8Array> | null = null;
  private buffer: string = "";

  constructor(private response: Response) {
    if (response.body) {
      this.reader = response.body.getReader();
    }
  }

  async *iter(): AsyncGenerator<StreamChunk> {
    if (!this.reader) return;

    while (true) {
      const { done, value } = await this.reader.read();
      if (done) break;

      this.buffer += new TextDecoder().decode(value);
      const lines = this.buffer.split("\n");
      this.buffer = lines.pop() || "";

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || !trimmed.startsWith("data: ")) continue;
        const data = trimmed.slice(6);
        if (data === "[DONE]") return;
        try {
          yield JSON.parse(data) as StreamChunk;
        } catch {
          continue;
        }
      }
    }
  }

  async text(): Promise<string> {
    const chunks: string[] = [];
    for await (const chunk of this.iter()) {
      if (chunk.choices) {
        for (const choice of chunk.choices) {
          const content = choice.delta?.content || choice.text || "";
          if (content) chunks.push(content);
        }
      } else if (chunk.content) {
        chunks.push(chunk.content);
      }
    }
    return chunks.join("");
  }
}

export async function createStream(
  config: Configuration,
  path: string,
  body: unknown,
): Promise<StreamProcessor> {
  const url = new URL(path, config.baseUrl);
  const headers = {
    ...getDefaultHeaders(config),
    Accept: "text/event-stream",
  };

  const response = await fetch(url.toString(), {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });

  return new StreamProcessor(response);
}
