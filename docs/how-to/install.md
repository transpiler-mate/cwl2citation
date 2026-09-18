# Install

Python 3.10 or newer is required. From the project checkout:

```sh
pip install transpiler-mate-runtime .
transpiler-mate cwl2citation --help
```

The package registers its `transpiler_mate.plugins` entry point automatically. CSL styles and validation schemas are available locally after installation; citation rendering does not fetch styles or resolve DOIs. Loading CWL may require network access for its imports and schemas.
