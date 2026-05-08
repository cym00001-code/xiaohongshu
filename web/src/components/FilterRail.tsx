import { Check, CircleDot, Clock3, Database, RefreshCw, Search, Sparkles } from "lucide-react";
import type { GalaxyInfo, ProviderStatus, TimeWindow, TrendNode } from "../types";
import { platformLabel } from "../format";

type FilterRailProps = {
  nodes: TrendNode[];
  galaxies: GalaxyInfo[];
  providers: ProviderStatus[];
  selectedGalaxy: string;
  selectedPlatforms: string[];
  search: string;
  window: TimeWindow;
  onGalaxyChange: (value: string) => void;
  onPlatformToggle: (value: string) => void;
  onSearchChange: (value: string) => void;
  onWindowChange: (value: TimeWindow) => void;
  onReset: () => void;
};

export function FilterRail({
  nodes,
  galaxies,
  providers,
  selectedGalaxy,
  selectedPlatforms,
  search,
  window,
  onGalaxyChange,
  onPlatformToggle,
  onSearchChange,
  onWindowChange,
  onReset
}: FilterRailProps) {
  const platformKeys = Array.from(new Set(nodes.flatMap((node) => Object.keys(node.platform_distribution))));

  return (
    <aside className="filter-rail" aria-label="趋势筛选">
      <div className="brand">
        <div className="brand-mark">
          <Sparkles size={18} />
        </div>
        <div>
          <strong>AI 趋势星系</strong>
          <span>多平台热度雷达</span>
        </div>
      </div>

      <section>
        <div className="section-title">
          <CircleDot size={15} />
          <span>星系视图</span>
        </div>
        <div className="choice-list">
          <button className={selectedGalaxy === "all" ? "is-active" : ""} onClick={() => onGalaxyChange("all")}>
            <span>全部星系</span>
            <small>{nodes.length}</small>
          </button>
          {galaxies.map((galaxy) => (
            <button
              key={galaxy.id}
              className={selectedGalaxy === galaxy.id ? "is-active" : ""}
              onClick={() => onGalaxyChange(galaxy.id)}
            >
              <span>{galaxy.label}</span>
              <small>{nodes.filter((node) => node.galaxy === galaxy.id).length}</small>
            </button>
          ))}
        </div>
      </section>

      <section>
        <div className="section-title">
          <Database size={15} />
          <span>平台来源</span>
        </div>
        <div className="platform-list">
          {platformKeys.map((platform) => (
            <button
              key={platform}
              className={selectedPlatforms.includes(platform) ? "is-active" : ""}
              onClick={() => onPlatformToggle(platform)}
            >
              <span>{platformLabel(platform)}</span>
              {selectedPlatforms.includes(platform) && <Check size={15} />}
            </button>
          ))}
        </div>
        <div className="provider-health">
          {providers.slice(0, 4).map((provider) => (
            <span key={provider.platform} className={provider.enabled ? "is-on" : ""}>
              {provider.label}
            </span>
          ))}
        </div>
      </section>

      <section>
        <div className="section-title">
          <Clock3 size={15} />
          <span>时间窗口</span>
        </div>
        <div className="segmented">
          <button className={window === "24h" ? "is-active" : ""} onClick={() => onWindowChange("24h")}>
            24小时
          </button>
          <button className={window === "7d" ? "is-active" : ""} onClick={() => onWindowChange("7d")}>
            7天
          </button>
        </div>
      </section>

      <section>
        <div className="section-title">
          <Search size={15} />
          <span>模型检索</span>
        </div>
        <div className="search-box">
          <Search size={15} />
          <input value={search} onChange={(event) => onSearchChange(event.target.value)} placeholder="搜索模型或方向" />
        </div>
      </section>

      <button className="reset-button" onClick={onReset}>
        <RefreshCw size={15} />
        重置视图
      </button>
    </aside>
  );
}
