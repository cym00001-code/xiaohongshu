import { Pause, Play, RefreshCw } from "lucide-react";
import type { TimeWindow } from "../types";

type TimelineBarProps = {
  window: TimeWindow;
  generatedAt: string;
  isLive: boolean;
  onWindowChange: (value: TimeWindow) => void;
  onLiveToggle: () => void;
  onRefresh: () => void;
};

export function TimelineBar({ window, generatedAt, isLive, onWindowChange, onLiveToggle, onRefresh }: TimelineBarProps) {
  return (
    <div className="timeline-bar" aria-label="趋势时间轴">
      <button className="play-button" onClick={onLiveToggle} aria-label={isLive ? "暂停自动刷新" : "继续自动刷新"}>
        {isLive ? <Pause size={18} /> : <Play size={18} />}
      </button>
      <div className="timeline-window">
        <button className={window === "24h" ? "is-active" : ""} onClick={() => onWindowChange("24h")}>
          24小时
        </button>
        <button className={window === "7d" ? "is-active" : ""} onClick={() => onWindowChange("7d")}>
          7天
        </button>
      </div>
      <div className="time-track">
        <span>{window === "24h" ? "24小时前" : "7天前"}</span>
        <i />
        <strong>现在</strong>
      </div>
      <button className="refresh-button" onClick={onRefresh}>
        <RefreshCw size={16} />
        刷新
      </button>
      <span className="updated-at">更新：{new Date(generatedAt).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" })}</span>
    </div>
  );
}
