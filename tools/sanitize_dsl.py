#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""清洗 Dify DSL 导出文件中的残留空节点。

背景
----
Dify 编辑器在反复复制/删除节点后，导出的 DSL 里会残留一些 ``data`` 为空、
没有 ``type`` 字段的孤立节点（例如 ``[{"data": {"title": "", "desc": ""}}]``）。
它们不在任何边（edge）上，属于纯粹的编辑器垃圾，但会让导出的 DSL 看起来很乱。

本脚本只做一件事：删除这些**无 type 且没有任何边连接**的节点，然后同步删除
指向已删除节点的边，最后校验：
  1) 所有边的 source/target 都存在于剩余节点中；
  2) 文件仍是合法 YAML，且 ``workflow.graph`` 结构完整。

默认以 dry-run 模式运行，加 ``--write`` 才会落盘。

用法
----
    python tools/sanitize_dsl.py apps                 # 预览
    python tools/sanitize_dsl.py apps --write         # 落盘
"""
from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

import yaml

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def iter_nodes(graph: dict):
    return graph.get("nodes") or []


def sanitize(doc: dict) -> tuple[dict, int, int]:
    """返回 (清洗后的 doc, 删除节点数, 删除边数)。"""
    graph = (doc.get("workflow") or {}).get("graph") or {}
    nodes = iter_nodes(graph)
    edges = graph.get("edges") or []

    # 1. 找出"无 type"的节点
    no_type_ids = set()
    for node in nodes:
        data = node.get("data") or {}
        if not data.get("type"):
            no_type_ids.add(node.get("id"))

    # 2. 只删除"同时没有任何边连接"的节点，避免误删正在使用的节点
    connected = set()
    for edge in edges:
        connected.add(edge.get("source"))
        connected.add(edge.get("target"))
    removable = no_type_ids - connected

    if not removable and not no_type_ids:
        return doc, 0, 0

    graph["nodes"] = [n for n in nodes if n.get("id") not in removable]
    kept_ids = {n.get("id") for n in graph["nodes"]}
    graph["edges"] = [
        e for e in edges if e.get("source") in kept_ids and e.get("target") in kept_ids
    ]
    dropped_edges = len(edges) - len(graph["edges"])

    # 被保留的"无 type"节点给出提示（说明它可能真的被引用了，需要人工确认）
    for node_id in sorted(no_type_ids & connected):
        print(f"    [warn] 节点 {node_id} 无 type 但被边引用，已保留，请人工确认")

    return doc, len(removable), dropped_edges


def check(doc: dict, path: Path) -> None:
    graph = (doc.get("workflow") or {}).get("graph") or {}
    ids = {n.get("id") for n in iter_nodes(graph)}
    if not ids:
        raise SystemExit(f"[FAIL] {path.name}: 清洗后没有节点了")
    for edge in graph.get("edges") or []:
        if edge.get("source") not in ids or edge.get("target") not in ids:
            raise SystemExit(f"[FAIL] {path.name}: 悬空边 {edge.get('id')}")
    # 必填的 app / kind 字段仍在
    for key in ("app", "kind", "version"):
        if key not in doc:
            raise SystemExit(f"[FAIL] {path.name}: 缺少顶层字段 {key}")
    if not (doc.get("app") or {}).get("mode"):
        raise SystemExit(f"[FAIL] {path.name}: 缺少 app.mode")


def main() -> int:
    parser = argparse.ArgumentParser(description="剔除 Dify DSL 中的残留空节点")
    parser.add_argument("target", help="DSL 文件所在目录")
    parser.add_argument("--write", action="store_true", help="实际写入文件（默认仅预览）")
    args = parser.parse_args()

    root = Path(args.target)
    files = sorted(root.glob("*.yml"))
    if not files:
        print(f"未在 {root} 下找到 .yml 文件")
        return 1

    total_nodes = total_edges = 0
    for path in files:
        with path.open(encoding="utf-8") as fh:
            doc = yaml.safe_load(fh)
        cleaned, dropped_nodes, dropped_edges = sanitize(doc)
        check(cleaned, path)
        total_nodes += dropped_nodes
        total_edges += dropped_edges
        print(
            f"  {path.name:32s} 删除节点 {dropped_nodes:2d} / 删除边 {dropped_edges:2d}"
            f"  剩余节点 {len(cleaned['workflow']['graph']['nodes']):3d}"
        )
        if args.write and (dropped_nodes or dropped_edges):
            with path.open("w", encoding="utf-8", newline="\n") as fh:
                yaml.safe_dump(cleaned, fh, allow_unicode=True, sort_keys=False, width=1000)

    print(f"\n合计：删除空节点 {total_nodes} 个，删除悬空边 {total_edges} 条")
    if not args.write:
        print("（预览模式，未写入；加 --write 落盘）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
