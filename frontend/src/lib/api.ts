import type { BoardData, BoardSummary, BoardWithMeta, Priority } from "@/lib/kanban";

export type SessionInfo = {
  authenticated: boolean;
  username?: string | null;
  displayName?: string | null;
};
export type ChatMessage = { role: "user" | "assistant"; content: string };
export type ChatResponse = {
  message: string;
  boardUpdated: boolean;
  board: BoardData | null;
  boardId: number;
};

export type BoardAction =
  | { action: "rename_column"; payload: { column_id: string; title: string } }
  | {
      action: "add_card";
      payload: {
        column_id: string;
        title: string;
        details: string;
        card_id?: string;
        priority?: Priority;
        dueDate?: string | null;
      };
    }
  | {
      action: "update_card";
      payload: {
        card_id: string;
        title?: string;
        details?: string;
        priority?: Priority;
        dueDate?: string | null;
      };
    }
  | { action: "delete_card"; payload: { card_id: string } }
  | {
      action: "move_card";
      payload: { card_id: string; target_column_id: string; target_index?: number };
    }
  | { action: "add_column"; payload: { title: string; column_id?: string } }
  | { action: "delete_column"; payload: { column_id: string } }
  | { action: "move_column"; payload: { column_id: string; target_index: number } };

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
  if (response.status === 204) {
    return undefined as T;
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
  register: (username: string, password: string, displayName?: string) =>
    request<SessionInfo>("/api/register", {
      method: "POST",
      body: JSON.stringify({ username, password, display_name: displayName }),
    }),
  logout: () => request<SessionInfo>("/api/logout", { method: "POST" }),
  updateProfile: (payload: { display_name?: string; password?: string }) =>
    request<{ id: number; username: string; displayName: string | null }>("/api/me", {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),

  // Multi-board
  listBoards: () => request<{ boards: BoardSummary[] }>("/api/boards"),
  createBoard: (name: string) =>
    request<BoardSummary>("/api/boards", {
      method: "POST",
      body: JSON.stringify({ name }),
    }),
  renameBoard: (id: number, name: string) =>
    request<BoardSummary>(`/api/boards/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ name }),
    }),
  deleteBoard: (id: number) =>
    request<void>(`/api/boards/${id}`, { method: "DELETE" }),
  getBoardState: (id: number) => request<BoardWithMeta>(`/api/boards/${id}`),
  postBoardAction: (id: number, action: BoardAction) =>
    request<BoardData>(`/api/boards/${id}/actions`, {
      method: "POST",
      body: JSON.stringify(action),
    }),

  // Legacy single-board (still used by tests + back-compat).
  getBoard: () => request<BoardData>("/api/board"),

  getChatHistory: (boardId?: number) =>
    request<{ messages: ChatMessage[] }>(
      boardId ? `/api/chat/history?board_id=${boardId}` : "/api/chat/history"
    ),
  resetChat: (boardId?: number) =>
    request<{ messages: ChatMessage[] }>(
      boardId ? `/api/chat/reset?board_id=${boardId}` : "/api/chat/reset",
      { method: "POST" }
    ),
  sendChat: (message: string, boardId?: number) =>
    request<ChatResponse>("/api/chat", {
      method: "POST",
      body: JSON.stringify({ message, board_id: boardId ?? null }),
    }),
};

export { ApiError };
