"""Export daily AADF means for automatic route averages; no model retraining."""
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.route_traffic import prepare_route_traffic

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--aadf', type=Path, default=None)
    args=parser.parse_args()
    result=prepare_route_traffic(ROOT,args.aadf)
    print(json.dumps(result,ensure_ascii=False,indent=2))
