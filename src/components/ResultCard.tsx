import type { GameData, GuessResult } from "../types";
import { buildPath, nodeLabel, rankLabel } from "../lib/scoring";

interface Props {
  data: GameData;
  result: GuessResult;
  onNext: () => void;
  isLast: boolean;
}

export function ResultCard({ data, result, onNext, isLast }: Props) {
  const targetPath = buildPath(result.targetId, data.nodes);
  const guessPath = buildPath(result.guessId, data.nodes);
  const checkpoint = result.checkpointId
    ? data.nodes[String(result.checkpointId)]
    : null;
  const target = data.nodes[String(result.targetId)];
  const guess = data.nodes[String(result.guessId)];
  const targetIds = new Set(targetPath.map((n) => n.id));

  let headline = "这道题先记下";
  if (result.exact) headline = "种级全中";
  else if (result.onTargetPath && checkpoint)
    headline = `正确到${rankLabel(checkpoint.rank)}`;
  else if (checkpoint) headline = `在${rankLabel(checkpoint.rank)}分叉`;

  return (
    <section className="result-card" id="result">
      <div className="result-score">
        <span className="result-score-number">{result.score}</span>
        <span className="result-score-unit">/ 100</span>
      </div>

      <div className="result-main">
        <p className="result-kicker">{headline}</p>
        <h2>
          {target?.zh ?? target?.name}
          {target?.zh && <em>{target?.name}</em>}
        </h2>

        <p className="result-summary">
          {result.exact ? (
            <>你直接答到了种，分类路径完全一致。</>
          ) : result.onTargetPath && checkpoint ? (
            <>
              你的选择在正确路径上，计分到
              <strong>{nodeLabel(checkpoint)}</strong>（
              {rankLabel(checkpoint.rank)}）。
            </>
          ) : (
            <>
              你和正确答案在 <strong>{nodeLabel(checkpoint ?? undefined)}</strong>
              （{checkpoint ? rankLabel(checkpoint.rank) : "未到计分阶元"}）分开，
              错枝按 90% 计分。
            </>
          )}
        </p>

        {guess && !guess.scoring && (
          <p className="result-note">
            你选的是 <strong>{nodeLabel(guess)}</strong>，这是检索阶元；
            它不单独计分，按上方最近的计分阶元计算。
          </p>
        )}

        <div className="result-paths">
          <div className="path-block">
            <span className="path-caption">正确路径</span>
            <div className="path-list">
              {targetPath.slice(1).map((node) => {
                const isCheckpoint = node.id === result.checkpointId;
                return (
                  <span
                    key={node.id}
                    className={`path-chip ${
                      node.scoring ? "is-scoring" : "is-aux"
                    } ${isCheckpoint ? "is-checkpoint" : ""}`}
                  >
                    {nodeLabel(node)}
                    <small>{rankLabel(node.rank)}</small>
                  </span>
                );
              })}
            </div>
          </div>

          {!result.exact && (
            <div className="path-block path-block-muted">
              <span className="path-caption">你的路径</span>
              <div className="path-list">
                {guessPath.slice(1).map((node) => (
                  <span
                    key={node.id}
                    className={`path-chip ${
                      targetIds.has(node.id) ? "is-correct" : "is-wrong"
                    }`}
                  >
                    {nodeLabel(node)}
                    <small>{rankLabel(node.rank)}</small>
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="result-footer">
          <p className="result-explain">
            计分阶元只有目、亚目、科、亚科、属、种；总科、下目、族、亚属等保留在树里，
            但作为检索阶元，不单独计分。
          </p>
          <button className="primary-button" type="button" onClick={onNext}>
            {isLast ? "看本局结果" : "下一题"}
          </button>
        </div>
      </div>
    </section>
  );
}
