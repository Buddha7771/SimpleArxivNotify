import requests

from typing import List, Optional
from pathlib import PosixPath, Path
from discord import SyncWebhook, Embed, File

from api import fetch_subject_recent, PaperInfo


class SimpleArxivNotify:
    """Simple Arxiv discord notify."""
    LOGO_IMG_PATH = Path(__file__).parent/'image'/'logo.png'
    MAX_ABSTRACT_LEN = 4000
    CHUNK_SIZE = 1000

    def __init__(
            self, 
            webhook_url: str,
            subjects: List[str],
            pdf_dir_path: Optional[PosixPath] = None):
        self.webhook = SyncWebhook.from_url(webhook_url)
        self.subjects = subjects
        self.pdf_dir_path = pdf_dir_path
        if pdf_dir_path is not None:
            self.pdf_dir_path.mkdir(parents=True, exist_ok=True)
    
    def send_embed(self, paper_info: PaperInfo):
        """Creates and sends a Discord embed for a given paper."""
        logo_img = File(self.LOGO_IMG_PATH)
        logo_url = f"attachment://{logo_img.filename}"

        embed = Embed(title=f'**{paper_info.title}**',
                      url=paper_info.pdf_url,
                      color=0xffffff,
                      timestamp=paper_info.submit)
        embed.set_author(icon_url=logo_url, name='arXiv')
        embed.set_footer(icon_url=logo_url, text='arXiv')
        embed.add_field(
            name='Authors',
            value='```' + ', '.join(paper_info.authors) + '```',
            inline=True)
        embed.add_field(
            name='Subjects',
            value='```'  + ', '.join(paper_info.subjects) + '```',
            inline=True)

        abs_len = min(len(paper_info.abstract), self.MAX_ABSTRACT_LEN)
        chunk = self.CHUNK_SIZE
        for i in range(0, abs_len, chunk):
            embed.add_field(
                name=f'Abstract {i//chunk + 1}/{abs_len//chunk + 1}',
                value='> ' + paper_info.abstract[i:i + chunk],
                inline=False)

        self.webhook.send(embed=embed, file=logo_img)
    
    def save_pdf(self, paper_info: PaperInfo):
        """Downloads and saves the PDF to the specified directory."""
        if self.pdf_dir_path is None:
            return

        pub = paper_info.submit
        pdf_dir_path = self.pdf_dir_path/\
            f'{pub.year}-{str(pub.month).zfill(2)}'/\
            f'{str(pub.day).zfill(2)}'
        pdf_dir_path.mkdir(parents=True, exist_ok=True)

        try:
            response = requests.get(paper_info.pdf_url)
            response.raise_for_status()
            with open(pdf_dir_path/f'{paper_info.title}.pdf', 'wb') as f:
                f.write(response.content)
        except requests.RequestException as e:
            print(f"Failed to download PDF for {paper_info.title}: {e}")

    def run(self):
        """Fetch recent papers and notify via Discord webhook."""
        for subject in self.subjects:
            for paper_info in fetch_subject_recent(subject):
                self.send_embed(paper_info)
                self.save_pdf(paper_info)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-w', '--webhook', type=str, required=True,
                        help='Discord webhook URL.')
    parser.add_argument('-s', '--subjects', nargs='*', default=['q-bio.BM'],
                        help = "Subjects to get notified about.")
    parser.add_argument('-d', '--dir', type=PosixPath, default=None,
                        help="Directory to save paper PDFs.")
    args = parser.parse_args()
    SimpleArxivNotify(webhook_url=args.webhook,
                      subjects=args.subjects,
                      pdf_dir_path=args.dir).run()
