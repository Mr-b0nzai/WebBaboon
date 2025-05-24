import json
import re

def fix_trailing_backslashes(obj):
    if isinstance(obj, dict):
        return {k: fix_trailing_backslashes(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [fix_trailing_backslashes(elem) for elem in obj]
    elif isinstance(obj, str):
        # Check for strings that appear to be regex and end in an unescaped backslash
        if re.search(r'[^\\](\\\\)*\\$', obj):
            return obj + '\\'  # Add one extra backslash (JSON will serialize this correctly as \\\\)
        return obj
    else:
        return obj

def main():
    input_file = "cleaned_combined_technologies.json"
    output_file = "fixed_output.json"

    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    fixed_data = fix_trailing_backslashes(data)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(fixed_data, f, indent=4, ensure_ascii=False)

    print(f"Fixed regex patterns saved to: {output_file}")

if __name__ == "__main__":
    main()
