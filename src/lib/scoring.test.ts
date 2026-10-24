import { describe, expect, it } from "vitest";
import { scoreGuess } from "./scoring";
import type { TaxonNode } from "../types";

const SCORING = {
  order: 15,
  suborder: 25,
  family: 50,
  subfamily: 65,
  genus: 80,
  species: 100,
};

function node(
  id: number,
  parentId: number | null,
  rank: string,
  name: string,
): TaxonNode {
  return {
    id,
    parentId,
    name,
    zh: name,
    rank,
    rankLevel: null,
    observationsCount: null,
    scoring: rank in SCORING,
    children: [],
  };
}

const nodes: Record<string, TaxonNode> = {
  "1": node(1, null, "class", "Insecta"),
  "2": node(2, 1, "order", "Hymenoptera"),
  "3": node(3, 2, "suborder", "Apocrita"),
  "4": node(4, 3, "infraorder", "Aculeata"),
  "5": node(5, 4, "superfamily", "Formicoidea"),
  "6": node(6, 5, "family", "Formicidae"),
  "7": node(7, 6, "subfamily", "Formicinae"),
  "8": node(8, 7, "tribe", "Camponotini"),
  "9": node(9, 8, "genus", "Camponotus"),
  "10": node(10, 9, "species", "Camponotus japonicus"),
  "11": node(11, 9, "species", "Camponotus friedae"),
  "20": node(20, 4, "superfamily", "Vespoidea"),
  "21": node(21, 20, "family", "Vespidae"),
};

describe("scoreGuess", () => {
  it("gives full marks for the exact species", () => {
    const result = scoreGuess(10, 10, nodes, SCORING);
    expect(result.score).toBe(100);
    expect(result.exact).toBe(true);
  });

  it("gives checkpoint credit for a correct ancestor", () => {
    expect(scoreGuess(10, 6, nodes, SCORING).score).toBe(50);
    expect(scoreGuess(10, 9, nodes, SCORING).score).toBe(80);
    expect(scoreGuess(10, 2, nodes, SCORING).score).toBe(15);
  });

  it("does not require a player to select auxiliary ranks", () => {
    expect(scoreGuess(10, 5, nodes, SCORING).score).toBe(25);
    expect(scoreGuess(10, 8, nodes, SCORING).score).toBe(65);
  });

  it("penalizes a wrong branch at the LCA checkpoint", () => {
    const bee = scoreGuess(10, 21, nodes, SCORING);
    expect(bee.score).toBe(23);
    expect(bee.checkpointRank).toBe("suborder");
    expect(bee.onTargetPath).toBe(false);
  });

  it("penalizes a wrong congener at genus", () => {
    const congener = scoreGuess(10, 11, nodes, SCORING);
    expect(congener.score).toBe(72);
    expect(congener.checkpointRank).toBe("genus");
  });

  it("scores zero above the order checkpoint", () => {
    expect(scoreGuess(10, 1, nodes, SCORING).score).toBe(0);
  });
});
