import argparse
import json
from wealthpilot.config import load_config
from wealthpilot.data_generation import write_dataset
from wealthpilot.validate_data import validate_generated_data


def main():
    parser = argparse.ArgumentParser(description="Generate WealthPilot Day 1 synthetic datasets.")
    parser.add_argument("--config", default="config/settings.yaml")
    parser.add_argument("--output", default="data/generated")
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    config = load_config(args.config)
    manifest = write_dataset(config, args.output, args.seed)
    report = validate_generated_data(args.output)
    print(json.dumps(
    {"manifest": manifest, "validation": report},
    indent=2,
    default=lambda value: value.item() if hasattr(value, "item") else str(value)
))


if __name__ == "__main__":
    main()
