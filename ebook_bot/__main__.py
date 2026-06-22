"""
Entry point: python -m ebook_bot [command]

Commands:
  run          Run one campaign immediately
  schedule     Start the scheduler (posts every POST_INTERVAL_HOURS)
  sales        Print sales report from all platforms
  email        Generate and print an email marketing sequence
"""
import sys
import json
from loguru import logger


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"

    if cmd == "run":
        from .orchestrator import run_campaign
        results = run_campaign(use_ai=True)
        print(json.dumps(results, indent=2, default=str))

    elif cmd == "schedule":
        from .scheduler import start
        start()

    elif cmd == "sales":
        from .orchestrator import get_sales_report
        report = get_sales_report()
        print(json.dumps(report, indent=2, default=str))

    elif cmd == "email":
        from .content.ai_writer import generate_email_sequence
        from .orchestrator import _get_best_link
        link = _get_best_link()
        emails = generate_email_sequence(link)
        for i, email in enumerate(emails, 1):
            print(f"\n{'='*60}")
            print(f"EMAIL {i}")
            print(f"SUBJECT: {email['subject']}")
            print(f"{'='*60}")
            print(email["body"])

    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
