import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import type { GameData } from "../types";
import { buildSearchIndex, searchTaxa } from "./search";

const data = JSON.parse(
  readFileSync("public/data/game.json", "utf8"),
) as GameData;
const index = buildSearchIndex(data.nodes);

describe("searchTaxa", () => {
  it("finds the Japanese carpenter ant by Chinese name", () => {
    const results = searchTaxa(index, "日本弓背蚁");
    expect(results[0]?.id).toBe(321673);
  });

  it("finds it by scientific name", () => {
    const results = searchTaxa(index, "Camponotus japonicus");
    expect(results[0]?.id).toBe(321673);
  });

  it("finds a family by Chinese name", () => {
    const results = searchTaxa(index, "蚁科");
    expect(results.some((entry) => entry.id === 47336)).toBe(true);
  });
});
