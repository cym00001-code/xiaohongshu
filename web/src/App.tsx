import { lazy, Suspense, useCallback, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { Activity, AlertTriangle, Gauge, Layers3, Loader2, RadioTower } from "lucide-react";
import { fetchTrendSnapshot } from "./api";
import { fallbackSnapshot } from "./sampleData";
import { DetailPanel } from "./components/DetailPanel";
import { FilterRail } from "./components/FilterRail";
import { TimelineBar } from "./components/TimelineBar";
import { compactNumber } from "./format";
import type { TimeWindow, TrendNode, TrendSnapshot } from "./types";
import "./styles.css";

const GalaxyCanvas = lazy(() => import("./components/GalaxyCanvas").then((module) => ({ default: module.GalaxyCanvas })));

export default function App() {
  const [snapshot, setSnapshot] = useState<TrendSnapshot>(fallbackSnapshot);
  const [timeWindow, setTimeWindow] = useState<TimeWindow>("24h");
  const [selectedEntity, setSelectedEntity] = useState("chatgpt");
  const [selectedGalaxy, setSelectedGalaxy] = useState("all");
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>([]);
  const [search, setSearch] = useState("");
  const [isLive, setIsLive] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadSnapshot = useCallback(async (targetWindow: TimeWindow) => {
    const controller = new AbortController();
    setIsLoading(true);
    try {
      const next = await fetchTrendSnapshot(targetWindow, controller.signal);
      setSnapshot(next);
      setError(null);
      setSelectedEntity((current) => next.nodes.find((node) => node.entity === current)?.entity ?? next.nodes[0]?.entity ?? "");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "趋势数据读取失败");
    } finally {
      setIsLoading(false);
    }
    return () => controller.abort();
  }, []);

  useEffect(() => {
    void loadSnapshot(timeWindow);
  }, [loadSnapshot, timeWindow]);

  useEffect(() => {
    if (!isLive) return;
    const refreshMs = Math.max(snapshot.refresh_minutes, 1) * 60 * 1000;
    const interval = globalThis.setInterval(() => {
      void loadSnapshot(timeWindow);
    }, refreshMs);
    return () => globalThis.clearInterval(interval);
  }, [isLive, loadSnapshot, snapshot.refresh_minutes, timeWindow]);

  const platformKeys = useMemo(
    () => Array.from(new Set(snapshot.nodes.flatMap((node) => Object.keys(node.platform_distribution)))),
    [snapshot.nodes]
  );

  useEffect(() => {
    if (selectedPlatforms.length === 0 && platformKeys.length > 0) {
      setSelectedPlatforms(platformKeys);
    }
  }, [platformKeys, selectedPlatforms.length]);

  const filteredNodes = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase();
    return snapshot.nodes.filter((node) => {
      const galaxyMatches = selectedGalaxy === "all" || node.galaxy === selectedGalaxy;
      const platformMatches =
        selectedPlatforms.length === 0 ||
        Object.keys(node.platform_distribution).some((platform) => selectedPlatforms.includes(platform));
      const searchMatches =
        !normalizedSearch ||
        node.label.toLowerCase().includes(normalizedSearch) ||
        node.galaxy_label.toLowerCase().includes(normalizedSearch);
      return galaxyMatches && platformMatches && searchMatches;
    });
  }, [snapshot.nodes, search, selectedGalaxy, selectedPlatforms]);

  const selectedNode = useMemo<TrendNode | null>(() => {
    return filteredNodes.find((node) => node.entity === selectedEntity) ?? filteredNodes[0] ?? null;
  }, [filteredNodes, selectedEntity]);

  const totalHeat = useMemo(() => filteredNodes.reduce((sum, node) => sum + node.heat, 0), [filteredNodes]);
  const liveProviders = snapshot.providers.filter((provider) => provider.enabled).length;

  function handlePlatformToggle(platform: string) {
    setSelectedPlatforms((current) =>
      current.includes(platform) ? current.filter((item) => item !== platform) : [...current, platform]
    );
  }

  function handleReset() {
    setSelectedGalaxy("all");
    setSelectedPlatforms(platformKeys);
    setSearch("");
    setSelectedEntity(snapshot.nodes[0]?.entity ?? "");
  }

  return (
    <main className="app-shell">
      <FilterRail
        nodes={snapshot.nodes}
        galaxies={snapshot.galaxies}
        providers={snapshot.providers}
        selectedGalaxy={selectedGalaxy}
        selectedPlatforms={selectedPlatforms}
        search={search}
        window={timeWindow}
        onGalaxyChange={setSelectedGalaxy}
        onPlatformToggle={handlePlatformToggle}
        onSearchChange={setSearch}
        onWindowChange={setTimeWindow}
        onReset={handleReset}
      />

      <section className="stage">
        <header className="top-bar">
          <div>
            <span>实时趋势雷达</span>
            <h1>AI 多星系热度图</h1>
          </div>
          <div className="status-strip">
            <StatusPill icon={<Gauge size={15} />} label="总热度" value={compactNumber(totalHeat)} />
            <StatusPill icon={<Layers3 size={15} />} label="星系" value={`${snapshot.galaxies.length} 个`} />
            <StatusPill icon={<RadioTower size={15} />} label="活跃源" value={`${liveProviders} 个`} />
            <StatusPill icon={isLoading ? <Loader2 size={15} className="spin" /> : <Activity size={15} />} label="刷新" value={`${snapshot.refresh_minutes} 分钟`} />
          </div>
        </header>

        {error && (
          <div className="error-banner">
            <AlertTriangle size={16} />
            <span>{error}，当前显示本地演示快照。</span>
          </div>
        )}

        <Suspense fallback={<div className="canvas-loading">三维星系加载中...</div>}>
          <GalaxyCanvas
            nodes={filteredNodes}
            galaxies={snapshot.galaxies.filter((galaxy) => selectedGalaxy === "all" || galaxy.id === selectedGalaxy)}
            selectedEntity={selectedNode?.entity ?? selectedEntity}
            onSelect={(node) => setSelectedEntity(node.entity)}
          />
        </Suspense>

        <TimelineBar
          window={timeWindow}
          generatedAt={snapshot.generated_at}
          isLive={isLive}
          onWindowChange={setTimeWindow}
          onLiveToggle={() => setIsLive((value) => !value)}
          onRefresh={() => void loadSnapshot(timeWindow)}
        />
      </section>

      <DetailPanel node={selectedNode} onClose={() => setSelectedEntity("")} />
    </main>
  );
}

function StatusPill({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <div className="status-pill">
      {icon}
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
