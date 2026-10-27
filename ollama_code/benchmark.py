"""Evaluate recorded real test outcomes; never claim model benchmark results without runs."""
import argparse,json
from pathlib import Path
from .intelligence import score_benchmark

def main():
    p=argparse.ArgumentParser(description='Score JSON coding benchmark outcomes')
    p.add_argument('results',type=Path,help='JSON list of recorded coding tasks')
    args=p.parse_args()
    print(json.dumps(score_benchmark(json.loads(args.results.read_text())),indent=2))
if __name__=='__main__':main()
