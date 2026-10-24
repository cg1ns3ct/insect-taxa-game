import { useState } from "react";
import type { GameData, GuessResult, Round } from "../types";

interface Props {
  data: GameData;
  answers: { round: Round; result: GuessResult }[];
  score: number;
  onRestart: () => void;
}

export function EndScreen({ data, answers, score, onRestart }: Props) {
  const [copied, setCopied] = useState(false);
  const max = answers.length * 100;
  const percent = max ? Math.round((score / max) * 100) : 0;

  async function share() {
    const text = `虫阶 · 昆虫分类阶元猜谜\n本局 ${score}/${max}（${percent}%）\n${answers
      .map(({ round, result }) => {
        const target = data.nodes[String(round.taxonId)];
        return `${result.score} 分 · ${target?.zh ?? target?.name}`;
      })
      .join("\n")}`;
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      setCopied(false);
    }
  }

  return (
    <section className="end-screen">
      <p className="eyebrow">本局结束</p>
      <div className="end-score">
        <span>{score}</span>
        <small>/ {max}</small>
      </div>
      <h1>{percent >= 80 ? "分类学家" : percent >= 55 ? "熟练观察者" : "继续看虫"}</h1>
      <p className="end-copy">
        你平均每题拿到 {answers.length ? Math.round(score / answers.length) : 0} 分。
        想再细一点，就多展开一级；想稳一点，就在科、属停手。
      </p>

      <div className="end-list">
        {answers.map(({ round, result }, index) => {
          const target = data.nodes[String(round.taxonId)];
          const checkpoint = result.checkpointId
            ? data.nodes[String(result.checkpointId)]
            : null;
          return (
            <div className="end-row" key={`${round.taxonId}-${index}`}>
              <span className="end-index">{String(index + 1).padStart(2, "0")}</span>
              <span className="end-name">
                {target?.zh ?? target?.name}
                {target?.zh && <em>{target?.name}</em>}
              </span>
              <span className="end-path">
                {result.exact
                  ? "种级全中"
                  : checkpoint
                    ? `到${checkpoint.zh ?? checkpoint.name}`
                    : "未到计分阶元"}
              </span>
              <span className={`end-points ${result.exact ? "is-full" : ""}`}>
                {result.score}
              </span>
            </div>
          );
        })}
      </div>

      <div className="end-actions">
        <button className="primary-button" type="button" onClick={onRestart}>
          再来一局
        </button>
        <button className="ghost-button" type="button" onClick={share}>
          {copied ? "已复制成绩" : "复制成绩"}
        </button>
      </div>
      <p className="end-credits">
        图片来自 iNaturalist，遵循各图 CC 许可；分类快照见页脚。
      </p>
    </section>
  );
}
