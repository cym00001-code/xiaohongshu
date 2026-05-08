import { Html, OrbitControls } from "@react-three/drei";
import { Canvas, useFrame } from "@react-three/fiber";
import { memo, useMemo, useRef } from "react";
import * as THREE from "three";
import type { GalaxyInfo, TrendNode } from "../types";
import { compactNumber } from "../format";

type GalaxyCanvasProps = {
  nodes: TrendNode[];
  galaxies: GalaxyInfo[];
  selectedEntity: string;
  onSelect: (node: TrendNode) => void;
};

const galaxyCenters: Record<string, [number, number, number]> = {
  global_models: [0, 0.4, 0],
  china_ai: [-4.8, -1.05, -0.6],
  frontier_ai: [4.65, -0.85, 0.5],
  tooling: [0.2, -3.85, -0.2]
};

const galaxyScale: Record<string, number> = {
  global_models: 1.38,
  china_ai: 0.98,
  frontier_ai: 0.98,
  tooling: 0.9
};

type PositionedNode = TrendNode & {
  position: [number, number, number];
  radius: number;
  isSelected: boolean;
};

export function GalaxyCanvas({ nodes, galaxies, selectedEntity, onSelect }: GalaxyCanvasProps) {
  const positioned = useMemo(() => {
    const groups = nodes.reduce<Record<string, TrendNode[]>>((acc, node) => {
      acc[node.galaxy] = [...(acc[node.galaxy] ?? []), node];
      return acc;
    }, {});

    return nodes.map<PositionedNode>((node) => {
      const siblings = groups[node.galaxy] ?? [];
      const index = Math.max(0, siblings.findIndex((item) => item.entity === node.entity));
      const count = Math.max(1, siblings.length);
      const center = galaxyCenters[node.galaxy] ?? [0, 0, 0];
      const angle = (index / count) * Math.PI * 2 - Math.PI / 5;
      const spread = (galaxyScale[node.galaxy] ?? 1) * (1.48 + Math.min(count, 6) * 0.3);
      const radius = 0.2 + Math.min(node.heat / 1800, 0.34);
      return {
        ...node,
        radius,
        isSelected: node.entity === selectedEntity,
        position: [
          center[0] + Math.cos(angle) * spread,
          center[1] + Math.sin(angle) * spread * 0.5,
          center[2] + Math.sin(angle * 1.4) * 0.85
        ]
      };
    });
  }, [nodes, selectedEntity]);

  return (
    <div className="galaxy-canvas" aria-label="AI 趋势多星系三维视图">
      <Canvas camera={{ position: [0, 2.8, 19.5], fov: 42 }} dpr={[1, 1.75]}>
        <color attach="background" args={["#03070d"]} />
        <ambientLight intensity={0.35} />
        <pointLight position={[0, 3, 5]} intensity={1.6} color="#7bd4ff" />
        <pointLight position={[-6, 0, 4]} intensity={0.9} color="#ffb44a" />
        <pointLight position={[6, -1, 3]} intensity={0.8} color="#65e28b" />
        <StarField />
        {galaxies.map((galaxy) => (
          <GalaxyCluster key={galaxy.id} galaxy={galaxy} />
        ))}
        {positioned.map((node) => (
          <TrendPlanet key={node.entity} node={node} onSelect={onSelect} />
        ))}
        <OrbitControls
          enableDamping
          dampingFactor={0.06}
          minDistance={8}
          maxDistance={17}
          maxPolarAngle={Math.PI / 1.85}
          minPolarAngle={Math.PI / 3.2}
        />
      </Canvas>
      <div className="canvas-legend">
        <span>星体大小=热度</span>
        <span>脉冲=增长</span>
        <span>色彩=口碑</span>
        <span>轨道=平台来源</span>
      </div>
    </div>
  );
}

function GalaxyCluster({ galaxy }: { galaxy: GalaxyInfo }) {
  const center = galaxyCenters[galaxy.id] ?? [0, 0, 0];
  const scale = galaxyScale[galaxy.id] ?? 1;
  const groupRef = useRef<THREE.Group>(null);

  useFrame((state) => {
    if (groupRef.current) {
      groupRef.current.rotation.z = Math.sin(state.clock.elapsedTime * 0.12) * 0.012;
    }
  });

  return (
    <group ref={groupRef} position={center}>
      <mesh rotation={[Math.PI / 2.4, 0, 0]}>
        <torusGeometry args={[2.1 * scale, 0.008, 12, 160]} />
        <meshBasicMaterial color={galaxy.color} transparent opacity={0.34} />
      </mesh>
      <mesh rotation={[Math.PI / 2.15, 0.15, 0.22]}>
        <torusGeometry args={[2.75 * scale, 0.005, 12, 160]} />
        <meshBasicMaterial color={galaxy.color} transparent opacity={0.18} />
      </mesh>
      <mesh rotation={[Math.PI / 2.05, -0.25, -0.12]}>
        <torusGeometry args={[3.22 * scale, 0.004, 12, 180]} />
        <meshBasicMaterial color="#7f93a9" transparent opacity={0.12} />
      </mesh>
      <Html center position={[0, -2.35 * scale, 0]} distanceFactor={12}>
        <div className="galaxy-label">
          <strong>{galaxy.label}</strong>
          <span>{galaxy.description}</span>
        </div>
      </Html>
    </group>
  );
}

function TrendPlanet({ node, onSelect }: { node: PositionedNode; onSelect: (node: TrendNode) => void }) {
  const planetRef = useRef<THREE.Mesh>(null);
  const haloRef = useRef<THREE.Mesh>(null);
  const color = new THREE.Color(node.color);
  const sentimentColor = node.sentiment < -0.18 ? "#ff5264" : node.sentiment > 0.35 ? "#65e28b" : node.color;

  useFrame((state) => {
    const elapsed = state.clock.elapsedTime;
    if (planetRef.current) {
      planetRef.current.rotation.y += 0.006 + Math.max(node.growth, 0) / 40000;
      const pulse = 1 + Math.sin(elapsed * (1.6 + Math.abs(node.growth) / 55)) * 0.035;
      planetRef.current.scale.setScalar(node.isSelected ? pulse * 1.12 : pulse);
    }
    if (haloRef.current) {
      const haloPulse = 1 + Math.sin(elapsed * 2.1) * 0.12;
      haloRef.current.scale.setScalar(node.isSelected ? haloPulse * 1.28 : haloPulse);
    }
  });

  return (
    <group position={node.position}>
      <mesh ref={haloRef}>
        <sphereGeometry args={[node.radius * 1.42, 32, 32]} />
        <meshBasicMaterial color={sentimentColor} transparent opacity={node.isSelected ? 0.2 : 0.1} />
      </mesh>
      <mesh ref={planetRef} onClick={(event) => {
        event.stopPropagation();
        onSelect(node);
      }}>
        <sphereGeometry args={[node.radius, 48, 48]} />
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={node.isSelected ? 1.45 : 0.8}
          metalness={0.22}
          roughness={0.35}
        />
      </mesh>
      <PlatformRings node={node} />
      <Html center position={[0, node.radius + 0.72, 0]} distanceFactor={10}>
        <button className={`planet-label ${node.isSelected ? "is-selected" : ""}`} onClick={() => onSelect(node)}>
          <strong>{node.label}</strong>
          <span>热度 {compactNumber(node.heat)}</span>
        </button>
      </Html>
    </group>
  );
}

function PlatformRings({ node }: { node: PositionedNode }) {
  const platforms = Object.keys(node.platform_distribution).slice(0, 5);
  const colors = ["#2f91ff", "#ff9c2b", "#ff4b4b", "#8f68ff", "#cbd5e1"];
  return (
    <>
      {platforms.map((platform, index) => (
        <mesh key={platform} rotation={[Math.PI / 2.1, index * 0.2, index * 0.13]}>
          <torusGeometry args={[node.radius * (1.55 + index * 0.3), 0.01, 8, 120]} />
          <meshBasicMaterial color={colors[index % colors.length]} transparent opacity={node.isSelected ? 0.85 : 0.46} />
        </mesh>
      ))}
    </>
  );
}

const StarField = memo(function StarField() {
  const geometry = useMemo(() => {
    const vertices = new Float32Array(650 * 3);
    for (let index = 0; index < 650; index += 1) {
      vertices[index * 3] = (Math.random() - 0.5) * 24;
      vertices[index * 3 + 1] = (Math.random() - 0.5) * 12;
      vertices[index * 3 + 2] = -6 - Math.random() * 10;
    }
    const starGeometry = new THREE.BufferGeometry();
    starGeometry.setAttribute("position", new THREE.BufferAttribute(vertices, 3));
    return starGeometry;
  }, []);

  return (
    <points geometry={geometry}>
      <pointsMaterial color="#8fc7ff" size={0.035} sizeAttenuation transparent opacity={0.72} />
    </points>
  );
});
