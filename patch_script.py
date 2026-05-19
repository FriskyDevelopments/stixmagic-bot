with open("tests/test_manifest.py", "r") as f:
    content = f.read()

content = content.replace(
    'from pipeline.asset_model import Asset',
    'from pipeline.asset_model import Asset, AssetCategory, SourceFormat'
)

content = content.replace(
    'category="letter"',
    'category=AssetCategory.LETTER'
)

content = content.replace(
    'category="symbol"',
    'category=AssetCategory.SYMBOL'
)

content = content.replace(
    'source_format="svg"',
    'source_format=SourceFormat.SVG'
)

with open("tests/test_manifest.py", "w") as f:
    f.write(content)
