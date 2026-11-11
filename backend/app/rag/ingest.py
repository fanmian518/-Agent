"""命令行导入 UTF-8 JSON 文档列表：python -m backend.app.rag.ingest 文件.json。"""

import argparse
from pathlib import Path

from pydantic import TypeAdapter

from backend.app.rag.knowledge import KnowledgeDocument, KnowledgeService


def main() -> int:
    """读取本地文档清单并调用分段入库服务。

    :return: 成功返回 0，配置、网络或文档错误返回 1。
    """
    parser = argparse.ArgumentParser(description="Ingest knowledge documents")
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    try:
        documents = TypeAdapter(list[KnowledgeDocument]).validate_json(args.path.read_text(encoding="utf-8"))
        count = KnowledgeService().ingest(documents)
    except Exception as error:
        print(f"Knowledge ingestion failed ({type(error).__name__}); check document format, model and database configuration.")
        return 1
    print(f"Knowledge ready; chunks={count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
