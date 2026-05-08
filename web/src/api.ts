import type { TimeWindow, TrendSnapshot } from "./types";

export async function fetchTrendSnapshot(window: TimeWindow, signal?: AbortSignal): Promise<TrendSnapshot> {
  const response = await fetch(`/api/trends?window=${window}`, { signal });
  if (!response.ok) {
    throw new Error(`趋势数据读取失败：${response.status}`);
  }
  return response.json();
}
