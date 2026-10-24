export type Rank =
  | "order"
  | "suborder"
  | "infraorder"
  | "superfamily"
  | "family"
  | "subfamily"
  | "tribe"
  | "genus"
  | "subgenus"
  | "species"
  | string;

export interface TaxonNode {
  id: number;
  parentId: number | null;
  name: string;
  zh: string | null;
  rank: Rank;
  rankLevel: number | null;
  observationsCount: number | null;
  scoring: boolean;
  children: number[];
}

export interface Round {
  taxonId: number;
  image: string;
  source: "owner" | "community" | "contributor";
  contributor?: string;
  placeScope?: "china" | "global";
  observationId: number;
  observationUrl: string;
  observedOn: string | null;
  placeGuess: string | null;
  license: string;
  attribution: string;
  agreements: number | null;
  identifications: number | null;
  evidence?: string | null;
  lifeStage?: string | null;
}

export interface GameData {
  version: number;
  generatedAt: string;
  rootId: number;
  scoring: Record<string, number>;
  scoringRanks: string[];
  counts: {
    taxa: number;
    rounds: number;
    targets: number;
    ownerRounds: number;
    contributorRounds?: number;
    extras?: number;
  };
  nodes: Record<string, TaxonNode>;
  rounds: Round[];
  extras?: Round[];
}

export interface GuessResult {
  targetId: number;
  guessId: number;
  lcaId: number;
  checkpointId: number | null;
  checkpointRank: string | null;
  baseScore: number;
  score: number;
  onTargetPath: boolean;
  exact: boolean;
}
