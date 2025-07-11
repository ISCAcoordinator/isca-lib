# ISCA (core) Library

**This repository is realllllyyy unstable at the moment :D**

This repository contains the fundamental blocks used by the ISCA tools.


## How to install

The library is not yet publisheable. Therefore, to install it, it is recommended to clone the repository and execute the command:

```sh
pip install -e.[dev]
```

This will install the requirements to run the library as well as the tools used by the maintainers to develop the library.

## How to use

As indicated earlier, the library is in active development and not stable. Nonetheless, it can be used already to explore the metadata for Interspeech 2025. To do so, copy the (full) content of the ForPublicationCommittee google drive folder locally. Then you can load the metadata as follows:

```python
import pathlib
conf_path = pathlib.Path("../data/ForPublicationCommittee/config.yaml")
from isca.io.cmt import CMTSerialiser
ser = CMTSerialiser(False, False)
conf = ser.load(conf_path)

# Show paper titles
for paper_id, paper in conf.papers.items():
    print(paper.title)
```

If you just want to load the papers, you can also proceed as follows:


```python
import pathlib
paper_metadata_path = pathlib.Path("../data/ForPublicationCommittee/validated_metadata.xlsx")
from isca.io.cmt import CMTSerialiser
ser = CMTSerialiser(False, False)
papers, _, _ = ser.load_papers(paper_metadata_path)

# Show paper titles
for paper_id, paper in papers.items():
    print(paper.title)
```
