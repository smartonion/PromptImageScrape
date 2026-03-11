import json


def parse_jsonld_blocks(response) -> list[dict]:
    blocks = []
    scripts = response.xpath("//script[@type='application/ld+json']/text()").getall()
    for script in scripts:
        if not script or not script.strip():
            continue
        try:
            parsed = json.loads(script)
        except json.JSONDecodeError:
            continue

        if isinstance(parsed, list):
            blocks.extend([item for item in parsed if isinstance(item, dict)])
        elif isinstance(parsed, dict):
            blocks.append(parsed)

    return blocks


def first_jsonld_of_type(blocks: list[dict], expected_type: str) -> dict | None:
    expected = expected_type.lower()
    for block in blocks:
        raw_type = block.get("@type")
        if isinstance(raw_type, list):
            match = any(str(item).lower() == expected for item in raw_type)
        else:
            match = str(raw_type).lower() == expected
        if match:
            return block
    return None
