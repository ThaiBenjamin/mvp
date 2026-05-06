import type { BoardData } from "@/lib/kanban";

export type SessionInfo = { authenticated: boolean; username?: string | null };
export type ChatMessage = { role: "user" | "assistant"; content: string };
export type ChatResponse = {
  message: string;
  boardUpdated: boolean;
  board: BoardData | null;
};

export type BoardAction =
  | { action: "rename_column"; payload: { column_id: string; title: string } }
  | {
      action: "add_card";
      payload: { column_id: string; title: string; details: string; card_id?: string };
    }
  | { action: "delete_card"; payload: { card_id: string } }
  | {
      action: "move_card";
      payload: { card_id: string; target_column_id: string; target_index?: number };
    };

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

const request = async <T>(input: string, init?: RequestInit): Promise<T> => {
  const response = await fetch(input, {
    ...init,
    headers: init?.body
      ? { "Content-Type": "application/json", ...(init?.headers ?? {}) }
      : init?.headers,
  });
  if (!response.ok) {
    throw new ApiError(response.status, `${init?.method ?? "GET"} ${input} failed`);
  }
  return (await response.json()) as T;
};

export const api = {
  getSession: () => request<SessionInfo>("/api/session"),
  login: (username: string, password: string) =>
    request<SessionInfo>("/api/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  logout: () => request<SessionInfo>("/api/logout", { method: "POST" }),

  getBoard: () => request<BoardData>("/api/board"),
  postBoardAction: (action: BoardAction) =>
    request<BoardData>("/api/board/actions", {
      method: "POST",
      body: JSON.stringify(action),
    }),

  getChatHistory: () => request<{ messages: ChatMessage[] }>("/api/chat/history"),
  resetChat: () =>
    request<{ messages: ChatMessage[] }>("/api/chat/reset", { method: "POST" }),
  sendChat: (message: string) =>
    request<ChatResponse>("/api/chat", {
      method: "POST",
      body: JSON.stringify({ message }),
    }),
};

export { ApiError };
