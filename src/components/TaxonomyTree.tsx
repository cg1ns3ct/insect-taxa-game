import type { TaxonNode } from "../types";
import { rankLabel } from "../lib/scoring";

interface Props {
  nodes: Record<string, TaxonNode>;
  rootId: number;
  expanded: Set<number>;
  selectedId: number | null;
  selectedPath: Set<number>;
  correctPath: Set<number>;
  onToggle: (id: number) => void;
  onSelect: (id: number) => void;
  disabled?: boolean;
}

interface RowProps extends Props {
  id: number;
  depth: number;
}

function TreeRow({
  id,
  depth,
  nodes,
  expanded,
  selectedId,
  selectedPath,
  correctPath,
  onToggle,
  onSelect,
  disabled,
}: RowProps) {
  const node = nodes[String(id)];
  if (!node) return null;
  const hasChildren = node.children.length > 0;
  const isExpanded = expanded.has(id);
  const isSelected = selectedId === id;
  const isOnSelectedPath = selectedPath.has(id);
  const isCorrect = correctPath.has(id);
  const classes = [
    "tree-row",
    isSelected ? "is-selected" : "",
    isOnSelectedPath ? "is-on-path" : "",
    isCorrect ? "is-correct" : "",
    node.scoring ? "is-scoring" : "is-aux",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className="tree-branch">
      <div
        className={classes}
        style={{ paddingLeft: `${10 + depth * 17}px` }}
        role="treeitem"
        aria-selected={isSelected}
        aria-expanded={hasChildren ? isExpanded : undefined}
      >
        <button
          type="button"
          className={`tree-toggle ${hasChildren ? "" : "is-empty"}`}
          onClick={(event) => {
            event.stopPropagation();
            if (hasChildren) onToggle(id);
          }}
          aria-label={isExpanded ? "收起" : "展开"}
          tabIndex={hasChildren ? 0 : -1}
        >
          {hasChildren ? (isExpanded ? "−" : "+") : "·"}
        </button>
        <button
          type="button"
          className="tree-label"
          onClick={() => {
            if (!disabled) onSelect(id);
          }}
          disabled={disabled}
        >
          <span className="tree-names">
            <span className="tree-zh">{node.zh ?? node.name}</span>
            {node.zh && <span className="tree-latin">{node.name}</span>}
          </span>
          <span
            className={`rank-pill rank-${node.rank} ${
              node.scoring ? "is-scoring-pill" : "is-aux-pill"
            }`}
          >
            {rankLabel(node.rank)}
          </span>
        </button>
      </div>
      {hasChildren && isExpanded && (
        <div className="tree-children" role="group">
          {node.children.map((childId) => (
            <TreeRow
              key={childId}
              id={childId}
              depth={depth + 1}
              nodes={nodes}
              rootId={0}
              expanded={expanded}
              selectedId={selectedId}
              selectedPath={selectedPath}
              correctPath={correctPath}
              onToggle={onToggle}
              onSelect={onSelect}
              disabled={disabled}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export function TaxonomyTree(props: Props) {
  const root = props.nodes[String(props.rootId)];
  if (!root) return <div className="tree-empty">分类树未加载。</div>;
  return (
    <div className="tree" role="tree" aria-label="昆虫分类树">
      <div className="tree-root">
        <span className="tree-root-mark">昆虫纲</span>
        <span className="tree-root-latin">Insecta</span>
        <span className="tree-root-note">从目开始计分</span>
      </div>
      <div className="tree-children">
        {root.children.map((childId) => (
          <TreeRow key={childId} id={childId} depth={0} {...props} />
        ))}
      </div>
    </div>
  );
}
