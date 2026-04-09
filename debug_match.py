import sys
import traceback

sys.stdout.reconfigure(encoding='utf-8')

print("Testing matching logic...")
try:
    from backend.routes.match import match_needs
    res = match_needs()
    print("Match successful!")
    print(res)
except Exception as e:
    print("Match failed:")
    traceback.print_exc()
