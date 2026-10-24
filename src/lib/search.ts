import { pinyin } from "pinyin-pro";
import type { TaxonNode } from "../types";
import { buildPath, nodeLabel, rankLabel } from "./scoring";

export interface SearchEntry {
  id: number;
  name: string;
  zh: string | null;
  rank: string;
  pinyin: string;
  path: string;
  score?: number;
}

function normalize(value: string): string {
  return value
    .toLowerCase()
    .replace(/[\s\-_.,'’·]+/g, "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

export function buildSearchIndex(
  nodes: Record<string, TaxonNode>,
): SearchEntry[] {
  return Object.values(nodes).map((node) => {
    const path = buildPath(node.id, nodes)
      .map((item) => nodeLabel(item))
      .join(" › ");
    let py = "";
    if (node.zh) {
      try {
        py = pinyin(node.zh, { toneType: "none", type: "array" }).join("");
      } catch {
        py = "";
      }
    }
    return {
      id: node.id,
      name: node.name,
      zh: node.zh,
      rank: node.rank,
      pinyin: py,
      path,
    };
  });
}

export function searchTaxa(
  index: SearchEntry[],
  rawQuery: string,
  limit = 30,
): SearchEntry[] {
  const query = normalize(rawQuery);
  if (!query) return [];
  const results: SearchEntry[] = [];
  for (const entry of index) {
    const name = normalize(entry.name);
    const zh = entry.zh ? normalize(entry.zh) : "";
    const py = normalize(entry.pinyin);
    let score = 0;
    if (name === query || zh === query) score = 120;
    else if (name.startsWith(query) || zh.startsWith(query)) score = 90;
    else if (name.includes(query) || zh.includes(query)) score = 70;
    else if (py.startsWith(query)) score = 60;
    else if (py.includes(query)) score = 40;
    if (score > 0) results.push({ ...entry, score });
  }
  results.sort(
    (a, b) =>
      (b.score ?? 0) - (a.score ?? 0) ||
      (b.zh ? 1 : 0) - (a.zh ? 1 : 0) ||
      a.rank.localeCompare(b.rank) ||
      a.name.localeCompare(b.name),
  );
  return results.slice(0, limit);
}

export function rankText(rank: string): string {
  return rankLabel(rank);
}
