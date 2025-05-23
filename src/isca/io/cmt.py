import pandas as pd

from ..model import Paper, Person

CMT_AUTHOR_SEP = "; "
CMT_FIRST_LAST_STEP = ", "
CMT_CORRESPONDING_MARKER = "*"


class CMTSerialiser:
    def load_submissions(self, file_handler) -> tuple[set[Paper], set[Person]]:
        df = pd.read_csv(file_handler, sep="\t")
        author_set = set()
        paper_set = set()

        for _, paper_info in df.iterrows():
            author_names = str(paper_info["Author Names"]).split(CMT_AUTHOR_SEP)
            author_emails = str(paper_info["Author Emails"]).split(CMT_AUTHOR_SEP)

            assert len(author_emails) == len(
                author_names
            ), f"The number of authors ({len(author_names)}) does not match the number of emails ({len(author_emails)})"

            paper_authors = list()

            for i_author, cur_author in enumerate(author_names):
                last_name, first_name = cur_author.split(CMT_FIRST_LAST_STEP)
                first_name = first_name.replace(CMT_CORRESPONDING_MARKER, "")
                email = author_emails[i_author].replace(CMT_CORRESPONDING_MARKER, "")

                cur_person = Person(first_name, last_name, email)
                paper_authors.append(cur_person)
                author_set.add(cur_person)

            cur_paper = Paper(str(paper_info["Paper Title"]), paper_authors, str(paper_info["Abstract"]))
            paper_set.add(cur_paper)

        return paper_set, author_set
