import re
import requests

from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import Tuple, List, Generator
from dataclasses import dataclass


@dataclass
class PaperInfo:
    title: str
    authors: List[str]
    subjects: List[str]
    abstract: str
    submit: datetime
    pdf_url: str


def fetch_abstract(id: str) -> Tuple[datetime, str]:
    """Fetch paper abstract.
    
    Parameters
    ----------
    id: str
        Arxiv paper id.

    Returns
    -------
    submit: datetime
        First Submit date.
    abstract: str
        Paper abstract.
    """
    response = requests.get(f'https://arxiv.org/abs/{id}')
    soup = BeautifulSoup(response.text, 'html.parser')

    dateline = soup.find(class_='dateline').text.strip()
    submitted_match = re.search(r'Submitted on (\d+ \w+ \d+)', dateline)
    submit = datetime.strptime(submitted_match[0],'Submitted on %d %b %Y')

    abstract = soup.find(class_='abstract mathjax')
    abstract.span.extract()
    abstract = abstract.text.strip()
    return submit, abstract


def fetch_subject_recent(subject: str) -> Generator[PaperInfo, None, None]:
    """Fetech recent subject paper.
    
    Parameters
    ----------
    subject: str
        ArXiv subject, e.g., 'cs' for computer science.
    
    Returns
    -------
    PaperInfo
        Information about each paper including title, authors, subjects, 
        abstract, submission date, and PDF URL.
    """
    try:
        response = requests.get(f'https://arxiv.org/list/{subject}/recent')
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
    except requests.RequestException as e:
        print(f"Error fetching URL: {e}")
        return

    date_list = soup.findAll('h3')
    data_list = soup.findAll('dl')
    if len(date_list) != len(data_list):
        print("Mismatch between date and data sections.")
        return

    for date, data in zip(date_list, data_list):
        try:
            pub_date = datetime.strptime(date.text[:16], '%a, %d %b %Y')
        except ValueError:
            print(f"Invalid date format: {data.text}")
            continue

        # Skip papers older than 1 day
        if datetime.now() - pub_date > timedelta(days=1):
            continue

        item_list = data.findAll('dt')
        meta_list = data.findAll('dd')
        if len(item_list) != len(meta_list):
            print("Mismatch between items and metadata entries.")
            continue

        for item, meta in zip(item_list, meta_list):
            try:
                # Extract arXiv ID
                id = item.find_all('a')[1].text.strip()
                id = id.split(':')[1]
                submit, abstract = fetch_abstract(id)

                # Extract title
                title = meta.find(class_="list-title mathjax")
                title.span.extract()
                title = title.text.strip()

                # Extract author
                list_author = meta.find(class_="list-authors")
                list_author = [author.text for author in list_author.findAll("a")]

                # Extract subjects
                list_subject = meta.find(class_="list-subjects")
                list_subject.span.extract()
                list_subject = list_subject.text.strip()
                list_subject = [subject.strip() 
                                for subject in list_subject.split(";")]

                yield PaperInfo(title=title,
                                authors=list_author,
                                subjects=list_subject,
                                abstract=abstract,
                                submit=submit,
                                pdf_url=f'https://arxiv.org/pdf/{id}.pdf')
            
            except Exception as e:
                print(f"Error processing paper: {e}")
                continue
