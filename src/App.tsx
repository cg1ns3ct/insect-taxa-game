import { useEffect, useMemo, useState } from "react";
import { ImagePanel } from "./components/ImagePanel";
import { SearchBox } from "./components/SearchBox";
import { TaxonomyTree } from "./components/TaxonomyTree";
import { ResultCard } from "./components/ResultCard";
import { EndScreen } from "./components/EndScreen";
import { buildSearchIndex } from "./lib/search";
import {
  buildPath,
  nearestScoring,
  nodeLabel,
  rankLabel,
  scoreGuess,
} from "./lib/scoring";
import type { GameData, GuessResult, Round } from "./types";

const BASE = import.meta.env.BASE_URL;
const ROUNDS_PER_GAME = 10;

function shuffle<T>(items: T[]): T[] {
  const copy = [...items];
  for (let i = copy.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
}

function initialExpanded(data: GameData): Set<number> {
  const set = new Set<number>([data.rootId]);
  const root = data.nodes[String(data.rootId)];
  if (!root?.children.length) return set;
  const pterygota = root.children.find(
    (id) => data.nodes[String(id)]?.name === "Pterygota",
  );
  set.add(pterygota ?? root.children[0]);
  return set;
}

export default function App() {
  const [data, setData] = useState<GameData | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [session, setSession] = useState<Round[]>([]);
  const [index, setIndex] = useState(0);
  const [guessId, setGuessId] = useState<number | null>(null);
  const [result, setResult] = useState<GuessResult | null>(null);
  const [answers, setAnswers] = useState<
    { round: Round; result: GuessResult }[]
  >([]);
  const [score, setScore] = useState(0);
  const [finished, setFinished] = useState(false);
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  useEffect(() => {
    fetch(`${BASE}data/game.json`)
      .then((response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json() as Promise<GameData>;
      })
      .then((payload) => {
        const rounds = shuffle(payload.rounds).slice(
          0,
          Math.min(ROUNDS_PER_GAME, payload.rounds.length),
        );
        setData(payload);
        setSession(rounds);
        setExpanded(initialExpanded(payload));
      })
      .catch((error: unknown) => {
        setLoadError(error instanceof Error ? error.message : String(error));
      });
  }, []);

  const currentRound = session[index];

  useEffect(() => {
    if (!currentRound) return;
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, [currentRound]);

  useEffect(() => {
    if (result) {
      const node = document.getElementById("result");
      window.setTimeout(
        () => node?.scrollIntoView({ behavior: "smooth", block: "start" }),
        80,
      );
    }
  }, [result]);

  const searchIndex = useMemo(
    () => (data ? buildSearchIndex(data.nodes) : []),
    [data],
  );

  const selectedPath = useMemo(() => {
    if (!data || guessId == null) return [];
    return buildPath(guessId, data.nodes);
  }, [data, guessId]);

  const selectedNode = data && guessId != null ? data.nodes[String(guessId)] : null;
  const guessCheckpoint =
    selectedPath.length > 0 ? nearestScoring(selectedPath) : null;

  const correctPath = useMemo(() => {
    if (!data || !result) return new Set<number>();
    return new Set(buildPath(result.targetId, data.nodes).map((node) => node.id));
  }, [data, result]);

  const selectedPathSet = useMemo(
    () => new Set(selectedPath.map((node) => node.id)),
    [selectedPath],
  );

  const canSubmit =
    Boolean(data) &&
    guessId != null &&
    guessCheckpoint != null &&
    result == null &&
    !finished;

  function startNewGame(payload: GameData) {
    const rounds = shuffle(payload.rounds).slice(
      0,
      Math.min(ROUNDS_PER_GAME, payload.rounds.length),
    );
    setSession(rounds);
    setIndex(0);
    setGuessId(null);
    setResult(null);
    setAnswers([]);
    setScore(0);
    setFinished(false);
    setExpanded(initialExpanded(payload));
  }

  function handleSubmit() {
    if (!data || !currentRound || guessId == null || !canSubmit) return;
    const next = scoreGuess(
      currentRound.taxonId,
      guessId,
      data.nodes,
      data.scoring,
    );
    setResult(next);
    setScore((value) => value + next.score);
    setAnswers((value) => [...value, { round: currentRound, result: next }]);
    const targetPath = buildPath(next.targetId, data.nodes);
    setExpanded((value) => {
      const copy = new Set(value);
      targetPath.forEach((node) => copy.add(node.id));
      return copy;
    });
  }

  function handleNext() {
    if (!data) return;
    if (index + 1 >= session.length) {
      setFinished(true);
      return;
    }
    setIndex((value) => value + 1);
    setGuessId(null);
    setResult(null);
    setExpanded(initialExpanded(data));
  }

  function handleJump(id: number) {
    if (!data) return;
    const path = buildPath(id, data.nodes);
    setExpanded((value) => {
      const copy = new Set(value);
      path.forEach((node) => copy.add(node.id));
      return copy;
    });
    setGuessId(id);
  }

  function toggle(id: number) {
    setExpanded((value) => {
      const copy = new Set(value);
      if (copy.has(id)) copy.delete(id);
      else copy.add(id);
      return copy;
    });
  }

  if (loadError) {
    return (
      <div className="center-state">
        <h1>题库没有加载成功</h1>
        <p>{loadError}</p>
        <p>请确认 `public/data/game.json` 已经生成。</p>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="center-state">
        <div className="loading-mark">虫</div>
        <p>正在翻开图鉴…</p>
      </div>
    );
  }

  if (finished) {
    return (
      <div className="app">
        <Header score={score} max={session.length * 100} index={session.length} total={session.length} />
        <main className="main">
          <EndScreen
            data={data}
            answers={answers}
            score={score}
            onRestart={() => startNewGame(data)}
          />
        </main>
        <Footer data={data} />
      </div>
    );
  }

  if (!currentRound) {
    return (
      <div className="center-state">
        <h1>题库还是空的</h1>
        <p>先跑数据管线生成 `game.json`。</p>
      </div>
    );
  }

  return (
    <div className="app">
      <Header
        score={score}
        max={session.length * 100}
        index={index + 1}
        total={session.length}
      />

      <main className="main">
        <div className="game-grid">
          <div className="left-column">
            <ImagePanel round={currentRound} baseUrl={BASE} />
            <div className="round-tip">
              <span className="tip-mark">怎么看</span>
              先看整体轮廓、翅、触角、足，再决定停在哪个阶元。越有把握，越往下点。
            </div>
          </div>

          <section className="answer-panel" aria-label="分类树作答区">
            <div className="answer-head">
              <div>
                <p className="eyebrow">你的判断</p>
                <h1>它属于哪一支？</h1>
              </div>
              <span className="round-counter">
                {String(index + 1).padStart(2, "0")} / {String(session.length).padStart(2, "0")}
              </span>
            </div>

            <SearchBox index={searchIndex} onJump={handleJump} />

            <div className="selection-strip">
              <span className="selection-kicker">当前选择</span>
              {selectedNode ? (
                <div className="selection-content">
                  <div className="selection-breadcrumb">
                    {selectedPath.slice(1).map((node, i) => (
                      <span key={node.id}>
                        {i > 0 && <b>›</b>}
                        {node.zh ?? node.name}
                      </span>
                    ))}
                  </div>
                  <span className="selection-current">
                    {nodeLabel(selectedNode)}
                    <span className="rank-pill">{rankLabel(selectedNode.rank)}</span>
                  </span>
                  {!selectedNode.scoring && guessCheckpoint && (
                    <span className="selection-note">
                      检索阶元，按 {nodeLabel(guessCheckpoint)}（{rankLabel(guessCheckpoint.rank)}）计分
                    </span>
                  )}
                  {selectedNode.scoring && (
                    <span className="selection-note is-scoring">
                      计分阶元 · 本级 {guessCheckpoint ? data.scoring[guessCheckpoint.rank] : 0} 分
                    </span>
                  )}
                </div>
              ) : (
                <p className="selection-empty">在下面的树里展开，或直接搜索阶元。</p>
              )}
            </div>

            <div className="tree-scroll">
              <TaxonomyTree
                nodes={data.nodes}
                rootId={data.rootId}
                expanded={expanded}
                selectedId={guessId}
                selectedPath={selectedPathSet}
                correctPath={correctPath}
                onToggle={toggle}
                onSelect={(id) => setGuessId(id)}
                disabled={result != null}
              />
            </div>

            <div className="submit-bar">
              <div className="submit-copy">
                {result ? (
                  <span>已提交，往下看复盘。</span>
                ) : guessCheckpoint ? (
                  <span>
                    提交后按你与正确答案的<strong>共同祖先</strong>结算
                    {selectedNode && !selectedNode.scoring ? "；检索阶元向上取最近计分阶元" : ""}
                  </span>
                ) : (
                  <span>至少选到目，才能提交。</span>
                )}
              </div>
              <button
                type="button"
                className="primary-button"
                onClick={handleSubmit}
                disabled={!canSubmit}
              >
                提交答案
              </button>
            </div>
          </section>
        </div>

        {result && (
          <ResultCard
            data={data}
            result={result}
            onNext={handleNext}
            isLast={index + 1 >= session.length}
          />
        )}
      </main>

      <Footer data={data} />
    </div>
  );
}

function Header({
  score,
  max,
  index,
  total,
}: {
  score: number;
  max: number;
  index: number;
  total: number;
}) {
  return (
    <header className="site-header">
      <div className="brand">
        <span className="brand-mark">虫阶</span>
        <span className="brand-sub">昆虫分类阶元猜谜</span>
      </div>
      <div className="header-stats">
        <div className="stat">
          <span className="stat-label">进度</span>
          <span className="stat-value">
            {Math.min(index, total)}<small> / {total}</small>
          </span>
        </div>
        <div className="stat">
          <span className="stat-label">得分</span>
          <span className="stat-value">
            {score}<small> / {max}</small>
          </span>
        </div>
        <div className="progress-track" aria-hidden="true">
          <span style={{ width: `${total ? (Math.min(index, total) / total) * 100 : 0}%` }} />
        </div>
      </div>
    </header>
  );
}

function Footer({ data }: { data: GameData }) {
  const date = new Date(data.generatedAt).toLocaleDateString("zh-CN");
  return (
    <footer className="site-footer">
      <span>虫阶 · 记录与图片来自 iNaturalist（cg1ns3ct、yy_never_air_force 及社区），遵循各自 CC 许可</span>
      <span>
        {data.counts.taxa.toLocaleString()} 个节点 · {data.counts.rounds} 道题 · 快照 {date}
      </span>
      <span>非商业学习项目</span>
    </footer>
  );
}
