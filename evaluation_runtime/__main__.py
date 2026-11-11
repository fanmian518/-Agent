import argparse
import json
from pathlib import Path
from .metrics import write_report

parser = argparse.ArgumentParser(description='Export measured Agent metrics; no paid calls are made')
parser.add_argument('--project')
parser.add_argument('--mode', default='live')
parser.add_argument('--pricing', type=Path)
parser.add_argument('--output', default='output/evaluation/report')
args = parser.parse_args()
prices = json.loads(args.pricing.read_text(encoding='utf-8')) if args.pricing else None
print(json.dumps(write_report(args.output, project=args.project, mode=args.mode, pricing=prices), ensure_ascii=False, indent=2))
