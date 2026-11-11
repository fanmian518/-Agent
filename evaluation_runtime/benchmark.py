"""Read-only actual graph evaluation; --live performs bounded model requests."""
import argparse
import os
from unittest.mock import patch
from langchain_core.tools import StructuredTool
from backend.app.agent.graph import build_shopping_graph
from backend.app.agent.intent_parser import parse_intent
from backend.app.services.product_service import search_products
from evaluation_runtime import run, write_report
from evaluation_runtime.callbacks import EvaluationCallback


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--output',default='output/evaluation/shopping')
    args=parser.parse_args()
    # Only the public catalogue search tool is exposed. Orders, cart and payment are excluded.
    tool=StructuredTool.from_function(search_products,name='search_products',description='按条件只读查询商品目录')
    graph=build_shopping_graph([tool])
    queries=['查找5000元以下的黑色手机','查找蓝色耳机','查找苹果手机','查找100元以下的运动鞋']
    mode='live-readonly' if args.live else 'offline-readonly'
    def execute():
        for query in queries:
            try:
                with run('shopping-langgraph',mode):
                    graph.invoke({'user_message':query},config={'callbacks':[EvaluationCallback()]})
            except Exception as exc:
                print('Scenario failed:',type(exc).__name__)
    if args.live:
        execute()
    else:
        with patch('backend.app.agent.graph.parse_intent',parse_intent):
            execute()
    print(write_report(args.output,project='shopping-langgraph',mode=mode))


if __name__=='__main__':
    main()
