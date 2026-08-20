import React from "react";

function TreeNode({ node, selectedId, onSelect, depth }) {
  if (node.is_group) {
    return (
      <div>
        <div className="tree-group-label">{node.code} — {node.title}</div>
        {node.children.map((child) => (
          <TreeNode key={child.id} node={child} selectedId={selectedId} onSelect={onSelect} depth={depth + 1} />
        ))}
      </div>
    );
  }
  return (
    <div
      className={`tree-item ${selectedId === node.id ? "active" : ""}`}
      onClick={() => onSelect(node.id)}
    >
      <span className={`status-dot ${node.status || "open"}`}></span>
      <span className="tree-item-code">{node.code}</span>
      <span className="tree-item-label">{node.title}</span>
    </div>
  );
}

export default function Sidebar({ catalog, tree, selectedId, onSelect }) {
  return (
    <div className="col col-nav">
      <div className="col-header">
        <div className="col-eyebrow">Navigation &amp; Scope</div>
        <div className="col-heading">{catalog ? catalog.title : "Katalog wird geladen…"}</div>
      </div>
      <div className="tree">
        {tree.map((node) => (
          <TreeNode key={node.id} node={node} selectedId={selectedId} onSelect={onSelect} depth={0} />
        ))}
      </div>
    </div>
  );
}
