import type { Round } from "../types";

interface Props {
  round: Round;
  baseUrl: string;
}

function shortPlace(place: string | null): string {
  if (!place) return "地点未记录";
  return place
    .replace(/邮政编码[:：]?\s*\d+/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function shortDate(date: string | null): string {
  if (!date) return "日期未记录";
  const parts = date.split("-");
  if (parts.length >= 2) return `${parts[0]} 年 ${Number(parts[1])} 月`;
  return date;
}

function licenseLabel(code: string): string {
  return code
    .replace("cc-by-nc-sa", "CC BY-NC-SA")
    .replace("cc-by-nc", "CC BY-NC")
    .replace("cc-by-sa", "CC BY-SA")
    .replace("cc-by", "CC BY")
    .replace("cc0", "CC0");
}

export function ImagePanel({ round, baseUrl }: Props) {
  return (
    <section className="image-panel" aria-label="本轮昆虫图片">
      <div className="image-frame">
        <img
          src={`${baseUrl}${round.image}`}
          alt="本轮需要鉴定的昆虫"
          loading="eager"
        />
        <div className="image-corner">
          <span className={`source-badge source-${round.source}`}>
            {round.source === "owner" ? "自有记录" : "社区记录"}
          </span>
          {round.placeScope === "global" && (
            <span className="source-badge scope-badge">境外同种记录</span>
          )}
        </div>
      </div>
      <div className="image-meta">
        <div className="image-meta-row">
          <span className="meta-label">地点</span>
          <span>{shortPlace(round.placeGuess)}</span>
        </div>
        <div className="image-meta-row">
          <span className="meta-label">时间</span>
          <span>{shortDate(round.observedOn)}</span>
        </div>
        <div className="image-credit">
          <a href={round.observationUrl} target="_blank" rel="noreferrer">
            {round.attribution}
          </a>
          <span> · {licenseLabel(round.license)} · iNaturalist</span>
        </div>
      </div>
    </section>
  );
}
