import type { GuessResult, TaxonNode } from "../types";

export const RANK_ORDER = [
  "order",
  "suborder",
  "infraorder",
  "superfamily",
  "family",
  "subfamily",
  "tribe",
  "genus",
  "subgenus",
  "species",
];

export const RANK_LABEL: Record<string, string> = {
  class: "纲",
  subclass: "亚纲",
  infraclass: "附纲",
  superorder: "总目",
  order: "目",
  suborder: "亚目",
  infraorder: "下目",
  parvorder: "小目",
  superfamily: "总科",
  epifamily: "表科",
  family: "科",
  subfamily: "亚科",
  supertribe: "总族",
  tribe: "族",
  subtribe: "亚族",
  genus: "属",
  subgenus: "亚属",
  section: "组",
  subsection: "亚组",
  zoosection: "派",
  zoosubsection: "亚派",
  complex: "复合种",
  species: "种",
  subspecies: "亚种",
  variety: "变种",
  form: "变型",
  hybrid: "杂交种",
};

export function rankLabel(rank: string): string {
  return RANK_LABEL[rank] ?? rank;
}

export function nodeLabel(node: TaxonNode | undefined): string {
  if (!node) return "未知";
  return node.zh ? `${node.zh} ${node.name}` : node.name;
}

export function buildPath(
  id: number,
  nodes: Record<string, TaxonNode>,
): TaxonNode[] {
  const path: TaxonNode[] = [];
  let cursor: TaxonNode | undefined = nodes[String(id)];
  const seen = new Set<number>();
  while (cursor && !seen.has(cursor.id)) {
    path.push(cursor);
    seen.add(cursor.id);
    cursor = cursor.parentId == null ? undefined : nodes[String(cursor.parentId)];
  }
  return path.reverse();
}

export function lcaId(a: number, b: number, nodes: Record<string, TaxonNode>): number {
  const pa = buildPath(a, nodes).map((n) => n.id);
  const pb = new Set(buildPath(b, nodes).map((n) => n.id));
  let id = a;
  for (let i = pa.length - 1; i >= 0; i -= 1) {
    if (pb.has(pa[i])) {
      id = pa[i];
      break;
    }
  }
  return id;
}

export function nearestScoring(
  path: TaxonNode[],
): TaxonNode | null {
  for (let i = path.length - 1; i >= 0; i -= 1) {
    if (path[i].scoring) return path[i];
  }
  return null;
}

export function scoreGuess(
  targetId: number,
  guessId: number,
  nodes: Record<string, TaxonNode>,
  scoring: Record<string, number>,
): GuessResult {
  const targetPath = buildPath(targetId, nodes);
  const guessPath = buildPath(guessId, nodes);
  const targetIds = new Set(targetPath.map((n) => n.id));
  const onTargetPath = targetIds.has(guessId);
  const lca = lcaId(targetId, guessId, nodes);
  const lcaPath = buildPath(lca, nodes);
  const checkpoint = nearestScoring(lcaPath);

  if (!checkpoint) {
    return {
      targetId,
      guessId,
      lcaId: lca,
      checkpointId: null,
      checkpointRank: null,
      baseScore: 0,
      score: 0,
      onTargetPath,
      exact: targetId === guessId,
    };
  }

  const baseScore = scoring[checkpoint.rank] ?? 0;
  const raw = onTargetPath ? baseScore : Math.max(0, baseScore - 5);
  return {
    targetId,
    guessId,
    lcaId: lca,
    checkpointId: checkpoint.id,
    checkpointRank: checkpoint.rank,
    baseScore,
    score: Math.round(raw),
    onTargetPath,
    exact: targetId === guessId,
  };
}

export function pathLabels(
  ids: number[],
  nodes: Record<string, TaxonNode>,
): string[] {
  return ids.map((id) => nodeLabel(nodes[String(id)]));
}
